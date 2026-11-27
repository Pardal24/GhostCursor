import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)

from ctypes import wintypes
from PIL import Image, ImageTk
from pynput import mouse, keyboard
from pathlib import Path
import tkinter as tk
import queue
import threading
import socket
import time
import signal
import json

user32 = ctypes.windll.user32

# --------------------- Constants ---------------------------------

W = user32.GetSystemMetrics(0)
H = user32.GetSystemMetrics(1)

PARK_MARGIN = 200
HOLD_KEY = keyboard.Key.f8

log = queue.Queue()
parked = (0,0)
reached = False

# ---------------------- Windows Message ----------------------------

WM_MOUSEMOVE = 0x0200
BUTTON_MSGS = {                         # code -> (button, is_down)
    0x0201: ("left", True),   0x0202: ("left", False),
    0x0204: ("right", True),  0x0205: ("right", False),
    0x0207: ("middle", True), 0x0208: ("middle", False),
    0x020B: ("x", True),      0x020C: ("x", False),
}
WHEEL_MSGS = {0x020A, 0x020E}
LLMHF_INJECTED = 0x01


#---------------------- Hide real cursor --------------------

# every system cursor shape Windows might show
OCR_IDS = [32512, 32513, 32514, 32515, 32516, 32642, 32643,
           32644, 32645, 32646, 32648, 32649, 32650]
SPI_SETCURSORS = 0x0057

user32.CreateCursor.restype = wintypes.HANDLE
user32.CreateCursor.argtypes = [wintypes.HINSTANCE, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
user32.SetSystemCursor.argtypes = [wintypes.HANDLE, wintypes.DWORD]

def hide_cursor():
    and_mask = (ctypes.c_ubyte * 128)(*([0xFF] * 128))
    xor_mask = (ctypes.c_ubyte * 128)()
    for ocr in OCR_IDS:
        blank = user32.CreateCursor(None, 0, 0, 32, 32, and_mask, xor_mask)
        user32.SetSystemCursor(blank, ocr)

def show_cursor():
    user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)

# -------------------- Windows Input (Mouse, Keyboard) ---------------

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

class INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]

MOUSE_FLAGS = {           # name -> (down flag, up flag, mouseData)
    "left":   (0x0002, 0x0004, 0),
    "right":  (0x0008, 0x0010, 0),
    "middle": (0x0020, 0x0040, 0),
    "x1":     (0x0080, 0x0100, 1),
    "x2":     (0x0080, 0x0100, 2),
}

MOUSEEVENTF_WHEEL, MOUSEEVENTF_HWHEEL = 0x0800, 0x1000

def send_mouse(flags, data=0):
    inp = INPUT(type=0)
    inp.u.mi = MOUSEINPUT(0, 0, data & 0xFFFFFFFF, flags, 0, 0)   # & handles negative wheel values
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

def get_cursor():
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


visitor_btns = set()
saved = None
replaying = False

def visitor_button(button, down):
    global saved, replaying
    if button not in MOUSE_FLAGS or not visiting:
        return
    down_f, up_f, data = MOUSE_FLAGS[button]
    gx, gy = round(mx), round(my)
    replaying = True
    if down:
        if not visitor_btns:
            saved = get_cursor()
        visitor_btns.add(button)
        user32.SetCursorPos(gx, gy)
        time.sleep(0.01)
        send_mouse(down_f, data)
    elif button in visitor_btns:
        visitor_btns.discard(button)
        user32.SetCursorPos(gx, gy)
        send_mouse(up_f, data)
        if not visitor_btns and saved:
            time.sleep(0.03)
            user32.SetCursorPos(*saved)
            saved = None
    replaying = bool(visitor_btns)


def visitor_scroll(delta, horizontal):
    global replaying
    if not visiting:
        return
    replaying = True
    s = get_cursor()
    user32.SetCursorPos(round(mx), round(my))
    time.sleep(0.01)
    send_mouse(MOUSEEVENTF_HWHEEL if horizontal else MOUSEEVENTF_WHEEL, delta)
    time.sleep(0.02)
    user32.SetCursorPos(*s)
    replaying = bool(visitor_btns)

# ----------------------- Server creation ---------------------------

port = 9999
bufferSize = 1024

server = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
server.bind(("", port))

# --------------------- Build Ghost Cursor -------------------------

GWL_EXSTYLE = -20
WS_EX_LAYERED     = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW  = 0x00000080
WS_EX_NOACTIVATE  = 0x08000000

CURSORS_DIR = Path(__file__).resolve().parent / "assets" / "cursors"
CURSORS = {                     # cursor choice -> (image file, name tag colour)
    "flower": ("flower_cursor_48.png", "#eef43f"),
    "frog":   ("frog_cursor_48.png",   "#ef3f3f"),
}
DEFAULT_CURSOR = "flower"

