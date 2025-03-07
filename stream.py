from picamera2 import Picamera2

import socket
import pickle
import struct

try:
    import cv2 # type: ignore
except ImportError:
    print("OpenCV not found. Please follow the readme instructions carefully.")

ALLOWED_IP = "192.168.64.121" # Pi A

HOST = "0.0.0.0"
PORT = 4050

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(1)

print(f"Waiting for a connection on {HOST}:{PORT}")

while True:
    conn, addr = server_socket.accept()
    if addr[0] != ALLOWED_IP:
        print(f"Connection attempt from {addr[0]} - not permitted.")
        conn.close()
        continue
    
    print(f"Connection established with {addr}")
    break

cap = None
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480)})
picam2.configure(config)
picam2.start()

try:
    while cap.isOpened():
        frame = picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        data = pickle.dumps(frame)
        message = struct.pact("Q", len(data)) + data
        
        # Send frame over socket
        conn.sendall(message)
        
finally:
    cap.release()
    conn.close()
    server_socket.close()
    print("Stream closed.")