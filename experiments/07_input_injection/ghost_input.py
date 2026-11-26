import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)

from ctypes import wintypes
import time

user32 = ctypes.windll.user32

W = user32.GetSystemMetrics(0)
H = user32.GetSystemMetrics(1)

c_x = round(0.5 * (W - 1))      # target: centre of the screen
c_y = round(0.5 * (H - 1))

# ----------------------- SendInput -------------------------------
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

class INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]

MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP   = 0x0010

def send_mouse(flags):
    inp = INPUT(type=0)                                    # 0 = mouse input
    inp.u.mi = MOUSEINPUT(0, 0, 0, flags, 0, 0)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

# ----------------------- cursor helpers --------------------------
def get_cursor():
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def click_at(x, y):
    saved = get_cursor()
    user32.SetCursorPos(x, y)
    time.sleep(0.01)                  # let the move register
    send_mouse(MOUSEEVENTF_RIGHTDOWN)
    time.sleep(0.05)
    send_mouse(MOUSEEVENTF_RIGHTUP)
    time.sleep(0.03)                  # let the click land BEFORE moving back
    user32.SetCursorPos(*saved)

# ----------------------- main ------------------------------------
if __name__ == "__main__":
    print(f"Right-clicking at the centre ({c_x}, {c_y}) every 5 s. Ctrl+C to stop.")
    try:
        while True:
            time.sleep(5)
            click_at(c_x, c_y)
            print("clicked")
    except KeyboardInterrupt:
        print("stopped")