CURSOR_HEIGHT = 32
HOTSPOT = (0, 0)
KEY = "#010203"
ALPHA_THRESHOLD = 128

root = tk.Tk()
root.overrideredirect(True)
root.attributes("-topmost", True)
root.config(bg = KEY)
root.geometry("+-4000+-4000")

canvas = tk.Canvas(root, bg=KEY, highlightthickness=0)
canvas.pack()

cursor_img = None

def build_cursor(ghost_name, cursor):
    global cursor_img
    png, color = CURSORS.get(cursor, CURSORS[DEFAULT_CURSOR])
    img = Image.open(CURSORS_DIR / png).convert("RGBA")
    scale = CURSOR_HEIGHT/img.height
    img = img.resize((round(img.width * scale), CURSOR_HEIGHT), Image.LANCZOS)
    if ALPHA_THRESHOLD is not None:
        r, g, b, a = img.split()
        img.putalpha(a.point(lambda v: 255 if v >= ALPHA_THRESHOLD else 0))
    cursor_img = ImageTk.PhotoImage(img)

    canvas.delete("all")
    canvas.create_image(0, 0, image = cursor_img, anchor = "nw")
    text = canvas.create_text(cursor_img.width() * 0.6 + 5, cursor_img.height() + 2,
                              text= ghost_name, fill = "white", font= ("Segoe UI", 9, "bold"), anchor="nw")
    x0, y0, x1, y1 = canvas.bbox(text)
    pill = canvas.create_rectangle(x0 - 5, y0 - 2, x1 + 5, y1 + 2, fill=color, outline=color)
    canvas.tag_lower(pill, text)
    _, _, x1, y1 = canvas.bbox("all")
    canvas.config(width=x1 + 1, height=y1 + 1)

root.update_idletasks()
hwnd = user32.GetParent(root.winfo_id())

style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

root.attributes("-transparentcolor", KEY)

#---------------------- Mouse filter ------------------------------

press_down = set()
blocked_down = set()

def normalized(dx, dy):
    return dx / (W - 1), dy / (H - 1)

def mouse_filter(msg, data):
    global reached, parked

    if data.flags & LLMHF_INJECTED:      # injected input (the visitor's replayed clicks/scrolls): never touch it
        return

    if msg in BUTTON_MSGS:
        b, down = BUTTON_MSGS[msg]
        if b == "x":
            b += str((data.mouseData >> 16) & 0xFFFF)

        if down:
            if reached:
                blocked_down.add(b)
                send({"t": "click_down", "button": b})
                mouse_listener.suppress_event()
            press_down.add(b)
            return

        if b in press_down:
            press_down.discard(b)
            return
        if b in blocked_down:
            blocked_down.discard(b)
            send({"t": "click_up", "button": b})
            mouse_listener.suppress_event()
        return

    if msg in WHEEL_MSGS and reached:
        delta = ctypes.c_short((data.mouseData >> 16) & 0xFFFF).value
        send({"t": "scroll", "d": delta, "h": msg == 0x020E})
        mouse_listener.suppress_event()

    if msg == WM_MOUSEMOVE:
        if not reached:
            at_edge = (data.pt.x >= W-1 and side == "right") or (data.pt.x <= 0 and side == "left")
            if at_edge and not replaying:
                park_x = W - 1 - PARK_MARGIN if side == "right" else PARK_MARGIN
                parked = (park_x, data.pt.y)
                ctypes.windll.user32.SetCursorPos(*parked)
                reached = True
                hide_cursor()
                send({"t": "join", "x": 0 if side == "right" else 1, "y": data.pt.y/(H-1)})
                mouse_listener.suppress_event()
            return

        cx, cy = get_cursor()
        dx = data.pt.x - cx
        dy = data.pt.y - cy
        ndx, ndy = normalized(dx, dy)
        send({"t": "move", "dx": ndx, "dy": ndy})

        mouse_listener.suppress_event()

    return

#-------------- keyboards thread -------------------------

def on_press(key):
    global reached
    if key == HOLD_KEY and reached:
        for b in list(blocked_down):
            send({"t": "click_up", "button": b})
        blocked_down.clear()
        reached = False
        show_cursor()
        send({"t": "panic"})
        user32.SetCursorPos(round(0.5 * (W - 1)), round(0.5 * (H - 1)))

# ------------ movement + housekeeping ----------------

def place(x, y):
    root.geometry(f"+{round(x) - HOTSPOT[0]}+{round(y) - HOTSPOT[1]}")

