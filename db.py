import os
import sqlite3
import pymysql
import pymysql.cursors
from datetime import datetime
from config import Config

_engine = None # 'mysql' or 'sqlite'

def detect_and_set_engine():
    global _engine
    if Config.DB_TYPE == 'sqlite':
        _engine = 'sqlite'
        return _engine
    
    if Config.DB_TYPE in ('mysql', 'auto'):
        try:
            # Test connecting to MySQL
            conn = pymysql.connect(
                host=Config.MYSQL_HOST,
                port=Config.MYSQL_PORT,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                charset='utf8mb4',
                connect_timeout=2
            )
            with conn.cursor() as cur:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS {Config.MYSQL_DB} CHARACTER SET utf8mb4;")
            conn.select_db(Config.MYSQL_DB)
            conn.close()
            _engine = 'mysql'
            print("[Database] Successfully connected to MySQL server!")
            return _engine
        except Exception as e:
            if Config.DB_TYPE == 'mysql':
                print(f"[Database Warning] MySQL connection failed ({e}). Falling back to SQLite.")
            _engine = 'sqlite'
            print("[Database] Using SQLite database at:", Config.SQLITE_PATH)
            return _engine

def get_engine():
    global _engine
    if _engine is None:
        detect_and_set_engine()
    return _engine

def get_connection():
    engine = get_engine()
    if engine == 'mysql':
        return pymysql.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
    else:
        conn = sqlite3.connect(Config.SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def execute_query(sql, params=None, fetch=None):
    """
    Execute SQL query safely.
    Replaces %s with ? when running on SQLite.
    Returns:
      fetch='all': list of dicts
      fetch='one': dict or None
      fetch=None: lastrowid (or rowcount)
    """
    engine = get_engine()
    if params is None:
        params = ()
    elif isinstance(params, list):
        params = tuple(params)
    elif not isinstance(params, tuple):
        params = (params,)

    if engine == 'sqlite':
        # Convert %s placeholders to ? for sqlite
        adapted_sql = sql.replace('%s', '?')
        # Also adapt common MySQL syntax differences if any
        adapted_sql = adapted_sql.replace('NOW()', "datetime('now', 'localtime')")
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(adapted_sql, params)
            if fetch == 'all':
                rows = cur.fetchall()
                return [dict(row) for row in rows]
            elif fetch == 'one':
                row = cur.fetchone()
                return dict(row) if row else None
            else:
                conn.commit()
                return cur.lastrowid
        finally:
            conn.close()
    else:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                if fetch == 'all':
                    return cur.fetchall()
                elif fetch == 'one':
                    return cur.fetchone()
                else:
                    return cur.lastrowid
        finally:
            conn.close()

def init_db():
    engine = get_engine()
    base_dir = os.path.dirname(__file__)
    
    if engine == 'mysql':
        schema_file = os.path.join(base_dir, 'schema.sql')
        with open(schema_file, 'r', encoding='utf-8') as f:
            script = f.read()
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                # Run statement by statement
                statements = [s.strip() for s in script.split(';') if s.strip()]
                for s in statements:
                    cur.execute(s)
            print("[Database] MySQL tables initialized successfully.")
        finally:
            conn.close()
    else:
        schema_file = os.path.join(base_dir, 'schema_sqlite.sql')
        with open(schema_file, 'r', encoding='utf-8') as f:
            script = f.read()
        conn = get_connection()
        try:
            conn.executescript(script)
            conn.commit()
            print("[Database] SQLite tables initialized successfully.")
        finally:
            conn.close()
