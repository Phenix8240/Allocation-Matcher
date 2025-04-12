# desktop_app.py
import threading
import webview
from app import app  # this assumes app.py contains `app = Flask(__name__)`

def run_flask():
    app.run(debug=False, use_reloader=False)

if __name__ == '__main__':
    # Run Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Launch the desktop app pointing to the Flask server
    webview.create_window("Elective Comparator", "http://127.0.0.1:5000")
    webview.start()