last_lift = 0.0
mx = my = 0
visiting = False

def follow():
    global last_lift, mx, my, visiting
    latest = None
    sum_dx = sum_dy = 0

    try:
        while True:
            msg = log.get_nowait()
            if msg[0] == "connect":
                build_cursor(msg[1], msg[2])
            elif msg[0] == "join":
                visiting = True
                latest = msg[1:]
            elif msg[0] == "move":
                sum_dx += msg[1] * (W-1)
                sum_dy += msg[2] * (H-1)
            elif msg[0] == "panic":
                visiting = False
                latest = None
                root.geometry("+-4000+-4000")

    except queue.Empty:
        pass

    if latest is not None:
        mx, my = latest
        place(mx, my)

    if visiting and (sum_dx or sum_dy):
        mx += sum_dx
        my += sum_dy

    going_home = (mx < 0 and side == "left") or (mx > W - 1 and side == "right")

    my = min(max(my, 0), H - 1)
    if side == "left":
        mx = min(mx, W - 1)
    else:
        mx = max(mx, 0)

    if going_home and visiting:
        visiting = False
        root.geometry("+-4000+-4000")
        release_visitor()
        send({"t": "return", "y": my / (H - 1)})
    elif visiting:
        place(mx, my)
        if visitor_btns:
            user32.SetCursorPos(round(mx), round(my))

    now = time.time()
    if now -last_lift > 1:
        root.attributes("-topmost", True)
        root.lift()
        last_lift = now

    root.after(16, follow)

def release_visitor():
    global saved, replaying
    for b in list(visitor_btns):
        send_mouse(MOUSE_FLAGS[b][1], MOUSE_FLAGS[b][2])
    visitor_btns.clear()
    if saved:
        user32.SetCursorPos(*saved)
        saved = None
    replaying = False

# ---------------------- Send and Receive UDP server -------------------

def send(msg):
    server.sendto(json.dumps(msg).encode(), (otherIp,port))

def receive():
    global reached
    while True:
        try:
            data, addr = server.recvfrom(bufferSize)
            msg = json.loads(data)
            t = msg["t"]
            if t == "connect":
                log.put(("connect", msg["name"], msg.get("cursor", DEFAULT_CURSOR)))
                if not msg.get("reply"):
                    send({"t": "connect", "name": name, "cursor": my_cursor, "reply": True})
            if t == "join":
                log.put(("join", msg["x"] * (W-1), msg["y"] * (H-1)))
            if t == "move":
                log.put(("move", msg["dx"], msg["dy"]))
            if t == "return":
                for b in list(blocked_down):
                    send({"t": "click_up", "button": b})
                blocked_down.clear()
                reached = False
                show_cursor()
                edge_x = W - 10 if side == "right" else 10       # 10 px inside, so it doesn't re-trigger "reached"
                user32.SetCursorPos(edge_x, round(msg["y"] * (H - 1)))
            if t == "click_down":
                visitor_button(msg["button"], True)
            if t == "click_up":
                visitor_button(msg["button"], False)
            if t == "scroll":
                visitor_scroll(msg["d"], msg["h"])
            if t == "panic":
                release_visitor()
                print("PANIC BUTTON WAS PRESSED")
                log.put(("panic",))

        except ConnectionError:
            pass
        except Exception as e:
            print("error: ", e)


# --------------------------- Main ------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="GhostCursor: move your cursor onto the other machine and control it as a ghost "
                    "cursor, while both machines stay independent of each other."
    )

    parser.add_argument(
        "-s", "--side", metavar="side", required=True, choices=["right", "left"],
        help="which side the other machine is on (right or left)"
    )

    parser.add_argument(
        "-ip", "--otherIp", metavar="otherIp", required=True,
        help="IP address of the other machine"
    )

    args = parser.parse_args()
    side = args.side
    otherIp = args.otherIp

    name = input("What's your name?: ").strip()
    my_cursor = input(f"Choose your cursor ({'/'.join(CURSORS)}): ").strip().lower()
    if my_cursor not in CURSORS:
        my_cursor = DEFAULT_CURSOR

    t = threading.Thread(target=receive, daemon=True)
    t.start()

    mouse_listener = mouse.Listener(win32_event_filter = mouse_filter)
    kb_listener = keyboard.Listener(on_press=on_press)
    mouse_listener.start()
    kb_listener.start()

    signal.signal(signal.SIGINT, lambda *_: root.destroy())
    send({"t": "connect", "name": name, "cursor": my_cursor})
    follow()

    try:
        root.mainloop()
    finally:
        show_cursor()                     # always give the real cursor back, even after a crash
        server.close()
        mouse_listener.stop()
        kb_listener.stop()
