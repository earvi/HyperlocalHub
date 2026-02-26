from flask import request
from flask_socketio import join_room, leave_room, emit

def register_socket_events(socketio):
    
    @socketio.on('connect')
    def handle_connect():
        print(f"Client connected: {request.sid}")

    @socketio.on('disconnect')
    def handle_disconnect():
        print(f"Client disconnected: {request.sid}")

    @socketio.on('join_alert')
    def handle_join(data):
        alert_id = data.get('alert_id')
        if alert_id:
            room = f"alert_{alert_id}"
            join_room(room)
            print(f"Client {request.sid} joined room {room}")
            
    @socketio.on('leave_alert')
    def handle_leave(data):
        alert_id = data.get('alert_id')
        if alert_id:
            room = f"alert_{alert_id}"
            leave_room(room)
            print(f"Client {request.sid} left room {room}")

    # Note: 'new_comment' event is emitted from the REST API route via server-side emit,
    # not usually from client to client directly for security (to validate user first).
