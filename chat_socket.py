from flask_socketio import emit, join_room, leave_room
from database.db import execute_query

def register_socket_events(socketio):
    """
    Registers SocketIO handlers for ephemeral walk-together in-app chat,
    mutual consent negotiation between 2 women travelers, and real-time emergency SOS broadcast.
    """

    @socketio.on('connect')
    def handle_connect():
        pass

    @socketio.on('disconnect')
    def handle_disconnect():
        pass

    @socketio.on('join_user_channel')
    def on_join_user(data):
        user_id = data.get('user_id')
        if user_id:
            room = f"user_{user_id}"
            join_room(room)

    @socketio.on('walk_request_sent')
    def on_walk_request_sent(data):
        """
        User A sends walk request to User B.
        Broadcasts incoming invitation to User B's personal channel.
        """
        recipient_id = data.get('recipient_id')
        requester_id = data.get('requester_id')
        walk_id = data.get('walk_request_id')
        approx_dist = data.get('approx_distance_m', 350)

        user = execute_query("SELECT anonymous_handle FROM users WHERE id = %s", (requester_id,), fetch='one')
        handle = user['anonymous_handle'] if user else "Traveler"

        recipient_room = f"user_{recipient_id}"
        emit('incoming_walk_request', {
            "walk_request_id": walk_id,
            "requester_id": requester_id,
            "requester_handle": handle,
            "approx_distance_m": approx_dist,
            "message": f"{handle} (~{approx_dist}m away) would like to walk together with you."
        }, to=recipient_room)

    @socketio.on('walk_request_response')
    def on_walk_request_response(data):
        """
        User B accepts or declines.
        Notifies User A and User B. If accepted, both immediately open chat.
        """
        walk_id = data.get('walk_request_id')
        requester_id = data.get('requester_id')
        recipient_id = data.get('recipient_id')
        decision = data.get('decision') # 'accepted' or 'rejected'

        u1 = execute_query("SELECT anonymous_handle FROM users WHERE id = %s", (requester_id,), fetch='one')
        u2 = execute_query("SELECT anonymous_handle FROM users WHERE id = %s", (recipient_id,), fetch='one')

        h1 = u1['anonymous_handle'] if u1 else "Requester"
        h2 = u2['anonymous_handle'] if u2 else "Companion"

        payload = {
            "walk_request_id": walk_id,
            "decision": decision,
            "requester_id": requester_id,
            "recipient_id": recipient_id,
            "requester_handle": h1,
            "recipient_handle": h2,
            "chat_enabled": decision == 'accepted'
        }

        # Send to both user rooms
        emit('walk_decision_received', payload, to=f"user_{requester_id}")
        emit('walk_decision_received', payload, to=f"user_{recipient_id}")

    @socketio.on('join_walk')
    def on_join_walk(data):
        walk_id = data.get('walk_request_id')
        user_id = data.get('user_id')
        if not walk_id:
            return

        room = f"walk_{walk_id}"
        join_room(room)

        user = execute_query("SELECT anonymous_handle FROM users WHERE id = %s", (user_id,), fetch='one')
        handle = user['anonymous_handle'] if user else "Traveler"

        messages = execute_query("""
            SELECT m.id, m.sender_id, m.message_text, m.created_at, u.anonymous_handle
            FROM chat_messages m
            JOIN users u ON u.id = m.sender_id
            WHERE m.walk_request_id = %s
            ORDER BY m.id ASC
        """, (walk_id,), fetch='all') or []

        emit('chat_history', {
            "walk_request_id": walk_id,
            "messages": messages
        })

        emit('user_joined', {
            "message": f"{handle} joined the walk.",
            "anonymous_handle": handle
        }, to=room)

    @socketio.on('send_message')
    def on_send_message(data):
        walk_id = data.get('walk_request_id')
        sender_id = data.get('sender_id')
        text = data.get('text', '').strip()

        if not walk_id or not sender_id or not text:
            return

        room = f"walk_{walk_id}"

        msg_id = execute_query("""
            INSERT INTO chat_messages (walk_request_id, sender_id, message_text)
            VALUES (%s, %s, %s)
        """, (walk_id, sender_id, text))

        user = execute_query("SELECT anonymous_handle FROM users WHERE id = %s", (sender_id,), fetch='one')
        sender_handle = user['anonymous_handle'] if user else "Traveler"

        emit('new_message', {
            "id": msg_id,
            "walk_request_id": walk_id,
            "sender_id": sender_id,
            "sender_handle": sender_handle,
            "text": text,
            "timestamp": "Just now"
        }, to=room)

    @socketio.on('leave_walk')
    def on_leave_walk(data):
        walk_id = data.get('walk_request_id')
        if walk_id:
            room = f"walk_{walk_id}"
            leave_room(room)
            emit('user_left', {"walk_request_id": walk_id}, to=room)

    @socketio.on('sos_broadcast_event')
    def on_sos_broadcast(data):
        emit('incoming_sos_alert', data, broadcast=True)

    @socketio.on('tamper_broadcast_event')
    def on_tamper_broadcast(data):
        emit('incoming_tamper_alert', data, broadcast=True)
