import ctypes
import ctypes.wintypes
import time

user32 = ctypes.windll.user32

def screen_size():
    # GetSystemMetrics(0) = SM_CXSCREEN (width), (1) = SM_CYSCREEN (height) of the PRIMARY monitor
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

def cursor_pos():
    pt = ctypes.wintypes.POINT()               # a C struct with .x and .y
    user32.GetCursorPos(ctypes.byref(pt))      # Windows fills it in (we pass a pointer)
    return pt.x, pt.y

# --- 1. Before DPI awareness ---
print("Screen size (DPI-UNAWARE):", screen_size())
print("Move your mouse to the BOTTOM-RIGHT corner... (3 s)")
time.sleep(3)
print("Cursor at corner (DPI-UNAWARE):", cursor_pos())

# --- 2. Turn DPI awareness on ---
ctypes.windll.shcore.SetProcessDpiAwareness(2)   # 2 = per-monitor aware

print("\nScreen size (DPI-AWARE):", screen_size())
print("Keep the mouse in the corner... (3 s)")
time.sleep(3)
print("Cursor at corner (DPI-AWARE):", cursor_pos())