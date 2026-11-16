# GhostCursor

Share one mouse and keyboard across two computers on the same local network, using UDP.

## Final goal

- Two machines sit side by side, each running GhostCursor.
- Move the cursor off the **left** edge of machine 1 and it shows up on machine 2 as a **ghost cursor** with the user's name under it.
- While the ghost cursor is on machine 2 it works like a normal cursor: open apps, type in the browser, and so on.
- It works in both directions: move off the **right** edge of machine 2 to go back to machine 1.
- Both machines stay independent. Only cursor and keyboard input are shared.

## Status: experiments / learning

| File | What it does |
|------|--------------|
| `udp_server.py` / `udp_client.py` | Basic UDP request/response test |
| `chat.py` | Two-way UDP chat between two machines (receives on a separate thread) |
| `ghost_cursor.py` | Placeholder for the main program |

## Running the chat test

On both machines (Python 3):

```bash
python chat.py
```

Enter your name and the **other** machine's IP address. Both machines use UDP port 9999, so allow it through the firewall. Type `!q` to quit.
