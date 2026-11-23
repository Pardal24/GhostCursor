import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)

import threading
import socket
from pynput import mouse
import tkinter as tk
import queue
import time
import signal
import json
from PIL import Image, ImageTk
from pathlib import Path

#-------------------- Setup ---------------------------
CURSORS_DIR = Path(__file__).resolve().parents[2] / "assets" / "cursors"
CURSORS = {                     # cursor choice -> (image file, name tag colour)
    "flower": ("flower_cursor_48.png", "#eef43f"),
    "frog":   ("frog_cursor_48.png",   "#ef3f3f"),
}
DEFAULT_CURSOR = "flower"

name = input("What's your name?: ").strip()
otherIp = input("What's the IP you want to connect?: ").strip()
my_cursor = input(f"Choose your cursor ({'/'.join(CURSORS)}): ").strip().lower()
if my_cursor not in CURSORS:
    my_cursor = DEFAULT_CURSOR

CURSOR_HEIGHT = 32
HOTSPOT = (0, 0)
KEY = "#010203"
ALPHA_THRESHOLD = 128
OFFSET = (0, 0)

# ---------------- Win32 constants ----------------
user32 = ctypes.windll.user32
GWL_EXSTYLE       = -20          # "which property": the extended window style
WS_EX_LAYERED     = 0x00080000   # window can be transparent (Tk's -transparentcolor already uses this)
WS_EX_TRANSPARENT = 0x00000020   # with LAYERED: mouse clicks pass THROUGH the window
WS_EX_TOOLWINDOW  = 0x00000080   # no taskbar button, not in Alt+Tab
WS_EX_NOACTIVATE  = 0x08000000   # window never takes keyboard focus

W = user32.GetSystemMetrics(0)
H = user32.GetSystemMetrics(1)

root = tk.Tk()
root.overrideredirect(True)
root.attributes("-topmost",True)
root.config(bg=KEY)
root.geometry("+-4000+-4000")
canvas = tk.Canvas(root, bg=KEY, highlightthickness=0)
canvas.pack()

cursor_img = None

def build_ghost(ghost_name, cursor):
    """Draw the other person's cursor image + name tag (called when their 'join' arrives)."""
    global cursor_img                             # keep a reference, or Tk drops the image
    png, color = CURSORS.get(cursor, CURSORS[DEFAULT_CURSOR])
    img = Image.open(CURSORS_DIR / png).convert("RGBA")
    scale = CURSOR_HEIGHT/img.height
    img = img.resize((round(img.width * scale), CURSOR_HEIGHT), Image.LANCZOS)
    if ALPHA_THRESHOLD is not None:
        r, g, b, a = img.split()
        img.putalpha(a.point(lambda v: 255 if v >= ALPHA_THRESHOLD else 0))
    cursor_img = ImageTk.PhotoImage(img)

    canvas.delete("all")
    canvas.create_image(0, 0, image=cursor_img, anchor="nw")
    text = canvas.create_text(cursor_img.width() * 0.6 + 5, cursor_img.height() + 2,
                              text=ghost_name, fill="white", font=("Segoe UI", 9, "bold"), anchor="nw")
    x0, y0, x1, y1 = canvas.bbox(text)
    pill = canvas.create_rectangle(x0 - 5, y0 - 2, x1 + 5, y1 + 2, fill=color, outline=color)
    canvas.tag_lower(pill, text)
    _, _, x1, y1 = canvas.bbox("all")
    canvas.config(width=x1 + 1, height=y1 + 1)

root.update_idletasks()                           # make sure the real Windows window exists now
hwnd = user32.GetParent(root.winfo_id())          # the HWND of the top-level window

style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)  # 1. read current flags
style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE   # 2. add ours
user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)   # 3. write them back

root.attributes("-transparentcolor", KEY)         # (re)apply colour key AFTER changing styles


#--------------- Create connection --------------------
port = 9999
bufferSize = 1024

server = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
server.bind(("", port))

# ------------ movement + housekeeping ----------------
def place(x, y):
    root.geometry(f"+{x - HOTSPOT[0]}+{y - HOTSPOT[1]}")

start = time.time()
last_lift = 0.0

def follow():
    global last_lift
    latest = None
    try:
        while True:
            item = q.get_nowait()
            if item[0] == "join":                 # Tk is not thread-safe: draw here, not in receive()
                build_ghost(item[1], item[2])
            else:
                latest = item[1:]
    except queue.Empty:
        pass

    if latest is not None:
        mx, my = latest
        place(mx + OFFSET[0], my + OFFSET[1])

    now = time.time()
    if now - last_lift > 1:                       # re-claim "on top" once per second
        root.attributes("-topmost", True)
        root.lift()
        last_lift = now
    root.after(16, follow)

# ------------- Mouse Positions -----------------------

q = queue.Queue()

def send(msg):
    server.sendto(json.dumps(msg).encode(), (otherIp, port))

def normalized(x,y):
    nx = x / (W-1)
    ny = y / (H-1)
    return min(max(nx, 0.0), 1.0), min(max(ny, 0.0), 1.0)

def on_move(x,y):
    nx, ny = normalized(x,y)
    send({"t": "move", "x": nx, "y": ny})

def receive():
    while True:
        try:
            data, addr = server.recvfrom(bufferSize)
            msg = json.loads(data)
            t = msg["t"]
            if t == "join":
                print(f"{msg['name']} joined!")
                q.put(("join", msg["name"], msg.get("cursor", DEFAULT_CURSOR)))
                if not msg.get("reply"):          # answer once, so whoever started first also learns our name
                    send({"t": "join", "name": name, "cursor": my_cursor, "reply": True})
            elif t == "chat":
                print(f"{msg['name']}: {msg['text']}")
            elif t == "move":
                x = round(msg['x'] * (W - 1))
                y = round(msg['y'] * (H - 1))
                q.put(("move", x, y))

        except ConnectionResetError:
            pass
        except Exception as e:
            print("error:", e)

t = threading.Thread(target=receive, daemon=True)
t.start()

listener = mouse.Listener(
    on_move=on_move)
listener.start()

signal.signal(signal.SIGINT, lambda *_: root.destroy())
send({"t": "join", "name": name, "cursor": my_cursor})
follow()
root.mainloop()

listener.stop()
server.close()
