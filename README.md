# GhostCursor

Share one mouse between two Windows computers on the same local network, over UDP.

Move your cursor off the edge of your screen and it appears on the other computer as a **ghost cursor** with your name under it. There you can click, scroll and open apps, while both machines stay fully independent.

## Features

- **Edge crossing:** leave your screen on the side facing the other machine to take control, and cross back to return.
- **Ghost cursor:** a custom cursor image with a coloured name tag, drawn in a transparent, click-through window.
- **Remote clicks and scrolling:** left, right, middle and side buttons, plus vertical and horizontal scroll, are replayed on the other machine with `SendInput`.
- **Works both ways:** both machines run the same program, so either one can visit the other.
- **Local input is protected:** while you're away, your own cursor is hidden and your clicks are blocked locally.
- **Panic key:** press **F8** to bring your cursor home immediately.

## Quick start

Requirements: Windows 10 or 11, and Python 3.10+.

```bash
pip install -r requirements.txt
```

Run it on **both** machines. `--side` is the side where the **other** machine sits:

```bash
# on the machine on the LEFT
python ghost_cursor.py --side right --otherIp <IP of the right machine>

# on the machine on the RIGHT
python ghost_cursor.py --side left --otherIp <IP of the left machine>
```

Each side asks for your name and a cursor (`flower` or `frog`). Allow **UDP port 9999** through the Windows firewall on both machines. Stop with **Ctrl+C** in the terminal.

## How it works

- **Transport:** UDP sockets on port `9999`, with small JSON messages such as `{"t": "move", "dx": 0.004, "dy": -0.001}`.
  Message types are `connect`, `join`, `move`, `click_down`, `click_up`, `scroll`, `return` and `panic`.
- **Resolution independence:** positions and movements are sent **normalized** (relative to screen size), so machines with different resolutions map correctly. The process is DPI-aware, so coordinates are in real pixels.
- **Capturing the cursor:** a low-level Windows mouse hook (through `pynput`) detects the screen edge, parks the real cursor, and **suppresses** local moves, clicks and scrolls while forwarding them to the other machine.
- **Ghost cursor:** a borderless, always-on-top tkinter window made click-through with the Win32 extended styles `WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE`.
- **Replaying input:** clicks and scrolls are injected at the ghost's position with `SendInput`. Injected events carry the `LLMHF_INJECTED` flag, so the hook lets them through instead of capturing them again.
- **Hiding the real cursor:** the system cursors are swapped for a blank one with `SetSystemCursor` and restored with `SystemParametersInfo(SPI_SETCURSORS)`, including on exit.
- **Threading:** network and input callbacks run on background threads and pass data to the Tk main loop through a `queue.Queue`, because Tk is not thread-safe.

## Roadmap

- [x] UDP request/response and two-way chat
- [x] Capture mouse events and send them as JSON
- [x] Draw a click-through ghost cursor with a name tag
- [x] Mirror the other machine's cursor live over UDP
- [x] Low-level mouse hook: inspect, inject and block events
- [x] Detect screen-edge crossing and hand the cursor over (and back)
- [x] Replay clicks and scrolling on the remote machine with `SendInput`
- [x] Combine everything into a single `ghost_cursor.py` program
- [ ] Forward keyboard input
- [ ] Multi-monitor support

## Project structure

```
GhostCursor/
├── ghost_cursor.py            # the main program
├── assets/cursors/            # cursor images (PNG)
├── experiments/               # step-by-step prototypes that led to ghost_cursor.py
│   ├── 01_udp_basics/         # UDP server/client request-response
│   ├── 02_chat/               # two-way UDP chat with a receive thread
│   ├── 03_mouse_input/        # mouse listener, screen size/DPI, mouse events over UDP
│   ├── 04_ghost_cursor/       # drawing the ghost cursor and sharing it over UDP
│   ├── 05_input_hooks/        # low-level mouse hook, event injection and blocking
│   ├── 06_edge_crossing/      # screen-edge detection and passing the cursor between machines
│   └── 07_input_injection/    # synthesizing real clicks with SendInput
├── requirements.txt
└── README.md
```

## Experiments

Each building block was prototyped on its own before being combined into `ghost_cursor.py`. Run these from the project root, for example `python experiments/04_ghost_cursor/ghost_share.py`.

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
| `06_edge_crossing/edge_pass.py` | **Two machines:** cross the edge, steer a ghost cursor on the other PC, cross back to return |
| `07_input_injection/ghost_input.py` | Inject a real right-click at a screen position with `SendInput`, then restore the cursor |

Notes:
- The networked experiments ask for the other machine's IP; `edge_pass.py` takes `--side` and `--otherIp` like the main program.
- In `chat.py` and `mouse_chat.py`, type `!q` to quit. Close the ghost window experiments with **Ctrl+C**.
