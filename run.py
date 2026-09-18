import os

from app import create_app
from app.extensions import socketio

app = create_app()

if __name__ == "__main__":
    # 3000 is the port the v0 preview panel watches for and proxies
    # automatically; keep this as the default so the app is visible in
    # preview without extra configuration.
    port = int(os.environ.get("PORT", 3000))
    socketio.run(app, host="0.0.0.0", port=port, debug=True, allow_unsafe_werkzeug=True)
