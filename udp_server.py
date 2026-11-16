import socket

#localIp = "172.31.161.108" #Linux
localIp = "172.18.82.151"
localPort = 20001
bufferSize = 1024

udp_server = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
udp_server.bind((localIp,localPort))

while(True):
    msg,addr1 = udp_server.recvfrom(bufferSize)

    msg = msg.decode()
    if msg:
        print(msg)
        msg_send = "Received the message"
        bytesToSend = str.encode(msg_send)
        udp_server.sendto(bytesToSend,addr1)
    else:
        msg_send = "Didn't received any message"
        bytesToSend = str.encode(msg_send)
        udp_server.sendto(bytesToSend,addr1)


