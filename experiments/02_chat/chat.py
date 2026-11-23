import threading
import socket

localPort = 9999
bufferSize = 1024

name = input("What's your name?: ")
otherIp = input("IP that you want to connect: ")

udp_server = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
udp_server.bind(("", localPort))


def receive():
    while True:
        try:
            msg, addr = udp_server.recvfrom(bufferSize)
            print(msg.decode())
        except ConnectionResetError:        # ← Windows quirk: other side not running yet, ignore
            pass
        except Exception as e:              # ← show real errors instead of hiding them
            print("error:", e)


udp_server.sendto(f"{name} join!".encode(), (otherIp, localPort))

t1 = threading.Thread(target=receive, daemon=True)
t1.start()

while True:
    message = input("")
    if message == "!q":
        break
    udp_server.sendto(f"{name}: {message}".encode(), (otherIp, localPort))

udp_server.close()
