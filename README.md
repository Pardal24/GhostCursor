# GhostCursor

Share one mouse and keyboard between two Windows computers on the same local network, over UDP.

> **Status:** in development. The `experiments/` folder contains the step-by-step prototypes used to explore each building block before writing the main program.

## Goal

- Two computers sit side by side, each running GhostCursor.
- Moving the cursor off the **left** edge of machine 1 makes it appear on machine 2 as a **ghost cursor** labelled with the user's name.
- The ghost cursor controls machine 2 like a normal mouse and keyboard: opening apps, typing in the browser, and so on.
- It works in both directions: moving off the **right** edge of machine 2 returns to machine 1.
- Both machines stay independent. Only mouse and keyboard input crosses the network.

## How it works (so far)

- **Transport:** UDP sockets on port `9999`, with JSON messages such as `{"t": "move", "x": 0.42, "y": 0.87}`.
- **Resolution independence:** cursor positions are sent **normalized** (0.0 to 1.0), so machines with different screen sizes map correctly. The process is DPI-aware, so coordinates are in real pixels.
- **Input capture:** `pynput` listeners, plus a low-level Windows mouse hook to read and **suppress** events. Suppressing them is what will let the local cursor "leave" the screen.
- **Ghost cursor:** a borderless, always-on-top, click-through tkinter window, made with the Win32 extended styles `WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE`. It draws a custom PNG cursor and a name tag.
- **Threading:** network and input callbacks run on background threads and pass data to the Tk main loop through a `queue.Queue`, because Tk is not thread-safe.

## Roadmap

- [x] UDP request/response and two-way chat
- [x] Capture mouse events and send them as JSON
- [x] Draw a click-through ghost cursor with a name tag
- [x] Mirror the other machine's cursor live over UDP
- [x] Low-level mouse hook: inspect, inject and block events
- [x] Detect screen-edge crossing and hand the cursor over (and back)
- [ ] Inject mouse and keyboard input on the remote machine (`SendInput`)
- [ ] Combine everything into a single `ghost_cursor` program

## Project structure

```
GhostCursor/
├── assets/cursors/            # cursor images (PNG)
├── experiments/
│   ├── 01_udp_basics/         # UDP server/client request-response
│   ├── 02_chat/               # two-way UDP chat with a receive thread
│   ├── 03_mouse_input/        # mouse listener, screen size/DPI, mouse events over UDP
│   ├── 04_ghost_cursor/       # drawing the ghost cursor and sharing it over UDP
│   ├── 05_input_hooks/        # low-level mouse hook, event injection and blocking
│   └── 06_edge_crossing/      # screen-edge detection and passing the cursor between machines
├── requirements.txt
└── README.md
```

| Experiment | What it shows |
|---|---|
| `01_udp_basics/udp_server.py`, `udp_client.py` | Minimal UDP request/response (localhost) |
| `02_chat/chat.py` | Peer-to-peer UDP chat; receiving runs on a daemon thread |
| `03_mouse_input/mouse_listener.py` | Print mouse moves, clicks and scrolls with `pynput` |
| `03_mouse_input/screen_size.py` | Screen size and cursor position, before and after DPI awareness |
| `03_mouse_input/mouse_chat.py` | Send normalized mouse events to the other machine as JSON |
| `04_ghost_cursor/ghost_skin.py` | Draw the cursor image + name tag on a canvas (click to move, Space to bounce) |
| `04_ghost_cursor/ghost_follow.py` | Floating, click-through ghost window that follows the real mouse |
| `04_ghost_cursor/ghost_auto.py` | Ghost driven by a background thread through a queue (circular path) |
| `04_ghost_cursor/ghost_share.py` | **Two machines:** each one shows the other's cursor as a ghost |
| `05_input_hooks/mouse_hook.py` | Low-level mouse hook: decode raw Windows messages, detect injected input |
| `05_input_hooks/mouse_suppress.py` | Hold **F8** to block clicks and scroll system-wide (10 s safety limit) |
| `06_edge_crossing/edge_detection.py` | Detect when the cursor hits the left or right screen edge |
| `06_edge_crossing/edge_deltas.py` | At the edge, park the real cursor and read raw movement deltas (F8 releases it) |
| `06_edge_crossing/edge_pass.py` | **Two machines:** cross the edge, steer a ghost cursor on the other PC, cross back to return. The local cursor is hidden and clicks are blocked while away (F8 = panic) |

## Requirements

- Windows 10 or 11. The experiments in `03`–`05` use the Win32 API through `ctypes`.
- Python 3.10+

```bash
pip install -r requirements.txt
```

## Usage

Run the scripts from the project root:

```bash
python experiments/04_ghost_cursor/ghost_share.py
```

- The networked scripts (`chat.py`, `mouse_chat.py`, `ghost_share.py`, `edge_pass.py`) ask for your name and the **other** machine's IP (`edge_pass.py` takes the IP as `--otherIp`). Run them on both machines and allow **UDP port 9999** through the Windows firewall.
- The `06_edge_crossing` scripts take the side the other machine is on, for example:

  ```bash
  python experiments/06_edge_crossing/edge_pass.py --side left --otherIp 192.168.1.20
  ```

- `chat.py` and `mouse_chat.py`: type `!q` to quit.
- The ghost windows are click-through, so close them with **Ctrl+C** in the terminal.
