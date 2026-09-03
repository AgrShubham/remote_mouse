from flask import Flask, render_template
from flask_socketio import SocketIO
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key

# Explicitly tell Flask where templates and static files are
app = Flask(__name__, template_folder="templates", static_folder="static")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

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

# Subpixel precision accumulators
subpixel_x = 0.0
subpixel_y = 0.0
subpixel_scroll_x = 0.0
subpixel_scroll_y = 0.0

@socketio.on("move")
def handle_move(data):
    global subpixel_x, subpixel_y
    try:
        dx = float(data.get("dx", 0)) + subpixel_x
        dy = float(data.get("dy", 0)) + subpixel_y

        int_dx = int(dx)
        int_dy = int(dy)

        subpixel_x = dx - int_dx
        subpixel_y = dy - int_dy

        if int_dx != 0 or int_dy != 0:
            mouse.move(int_dx, int_dy)
    except Exception as e:
        print("Error in move:", e)


@socketio.on("click")
def handle_click(data):
    try:
        button_name = data.get("button", "left")
        count = int(data.get("count", 1))
        btn = Button.right if button_name == "right" else Button.left
        mouse.click(btn, count)
    except Exception as e:
        print("Error in click:", e)


@socketio.on("mouse_down")
def handle_mouse_down(data):
    try:
        button_name = data.get("button", "left")
        btn = Button.right if button_name == "right" else Button.left
        mouse.press(btn)
    except Exception as e:
        print("Error in mouse_down:", e)


@socketio.on("mouse_up")
def handle_mouse_up(data):
    try:
        button_name = data.get("button", "left")
        btn = Button.right if button_name == "right" else Button.left
        mouse.release(btn)
    except Exception as e:
        print("Error in mouse_up:", e)


@socketio.on("scroll")
def handle_scroll(data):
    global subpixel_scroll_x, subpixel_scroll_y
    try:
        dx = float(data.get("dx", 0)) + subpixel_scroll_x
        dy = float(data.get("dy", 0)) + subpixel_scroll_y

        int_dx = int(dx)
        int_dy = int(dy)

        subpixel_scroll_x = dx - int_dx
        subpixel_scroll_y = dy - int_dy

        if int_dx != 0 or int_dy != 0:
            mouse.scroll(int_dx, int_dy)
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


# ----------------- Gamepad handlers ----------------- #

def resolve_gamepad_input(code):
    """
    Resolves input code like 'w', 'space', 'shift', 'mouse_left', etc.
    Returns (type, resolved_obj) where type is 'key' or 'mouse'.
    """
    if not code:
        return None, None
    code_lower = str(code).lower()

    if code_lower in ("mouse_left", "left_click", "mouse1"):
        return "mouse", Button.left
    if code_lower in ("mouse_right", "right_click", "mouse2"):
        return "mouse", Button.right
    if code_lower in ("mouse_middle", "middle_click", "mouse3"):
        return "mouse", Button.middle

    special_keys = {
        "space": Key.space,
        "shift": Key.shift,
        "shift_l": Key.shift_l,
        "ctrl": Key.ctrl,
        "ctrl_l": Key.ctrl_l,
        "alt": Key.alt,
        "tab": Key.tab,
        "esc": Key.esc,
        "enter": Key.enter,
        "up": Key.up,
        "down": Key.down,
        "left": Key.left,
        "right": Key.right,
        "backspace": Key.backspace,
        "caps_lock": Key.caps_lock,
        "delete": Key.delete,
        "page_up": Key.page_up,
        "page_down": Key.page_down,
        "home": Key.home,
        "end": Key.end,
        "f1": Key.f1,
        "f2": Key.f2,
        "f3": Key.f3,
        "f4": Key.f4,
        "f5": Key.f5,
        "f6": Key.f6,
    }
    if code_lower in special_keys:
        return "key", special_keys[code_lower]

    if len(code) == 1:
        return "key", code.lower()

    return None, None


held_gamepad_keys = set()
current_stick_keys = set()

@socketio.on("gamepad_button_down")
def handle_gamepad_button_down(data):
    try:
        input_code = data.get("input")
        in_type, resolved = resolve_gamepad_input(input_code)
        if in_type == "key":
            keyboard.press(resolved)
            held_gamepad_keys.add(resolved)
        elif in_type == "mouse":
            mouse.press(resolved)
    except Exception as e:
        print("Error in gamepad_button_down:", e)


@socketio.on("gamepad_button_up")
def handle_gamepad_button_up(data):
    try:
        input_code = data.get("input")
        in_type, resolved = resolve_gamepad_input(input_code)
        if in_type == "key":
            keyboard.release(resolved)
            held_gamepad_keys.discard(resolved)
        elif in_type == "mouse":
            mouse.release(resolved)
    except Exception as e:
        print("Error in gamepad_button_up:", e)


@socketio.on("gamepad_stick_sync")
def handle_gamepad_stick_sync(data):
    """
    Syncs active movement keys from analog thumbstick (e.g. ['w', 'd'] or ['a']).
    Releases keys that became inactive and presses newly active keys.
    """
    global current_stick_keys
    try:
        desired_keys = set(data.get("keys", []))
        to_release = current_stick_keys - desired_keys
        to_press = desired_keys - current_stick_keys

        for k in to_release:
            in_type, resolved = resolve_gamepad_input(k)
            if in_type == "key":
                keyboard.release(resolved)

        for k in to_press:
            in_type, resolved = resolve_gamepad_input(k)
            if in_type == "key":
                keyboard.press(resolved)

        current_stick_keys = desired_keys
    except Exception as e:
        print("Error in gamepad_stick_sync:", e)


@socketio.on("gamepad_release_all")
def handle_gamepad_release_all():
    global current_stick_keys, held_gamepad_keys
    try:
        for k in current_stick_keys:
            in_type, resolved = resolve_gamepad_input(k)
            if in_type == "key":
                keyboard.release(resolved)
        current_stick_keys.clear()

        for k in list(held_gamepad_keys):
            keyboard.release(k)
        held_gamepad_keys.clear()

        mouse.release(Button.left)
        mouse.release(Button.right)
    except Exception as e:
        print("Error in gamepad_release_all:", e)


if __name__ == "__main__":
    # debug=True so we see errors clearly in the terminal
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)
