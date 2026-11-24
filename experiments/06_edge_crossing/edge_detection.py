import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)

from pynput import mouse
import queue


W = ctypes.windll.user32.GetSystemMetrics(0)
H = ctypes.windll.user32.GetSystemMetrics(1)

WM_MOUSEMOVE = 0x0200

log = queue.Queue()
reached = False

def mouse_filter(msg, data):
    global reached

    if msg == WM_MOUSEMOVE:
        if data.pt.x >= W - 1 and not reached and side == "right":
            log.put("REACHED")
            reached = True
            return
        if data.pt.x <= 0 and not reached and side == "left":
            log.put("REACHED")
            reached = True
            return
        if reached and 20 < data.pt.x < W - 21:
            reached = False

    return


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description= "What side are you on"
    )

    parser.add_argument(
        "-s", "--side", metavar="side",
        required=True, choices = ["right", "left"],
        help = "which side the other laptop is on"
    )

    args = parser.parse_args()
    side = args.side

    mouse_listener = mouse.Listener(win32_event_filter = mouse_filter)
    mouse_listener.start()


    try:
        while True:
            try:
                print(log.get(timeout=0.2))
            except queue.Empty:
                pass
    except KeyboardInterrupt:
        pass
    finally:
        mouse_listener.stop()
