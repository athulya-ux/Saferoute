import os
from flask import Flask, render_template, send_from_directory, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
from config import Config
from database.db import init_db
from database.seed_data import seed_initial_data

# Import API blueprints
from api.routes_api import routes_bp
from api.incidents_api import incidents_bp
from api.help_points_api import help_points_bp
from api.auth_api import auth_bp
from api.walk_together_api import walk_bp
from api.emergency_api import emergency_bp
from api.anti_tamper_api import tamper_bp
from sockets.chat_socket import register_socket_events

def create_app():
    app = Flask(__name__, 
                template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
                static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    
    app.config.from_object(Config)
    CORS(app)

    # Register blueprints
    app.register_blueprint(routes_bp)
    app.register_blueprint(incidents_bp)
    app.register_blueprint(help_points_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(walk_bp)
    app.register_blueprint(emergency_bp)
    app.register_blueprint(tamper_bp)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/api/health')
    def health():
        return jsonify({
            "status": "healthy",
            "app": "SafeRoute - Women Route Safety Platform",
            "version": "1.0.0"
        })

    return app

app = create_app()
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
register_socket_events(socketio)

# Auto-initialize database on startup (for both local and production Gunicorn on Render)
try:
    init_db()
    seed_initial_data()
except Exception as e:
    print("[Startup Note] Database init warning:", e)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n=======================================================")
    print(f"  SafeRoute: Women-Only Route Safety Web App")
    print(f"  Server listening on: http://127.0.0.1:{port}")
    print(f"=======================================================\n")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
