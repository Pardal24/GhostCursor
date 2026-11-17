# GhostCursor

Share one mouse and keyboard across two computers on the same local network, using UDP.

## Final goal

- Two machines sit side by side, each running GhostCursor.
- Move the cursor off the **left** edge of machine 1 and it shows up on machine 2 as a **ghost cursor** with the user's name under it.
- While the ghost cursor is on machine 2 it works like a normal cursor: open apps, type in the browser, and so on.
- It works in both directions: move off the **right** edge of machine 2 to go back to machine 1.
- Both machines stay independent. Only cursor and keyboard input are shared.

## Project structure

```
GhostCursor/
├── ghost_cursor.py          # main program (work in progress)
├── requirements.txt         # Python libraries to install
├── assets/
│   └── cursors/             # cursor images (PNG)
└── experiments/             # learning steps, in order
    ├── 01_udp_basics/       # udp_server.py + udp_client.py: request/response test
    ├── 02_chat/             # chat.py: two-way UDP chat with a receive thread
    ├── 03_mouse_input/      # cursor.py: pynput mouse listener
    │                        # screenSize.py: screen size and DPI awareness test
    │                        # mouse_chat.py: send mouse events as JSON over UDP
    └── 04_ghost_drawing/    # cursor_skin.py: draw ghost cursor + name tag with tkinter
```

## Setup

```bash
pip install -r requirements.txt
```

## Running the experiments

Run from the project root, for example:

```bash
python experiments/02_chat/chat.py
python experiments/03_mouse_input/mouse_chat.py
python experiments/04_ghost_drawing/cursor_skin.py
```

The chat and mouse_chat scripts ask for your name and the **other** machine's IP. They use UDP port 9999, so allow it through the firewall. Type `!q` to quit.
