import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)

import time
import queue
from pynput import keyboard,mouse

WM_MOUSEMOVE = 0x0200
BUTTON_MSGS = {                         # code -> (button, is_down)
    0x0201: ("left", True),   0x0202: ("left", False),
    0x0204: ("right", True),  0x0205: ("right", False),
    0x0207: ("middle", True), 0x0208: ("middle", False),
    0x020B: ("x", True),      0x020C: ("x", False),
}
WHEEL_MSGS = {0x020A, 0x020E}
LLMHF_INJECTED = 0x01

HOLD_KEY = keyboard.Key.f8
MAX_HOLD = 10

blocking = False
blocking_start = 0.0
press_down = set()
blocked_down = set()
log = queue.Queue()

def mouse_filter(msg, data):

    if msg == WM_MOUSEMOVE:
        return

    active = blocking and (time.time() - blocking_start) < MAX_HOLD

    if msg in BUTTON_MSGS:
        b, down = BUTTON_MSGS[msg]
        if b == "x":
            b += str((data.mouseData >> 16) & 0xFFFF)

        if down:
            if active:
                blocked_down.add(b)
                log.put(f"Blocked {b} down")
                mouse_listener.suppress_event()
            press_down.add(b) # if reaches here it's because is not active bc suppress blocks everythin down
            return

        if b in press_down:
            press_down.discard(b)
            return
        if b in blocked_down:
            blocked_down.discard(b)
            log.put(f"Blocked {b} up")
            mouse_listener.suppress_event()
        return

    if msg in WHEEL_MSGS and active:
        log.put("Blocked scroll")
        mouse_listener.suppress_event()


#--------------- Keyboard callbacks---------------

def on_press(key):
    global blocking, blocking_start
    if key == HOLD_KEY and not blocking:
        blocking = True
        blocking_start = time.time()
        log.put("F8 held: Blocking Started")


def on_release(key):
    global blocking
    if key == HOLD_KEY and blocking:
        blocking = False
        log.put("F8 released: Blocking Stopped")


# ----------------- Main ------------------------

mouse_listener = mouse.Listener(win32_event_filter=mouse_filter)
kb_listener = keyboard.Listener(on_press= on_press, on_release= on_release)
mouse_listener.start()
kb_listener.start()
print(f"Hold F8 to block clicks (max {MAX_HOLD}s). Ctrl+C here to quit.\n")

warned = False
try:
    while True:
        try:
            print(log.get(timeout=0.2))
        except queue.Empty:
            pass

        if (blocking and time.time() - blocking_start >= MAX_HOLD and not warned):
            log.put("!!! safety limit reached: clicks allowed again (release F8)")
            warned = True
        if not blocking:
            warned = False

except KeyboardInterrupt:
    pass

finally:
    mouse_listener.stop()
    kb_listener.stop()
