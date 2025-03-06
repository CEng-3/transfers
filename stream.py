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

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

try:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame.")
            break
        
        data = pickle.dumps(frame)
        message = struct.pact("Q", len(data)) + data
        
        # Send frame over socket
        conn.sendall(message)
        
finally:
    cap.release()
    conn.close()
    server_socket.close()
    print("Stream closed.")