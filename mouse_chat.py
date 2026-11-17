import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)

import socket
import threading
import json
from pynput import mouse

user32 = ctypes.windll.user32
W = user32.GetSystemMetrics(0)
H = user32.GetSystemMetrics(1)

name = input("What's your name?: ")
otherIp = input("What's the IP you want to connect?: ")
port = 9999
bufferSize = 1024

server = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
server.bind(("", port))

def send(msg):
    server.sendto(json.dumps(msg).encode(), (otherIp, port))

def to_normalize(x, y):
    nx = x / (W - 1)
    ny = y / (H - 1)
    return min(max(nx, 0.0), 1.0), min(max(ny, 0.0), 1.0)

def on_move(x, y):
    nx, ny = to_normalize(x, y)
    send({"t": "move", "x": nx, "y": ny})

def on_click(x, y, button, pressed):
    nx, ny = to_normalize(x, y)
    send({"t": "btn", "b": button.name, "down": pressed, "x": nx, "y": ny}) 

def on_scroll(x, y, dx, dy):
    nx, ny = to_normalize(x, y)
    send({"t": "wheel", "dy": dy, "x": nx, "y": ny})

def receive():
    while True:
        try:
            data, addr = server.recvfrom(bufferSize)
            msg = json.loads(data)                   
            t = msg["t"]
            if t == "join":
                print(f"{msg['name']} joined!")
            elif t == "chat":
                print(f"{msg['name']}: {msg['text']}")
            elif t == "move":
                print(f"move  ({msg['x']:.3f}, {msg['y']:.3f})")
            elif t == "btn":
                print(f"{msg['b']} {'down' if msg['down'] else 'up'} at ({msg['x']:.3f}, {msg['y']:.3f})")
            elif t == "wheel":
                print(f"scroll {'up' if msg['dy'] > 0 else 'down'} at ({msg['x']:.3f}, {msg['y']:.3f})")
        except ConnectionResetError:
            pass
        except Exception as e:
            print("error:", e)

send({"t": "join", "name": name})

t = threading.Thread(target=receive, daemon=True)   
t.start()

listener = mouse.Listener(                           
    on_move=on_move,
    on_click=on_click,
    on_scroll=on_scroll)
listener.start()

while True:
    text = input(": ")
    if text == "!q":
        break
    send({"t": "chat", "name": name, "text": text})

listener.stop()                                     
server.close()