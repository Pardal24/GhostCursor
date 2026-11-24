import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)

import queue
from pynput import mouse, keyboard

W = ctypes.windll.user32.GetSystemMetrics(0)
H = ctypes.windll.user32.GetSystemMetrics(1)

WM_MOUSEMOVE = 0x0200

HOLD_KEY = keyboard.Key.f8
PARK_MARGIN = 200


log = queue.Queue()
reached = False
park = (0,0)
panic = False



def mouse_filter (msg, data):
    global reached, park

    if msg != WM_MOUSEMOVE:
        return

    if not reached:
        at_edge = ( side == "right" and data.pt.x >= (W - 1)) or (side == "left" and data.pt.x <= 0)
        if at_edge:
            log.put(("reach",))
            park_x = W - 1 - PARK_MARGIN if side == "right" else PARK_MARGIN
            park=(park_x, data.pt.y)
            ctypes.windll.user32.SetCursorPos(*park)
            reached = True
            mouse_listener.suppress_event()
        return

    dx = data.pt.x - park[0]
    dy = data.pt.y - park[1]
    log.put(("delta", dx, dy))
    mouse_listener.suppress_event()


    return

def on_press(key):
    global reached
    if key == HOLD_KEY and reached:
        reached = False
        log.put(("panic",))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description= "Send your cursor to the other computer in your right/left side"
    )

    parser.add_argument(
        "-s", "--side", metavar="side",
        required=True, choices=["right","left"],
        help = "which side the other laptop is on (right or left)"
    )

    args = parser.parse_args()
    side = args.side

    mouse_listener = mouse.Listener(win32_event_filter = mouse_filter)
    kb_listener = keyboard.Listener(on_press=on_press)
    mouse_listener.start()
    kb_listener.start()

    total_x = total_y = 0
    try:
        while True:
            try:
                msg = log.get(timeout=0.02)
            except queue.Empty:
                continue
            if msg[0] == "reach":
                total_x = total_y = 0
                print("REACHED: cursor parked")
            elif msg[0] == "delta":
                _, dx, dy = msg
                total_x += dx
                total_y += dy
                print(f"delta ({dx:+4d},{dy:+4d})   total ({total_x:+6d},{total_y:+6d})")
            elif msg[0] == "panic":
                print("PANIC: cursor released")

    except KeyboardInterrupt:
        pass

    finally:
        mouse_listener.stop()
        kb_listener.stop()
