from picamera2 import Picamera2
import socket
import pickle
import struct
import threading
import time

try:
    import cv2
except ImportError:
    print("OpenCV not found. Please follow the readme instructions carefully.")

ALLOWED_IPS = ["192.168.64.121"]  # Pi A IP
HOST = "0.0.0.0"
PORT = 4050

# Initialize camera
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480)})
picam2.configure(config)
picam2.start()

# Capture frames in a separate thread
frame_lock = threading.Lock()
current_frame = None

def capture_frames():
    global current_frame
    while True:
        frame = picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        with frame_lock:
            current_frame = frame
        time.sleep(0.1)  # Limit frame rate to 10 FPS

# Start frame capture thread
frame_thread = threading.Thread(target=capture_frames, daemon=True)
frame_thread.start()

def handle_client(conn, addr):
    print(f"New connection from {addr}")
    try:
        while True:
            with frame_lock:
                if current_frame is None:
                    time.sleep(0.1)
                    continue
                
                # Make a copy to avoid potential race conditions
                frame_to_send = current_frame.copy()
            
            data = pickle.dumps(frame_to_send)
            message = struct.pack("Q", len(data)) + data
            
            # Send frame over socket
            conn.sendall(message)
            time.sleep(0.1)  # Limit framerate
            
    except (ConnectionResetError, BrokenPipeError):
        print(f"Client {addr} disconnected")
    except Exception as e:
        print(f"Error with client {addr}: {e}")
    finally:
        conn.close()

# Accept connections
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen(5)

print(f"Server started on {HOST}:{PORT}")

try:
    while True:
        conn, addr = server_socket.accept()
        if addr[0] not in ALLOWED_IPS:
            print(f"Connection attempt from {addr[0]} - not permitted.")
            conn.close()
            continue
        
        # Handle each client in a separate thread
        client_thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        client_thread.start()
        
except KeyboardInterrupt:
    print("Shutting down server...")
finally:
    server_socket.close()
    print("Server closed")