import threading
import time
import webview
import sys
import os

# Ensure the current directory is in the path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import app, socketio
from database import init_db

def start_server():
    print("Starting local HyperlocalHub server...")
    # It is crucial to set use_reloader=False when running in a background thread
    # otherwise Werkzeug tries to spawn a subprocess and crashes.
    socketio.run(app, host="127.0.0.1", port=5000, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    # Initialize the database if needed
    init_db()

    # Start the Flask/SocketIO backend in a background thread
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()

    # Give the server a short moment to bind to the port
    time.sleep(1.5)

    # Create the native desktop window pointing to our local server
    print("Launching native desktop window...")
    window = webview.create_window(
        title='HyperlocalHub', 
        url='http://127.0.0.1:5000', 
        width=1280, 
        height=800,
        min_size=(900, 600),
        text_select=True,
        zoomable=True
    )
    
    # Start the GUI event loop. This blocks until the window is closed.
    webview.start(debug=False)
