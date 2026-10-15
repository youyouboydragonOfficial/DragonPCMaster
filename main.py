import os
import sys
import socket
import threading
import webview
from flask import Flask, jsonify, send_from_directory, render_template_string
from hardware_engine import HardwareEngine

app = Flask(__name__, static_folder="static")
engine = HardwareEngine()

def find_free_port(preferred=47820):
    for port in [preferred, preferred + 1, preferred + 2, 0]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(('127.0.0.1', port))
            actual_port = s.getsockname()[1]
            s.close()
            return actual_port
        except Exception:
            continue
    return 47820

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)

@app.route("/api/specs")
def get_specs():
    return jsonify(engine.static_info)

@app.route("/api/metrics")
def get_metrics():
    metrics = engine.sample_metrics()
    return jsonify(metrics)

@app.route("/api/game/start", methods=["POST"])
def game_start():
    res = engine.start_game_recording()
    return jsonify(res)

@app.route("/api/game/stop", methods=["POST"])
def game_stop():
    res = engine.stop_game_recording()
    return jsonify(res)

import time

@app.route("/api/game/status")
def game_status():
    duration = 0
    if engine.recording_active:
        duration = round(time.time() - engine.session_start_time, 1)
    return jsonify({
        "active": engine.recording_active,
        "samples": len(engine.session_data),
        "duration": duration
    })

def run_flask(port):
    # Run flask in quiet mode
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)

def main():
    port = find_free_port()
    flask_thread = threading.Thread(target=run_flask, args=(port,), daemon=True)
    flask_thread.start()

    icon_path = os.path.abspath(os.path.join("static", "icon.ico"))
    if not os.path.exists(icon_path):
        icon_path = None

    # Create native WebView window
    window = webview.create_window(
        title="Dragon PC Master Monitor - 最強パソコン状態・負荷監視",
        url=f"http://127.0.0.1:{port}",
        width=1280,
        height=820,
        min_size=(980, 680),
        background_color="#0a0d14"
    )

    def on_closing():
        engine.close()

    window.events.closing += on_closing
    webview.start(icon=icon_path)

if __name__ == "__main__":
    main()
