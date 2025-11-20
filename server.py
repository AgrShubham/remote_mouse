from flask import Flask, render_template
from flask_socketio import SocketIO
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key

# Explicitly tell Flask where templates are
app = Flask(__name__, template_folder="templates")
socketio = SocketIO(app, cors_allowed_origins="*")

mouse = MouseController()
keyboard = KeyboardController()

# Map simple string names from client -> pynput Key objects
KEY_MAP = {
    # Basic control keys
    "enter": Key.enter,
    "backspace": Key.backspace,
    "tab": Key.tab,
    "esc": Key.esc,
    "space": Key.space,
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
    "delete": Key.delete,
    "home": Key.home,
    "end": Key.end,
    "page_up": Key.page_up,
    "page_down": Key.page_down,

    # Media keys (support can vary by OS)
    "media_play_pause": Key.media_play_pause,
    "media_next": Key.media_next,
    "media_previous": Key.media_previous,
    "media_volume_up": Key.media_volume_up,
    "media_volume_down": Key.media_volume_down,
    "media_volume_mute": Key.media_volume_mute,
}


@app.route("/")
def index():
    return render_template("index.html")


# ----------------- Mouse handlers ----------------- #

@socketio.on("move")
def handle_move(data):
    try:
        dx = float(data.get("dx", 0))
        dy = float(data.get("dy", 0))
        sensitivity = 1.0  # speed handled on client side
        mouse.move(dx * sensitivity, dy * sensitivity)
    except Exception as e:
        print("Error in move:", e)


@socketio.on("click")
def handle_click(data):
    try:
        button_name = data.get("button", "left")
        if button_name == "right":
            btn = Button.right
        else:
            btn = Button.left
        mouse.click(btn)
    except Exception as e:
        print("Error in click:", e)


@socketio.on("scroll")
def handle_scroll(data):
    try:
        dx = float(data.get("dx", 0))
        dy = float(data.get("dy", 0))
        mouse.scroll(dx, dy)
    except Exception as e:
        print("Error in scroll:", e)


# ----------------- Keyboard handlers ----------------- #

@socketio.on("text")
def handle_text(data):
    """
    Type a full string as if from keyboard.
    """
    try:
        text = data.get("text", "")
        if text:
            keyboard.type(text)
    except Exception as e:
        print("Error in text:", e)


@socketio.on("key")
def handle_key(data):
    """
    Handle single special keys and media keys.
    data: { "name": "enter" | "media_volume_up" | ..., "action": "tap"|"press"|"release" }
    """
    try:
        name = data.get("name")
        if not name:
            return

        key = KEY_MAP.get(name)
        if not key:
            print(f"Unknown key requested: {name}")
            return

        action = data.get("action", "tap")

        if action == "press":
            keyboard.press(key)
        elif action == "release":
            keyboard.release(key)
        else:  # "tap" (default)
            keyboard.press(key)
            keyboard.release(key)
    except Exception as e:
        print("Error in key:", e)


if __name__ == "__main__":
    # debug=True so we see errors clearly in the terminal
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
