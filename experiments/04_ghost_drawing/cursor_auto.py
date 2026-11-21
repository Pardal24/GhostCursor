import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)

import threading
from pynput import mouse
import tkinter as tk
import queue
import time
from PIL import Image, ImageTk
from pathlib import Path
import ctypes.wintypes
import signal
import random
import math

# ---------------- settings ----------------
CURSOR_PNG = Path(__file__).resolve().parents[2] / "assets" / "cursors" / "flower_cursor_48.png"
CURSOR_HEIGHT = 32
HOTSPOT = (0, 0)
NAME = "Bela"
COLOR = "#ff5fa2"
KEY = "#010203"
ALPHA_THRESHOLD = 128
OFFSET = (0, 0)
RUN_SECONDS = 120

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
canvas = tk.Canvas(root, bg=KEY, highlightthickness=0)
canvas.pack()

img = Image.open(CURSOR_PNG).convert("RGBA")
scale = CURSOR_HEIGHT/img.height
img = img.resize((round(img.width * scale), CURSOR_HEIGHT), Image.LANCZOS)
if ALPHA_THRESHOLD is not None:
    r, g, b, a = img.split()
    img.putalpha(a.point(lambda v: 255 if v >= ALPHA_THRESHOLD else 0))
cursor_img = ImageTk.PhotoImage(img)

canvas.create_image(0, 0, image=cursor_img, anchor="nw")
text = canvas.create_text(cursor_img.width() * 0.6 + 5, cursor_img.height() + 2,
                          text=NAME, fill="white", font=("Segoe UI", 9, "bold"), anchor="nw")
x0, y0, x1, y1 = canvas.bbox(text)
pill = canvas.create_rectangle(x0 - 5, y0 - 2, x1 + 5, y1 + 2, fill=COLOR, outline=COLOR)
canvas.tag_lower(pill, text)
_, _, x1, y1 = canvas.bbox("all")
canvas.config(width=x1 + 1, height=y1 + 1)

# ---------------- NEW: make it click-through ----------------

root.update_idletasks()                           # make sure the real Windows window exists now
hwnd = user32.GetParent(root.winfo_id())          # the HWND of the top-level window

style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)  # 1. read current flags
style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE   # 2. add ours
user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)   # 3. write them back

root.attributes("-transparentcolor", KEY)         # (re)apply colour key AFTER changing styles

# check it worked
style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
print(f"HWND = {hwnd:#x}, extended style = {style:#010x}")
print("click-through:", bool(style & WS_EX_TRANSPARENT), "| no-activate:", bool(style & WS_EX_NOACTIVATE))

#-------------------- Mouse pos generator ---------------------
q = queue.Queue()
def mouse_pos():
    t0 = time.time()
    while True:
        t = time.time() - t0
        x = int(W / 2 + (W / 3) * math.cos(t))      # a circle, one lap every ~6 s
        y = int(H / 2 + (H / 3) * math.sin(t))
        q.put((x, y))
        time.sleep(0.005)   

t = threading.Thread(target=mouse_pos, daemon=True)
t.start()

# ---------------- movement + housekeeping ----------------
def place(x, y):
    root.geometry(f"+{x - HOTSPOT[0]}+{y - HOTSPOT[1]}")

start = time.time()
last_lift = 0.0

def follow():
    global last_lift
    latest = None
    try:
        while True:
            latest = q.get_nowait()
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
    if now - start > RUN_SECONDS:
        root.destroy()
        return
    root.after(16, follow)


# you can't click the ghost anymore -> close it with Ctrl+C in the terminal (or wait)
signal.signal(signal.SIGINT, lambda *_: root.destroy())
follow()
root.mainloop()