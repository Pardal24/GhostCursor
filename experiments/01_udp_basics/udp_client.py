import socket

msg = input("Enter a message: ")
bytesToSend =  str.encode(msg)

#serverAddrPort = ("172.31.161.108", 20001) #Linux
serverAddrPort = ("localhost", 20001)
bufferSize = 1024

udp_client = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

udp_client.sendto(bytesToSend,serverAddrPort)

response = udp_client.recvfrom(bufferSize)
msg_response = response[0].decode()
print(msg_response)