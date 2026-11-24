import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)

import socket
import queue
from pynput import mouse, keyboard
import threading
import json
from PIL import Image, ImageTk
from pathlib import Path
import tkinter as tk
import time
import signal


#-------------------- Setup Ghost Cursor ---------------------------
CURSORS_DIR = Path(__file__).resolve().parents[2] / "assets" / "cursors"
CURSORS = {                     # cursor choice -> (image file, name tag colour)
    "flower": ("flower_cursor_48.png", "#eef43f"),
    "frog":   ("frog_cursor_48.png",   "#ef3f3f"),
}
DEFAULT_CURSOR = "flower"

CURSOR_HEIGHT = 32
HOTSPOT = (0, 0)
KEY = "#010203"
ALPHA_THRESHOLD = 128

#----------------------- Windows Constants --------------------------
user32 = ctypes.windll.user32
GWL_EXSTYLE = -20
WS_EX_LAYERED     = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW  = 0x00000080
WS_EX_NOACTIVATE  = 0x08000000

WM_MOUSEMOVE = 0x0200

W = user32.GetSystemMetrics(0)
H = user32.GetSystemMetrics(1)

PARK_MARGIN = 200
HOLD_KEY = keyboard.Key.f8


log = queue.Queue()
parked = (0,0)
reached = False

#----------------------- Tkinter ------------------------------

root = tk.Tk()
root.overrideredirect(True)
root.attributes("-topmost", True)
root.config(bg=KEY)
root.geometry("+-4000+-4000")

canvas = tk.Canvas(root, bg = KEY, highlightthickness= 0)
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

#------------------------ Server Settings -------------------------
port = 9999
bufferSize = 1024

server = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
server.bind(("", port))

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
        send({"t": "return", "y": my / (H - 1)})
    elif visiting:
        place(mx, my)

    now = time.time()
    if now -last_lift > 1:
        root.attributes("-topmost", True)
        root.lift()
        last_lift = now

    root.after(16, follow)


#---------------------- Mouse filter ------------------------------

def normalized(dx, dy):
    return dx / (W - 1), dy / (H - 1)

def mouse_filter(msg, data):
    global reached, parked

    if msg != WM_MOUSEMOVE:
        return

    if not reached:
        at_edge = (data.pt.x >= W-1 and side == "right") or (data.pt.x <= 0 and side == "left")
        if at_edge:
            park_x = W - 1 - PARK_MARGIN if side == "right" else PARK_MARGIN
            parked = (park_x, data.pt.y)
            ctypes.windll.user32.SetCursorPos(*parked)
            reached = True
            send({"t": "join", "x": 0 if side == "right" else 1, "y": data.pt.y/(H-1)})
            mouse_listener.suppress_event()
        return

    dx = data.pt.x - parked[0]
    dy = data.pt.y - parked[1]
    ndx, ndy = normalized(dx, dy)
    send({"t": "move", "dx": ndx, "dy": ndy})

    mouse_listener.suppress_event()

    return

#-------------- keyboards thread -------------------------

def on_press(key):
    global reached
    if key == HOLD_KEY and reached:
        reached = False
        send({"t": "panic"})
        user32.SetCursorPos(round(0.5 * (W - 1)), round(0.5 * (H - 1)))


#--------------------- Receive and Send UDP msg --------------------------------

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
                reached = False
                edge_x = W - 10 if side == "right" else 10       # 10 px inside, so it doesn't re-trigger "reached"
                user32.SetCursorPos(edge_x, round(msg["y"] * (H - 1)))
            if t == "panic":
                print("PANIC BUTTON WAS PRESSED")
                log.put(("panic",))

        except ConnectionError:
            pass
        except Exception as e:
            print("error: ", e)

# -------------------- Main ------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description= "Pass the cursor from one laptop to the other"
    )

    parser.add_argument(
        "-s", "--side", metavar="side",
        required=True, choices=["right","left"],
        help="in which side is the other laptop (right or left)"
    )
    parser.add_argument(
        "-ip", "--otherIp", metavar="otherIp",
        required=True,
        help="What's the IP you want to connect?"
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

    root.mainloop()

    server.close()
    mouse_listener.stop()
    kb_listener.stop()
