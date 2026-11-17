import tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk

# ---------------- settings ----------------
CURSOR_PNG = Path(__file__).parent / "flower_cursor_48.png"
CURSOR_HEIGHT = 32          # final size on screen, in pixels
HOTSPOT = (0, 0)            # pixel in the RESIZED image where the "tip" is (top-left for a classic arrow)
NAME = "Bela"
COLOR = "#ff5fa2"
W, H = 500, 350             # canvas size for this test

# ---------------- window + canvas ----------------
root = tk.Tk()
root.title("3.1 - ghost cursor drawing")
canvas = tk.Canvas(root, width=W, height=H, bg="#202020", highlightthickness=0)
canvas.pack()

# ---------------- load + resize the PNG ----------------
img = Image.open(CURSOR_PNG).convert("RGBA")              # RGBA = keep transparency
scale = CURSOR_HEIGHT / img.height
img = img.resize((round(img.width * scale), CURSOR_HEIGHT), Image.LANCZOS)
cursor_img = ImageTk.PhotoImage(img)                      # must exist AFTER tk.Tk(); keep this variable alive!

# ---------------- build the ghost (image + name tag) ----------------
def build_ghost(x, y):
    """Draw the ghost so that its TIP (hotspot) is at canvas point (x, y)."""
    canvas.delete("ghost")
    left, top = x - HOTSPOT[0], y - HOTSPOT[1]
    canvas.create_image(left, top, image=cursor_img, anchor="nw", tags="ghost")
    text = canvas.create_text(left + cursor_img.width() * 0.6, top + cursor_img.height(),
                              text=NAME, fill="white", font=("Segoe UI", 9, "bold"),
                              anchor="nw", tags="ghost")
    x0, y0, x1, y1 = canvas.bbox(text)
    pill = canvas.create_rectangle(x0 - 5, y0 - 2, x1 + 5, y1 + 2,
                                   fill=COLOR, outline=COLOR, tags="ghost")
    canvas.tag_lower(pill, text)                           # pill behind the text

build_ghost(60, 60)

# ---------------- click = put the TIP exactly where you clicked ----------------
def on_click(event):
    canvas.delete("marker")
    canvas.create_oval(event.x - 2, event.y - 2, event.x + 2, event.y + 2,
                       fill="red", outline="", tags="marker")   # red dot = target
    build_ghost(event.x, event.y)

canvas.bind("<Button-1>", on_click)

# ---------------- after(): bounce around (practice for live movement) ----------------
dx, dy = 3, 2
bouncing = True

def animate():
    global dx, dy
    if bouncing:
        canvas.move("ghost", dx, dy)                       # move ALL items tagged "ghost"
        x0, y0, x1, y1 = canvas.bbox("ghost")
        if x0 <= 0 or x1 >= W: dx = -dx
        if y0 <= 0 or y1 >= H: dy = -dy
    root.after(16, animate)                                # call me again in ~16 ms (~60 fps)

def toggle_bounce(event):
    global bouncing
    bouncing = not bouncing

root.bind("<space>", toggle_bounce)
animate()
root.mainloop()