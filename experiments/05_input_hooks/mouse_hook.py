import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)      # pt coordinates in real pixels

import queue
import threading
import time
from ctypes import wintypes
from pynput import mouse

# ---------------- Windows message codes (what kind of event) ----------------
WM_MOUSEMOVE   = 0x0200
WM_MOUSEWHEEL  = 0x020A
WM_MOUSEHWHEEL = 0x020E
WM_XBUTTONDOWN = 0x020B
WM_XBUTTONUP   = 0x020C

WM_NAMES = {
    0x0200: "MOVE",
    0x0201: "LEFT DOWN",   0x0202: "LEFT UP",
    0x0204: "RIGHT DOWN",  0x0205: "RIGHT UP",
    0x0207: "MIDDLE DOWN", 0x0208: "MIDDLE UP",
    0x020A: "WHEEL",       0x020E: "H-WHEEL",
    0x020B: "X DOWN",      0x020C: "X UP",
}

LLMHF_INJECTED = 0x01        # flag bit: "this event was faked by software"
SHOW_MOVES = False           # True = print every real move too (floods the terminal)

# ---------------- SendInput: create a REAL (fake) mouse event ----------------
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

class INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]

MOUSEEVENTF_MOVE = 0x0001    # relative move (a vector), like a real mouse

def fake_move(dx, dy):
    inp = INPUT(type=0)                                    # 0 = mouse input
    inp.u.mi = MOUSEINPUT(dx, dy, 0, MOUSEEVENTF_MOVE, 0, 0)
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

# ---------------- the hook filter: runs INSIDE Windows' hook ----------------
events = queue.Queue()

def mouse_filter(msg, data):

    events.put((msg, data.pt.x, data.pt.y, data.mouseData, data.flags, data.time))
    # returning nothing = the event continues normally to Windows and apps

# ---------------- helpers ----------------
def hiword_signed(value):
    """Top 16 bits of a 32-bit number, read as a signed number (can be negative)."""
    return ctypes.c_short((value >> 16) & 0xFFFF).value

def describe(msg, x, y, mdata, flags, t):
    name = WM_NAMES.get(msg, "OTHER")
    extra = ""
    if msg in (WM_MOUSEWHEEL, WM_MOUSEHWHEEL):
        d = hiword_signed(mdata)
        extra = f"  delta={d:+d} ({d / 120:+.2f} notches)"
    elif msg in (WM_XBUTTONDOWN, WM_XBUTTONUP):
        extra = f"  button=X{hiword_signed(mdata)}"          # X1 = back, X2 = forward
    inj = "  [INJECTED]" if flags & LLMHF_INJECTED else ""
    return f"t={t:>10}  msg={msg:#06x}  {name:<11}  pt=({x:5d},{y:5d}){extra}{inj}"

# ---------------- optional test: a fake move every 5 s ----------------
def injector():
    while True:
        time.sleep(5)
        fake_move(40, 0)      # SendInput -> arrives in the hook flagged [INJECTED]

# ---------------- main ----------------
listener = mouse.Listener(win32_event_filter=mouse_filter)
listener.start()
threading.Thread(target=injector, daemon=True).start()
print("Hook running. Move, click, scroll, use side buttons. Ctrl+C to quit.\n")

moves, last_report = 0, time.time()
try:
    while True:
        try:
            ev = events.get(timeout=0.2)          # wait a bit, so Ctrl+C still works
        except queue.Empty:
            ev = None

        if ev:
            msg, flags = ev[0], ev[4]
            if msg == WM_MOUSEMOVE:
                moves += 1
                if SHOW_MOVES or flags & LLMHF_INJECTED:
                    print(describe(*ev))
            else:
                print(describe(*ev))

        now = time.time()
        if now - last_report >= 1:
            if moves:
                print(f"   ... {moves} move events in the last second")
            moves, last_report = 0, now
except KeyboardInterrupt:
    pass
finally:
    listener.stop()
    print("Hook removed.")
