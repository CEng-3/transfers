import socket
import pickle
import struct
import threading
import time
import datetime
import os
import subprocess
import cv2
import traceback
from pathlib import Path

# Try to import Picamera2
try:
    from picamera2 import Picamera2
    camera_available = True
except ImportError:
    print("WARNING: Picamera2 not available. Using fallback mode.")
    camera_available = False

# Configuration
HOST = "0.0.0.0"
PORT = 4050
ALLOWED_IPS = ["192.168.64.121"]  # Pi A IP
TIMELAPSE_DIR = 'images'  # Changed from 'static/images/timelapse' to 'images'
VIDEOS_DIR = '.'  # Changed to current directory
FRAME_RATE = 15  # FPS for timelapse video

# SSH transfer configuration
SEND_VIDEO = True  # Flag to control remote transfer of completed video
REMOTE_HOST = "192.168.64.121"  # The target Pi
REMOTE_USER = "tower-garden"
REMOTE_DIR = "/home/tower-garden/site/static/videos/pi_"

# Ensure directories exist
Path(TIMELAPSE_DIR).mkdir(parents=True, exist_ok=True)

# Global variables
frame_lock = threading.Lock()
current_frame = None
camera = None

def initialize_camera():
    """Initialize the camera with appropriate settings"""
    global camera, camera_available
    
    if not camera_available:
        return False
    
    try:
        camera = Picamera2()
        config = camera.create_preview_configuration(main={"size": (640, 480)})
        camera.configure(config)
        camera.start()
        print("Camera initialized successfully")
        return True
    except Exception as e:
        print(f"Camera initialization error: {e}")
        camera_available = False
        return False

def capture_frames():
    """Continuously capture frames from the camera"""
    global current_frame, camera
    
    if not camera_available:
        print("Camera not available for frame capture")
        return
    
    print("Starting frame capture thread")
    while True:
        try:
            frame = camera.capture_array()
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            frame = cv2.flip(frame, -1)  # Flip image vertically as in app.py
            
            with frame_lock:
                current_frame = frame
            
            time.sleep(0.1)  # Limit frame rate to 10 FPS
        except Exception as e:
            print(f"Error capturing frame: {e}")
            time.sleep(1)  # Wait before retrying

def capture_timelapse_frame():
    """Capture a frame for the timelapse"""
    global current_frame
    
    # Only capture during daylight hours (6:00 - 18:00)
    current_hour = datetime.datetime.now().hour
    if not (6 <= current_hour < 18):
        return
    
    # Ensure timelapse directory exists for today
    today_date = datetime.datetime.now().strftime('%Y-%m-%d')
    today_dir = os.path.join(TIMELAPSE_DIR, today_date)
    Path(today_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        with frame_lock:
            if current_frame is None:
                print("No frame available for timelapse")
                return
            
            # Use a copy to avoid race conditions
            frame_to_save = current_frame.copy()
        
        # Save image with timestamp
        timestamp = datetime.datetime.now().strftime('%H-%M-%S')
        filename = f"{today_dir}/frame_{timestamp}.jpg"
        cv2.imwrite(filename, frame_to_save)
        print(f"Captured timelapse frame: {filename}")
    except Exception as e:
        print(f"Error capturing timelapse frame: {e}")
        traceback.print_exc()

def create_timelapse_video():
    """Create a timelapse video from today's captured frames"""
    today_date = datetime.datetime.now().strftime('%Y-%m-%d')
    today_dir = os.path.join(TIMELAPSE_DIR, today_date)
    
    # Check if directory exists and contains images
    if not os.path.exists(today_dir):
        print(f"No timelapse directory for today ({today_dir})")
        return
    
    frames = [f for f in os.listdir(today_dir) if f.endswith('.jpg')]
    if not frames:
        print(f"No frames captured today in {today_dir}")
        return
    
    try:
        # Create video using ffmpeg and save in the current directory
        output_video = f"timelapse_{today_date}.mp4"  # Changed path
        
        # Use ffmpeg to create video
        ffmpeg_cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file if it exists
            '-framerate', str(FRAME_RATE),
            '-pattern_type', 'glob',
            '-i', f"{today_dir}/frame_*.jpg",
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            output_video
        ]
        
        process = subprocess.Popen(
            ffmpeg_cmd, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            print(f"Timelapse video created successfully: {output_video}")
            
            # Optional: Clean up individual frames
            # for frame in frames:
            #     os.remove(os.path.join(today_dir, frame))
            
            # Transfer the completed video file to the remote server
            transfer_video_file(output_video)
        else:
            print(f"Error creating timelapse video: {stderr.decode()}")
    
    except Exception as e:
        print(f"Exception during timelapse creation: {e}")
        traceback.print_exc()
     
def transfer_video_file(video_path):
    """Transfer the timelapse video to remote host using SSH"""
    if not SEND_VIDEO:
        print("Video transfer skipped (SEND_VIDEO flag is disabled)")
        return
    
    if not os.path.exists(video_path):
        print("Video transfer skipped (video file not found)")
        return
    
    try:
        print(f"Transferring video to {REMOTE_USER}@{REMOTE_HOST}:{REMOTE_DIR}...")
        
        # Get the filename part without the path
        video_filename = os.path.basename(video_path)
        
        # First ensure the remote directory exists
        print("Ensuring remote directory exists...")
        mkdir_cmd = [
            "ssh", 
            f"{REMOTE_USER}@{REMOTE_HOST}", 
            f"mkdir -p {REMOTE_DIR}"
        ]
        
        mkdir_result = subprocess.run(
            mkdir_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if mkdir_result.returncode != 0:
            print(f"Warning: Could not ensure remote directory exists: {mkdir_result.stderr}")
        
        # Execute scp command to transfer the file
        transfer_cmd = [
            "scp",
            video_path,
            f"{REMOTE_USER}@{REMOTE_HOST}:{REMOTE_DIR}/{video_filename}"
        ]
        
        print("Executing command:", " ".join(transfer_cmd))
        
        result = subprocess.run(
            transfer_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False  # Don't raise exception, handle manually
        )
        
        if result.returncode == 0:
            print(f"Video transfer completed successfully")
        else:
            print(f"Error transferring video. Return code: {result.returncode}")
            print(f"Error details: {result.stderr}")
    except Exception as e:
        print(f"Unexpected error during transfer: {e}")
        traceback.print_exc()        

def handle_client(conn, addr):
    """Handle an individual client connection"""
    print(f"New connection from {addr}")
    try:
        while True:
            with frame_lock:
                if current_frame is None:
                    time.sleep(0.1)
                    continue
                
                # Make a copy to avoid potential race conditions
                frame_to_send = current_frame.copy()
            
            # Serialize frame data
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

def setup_timelapse_scheduler():
    """Set up the scheduler for timelapse-related tasks"""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        
        scheduler = BackgroundScheduler()
        
        # Schedule timelapse frame capture every 15 minutes
        scheduler.add_job(
            capture_timelapse_frame,
            'interval',
            minutes=15,
            id='timelapse_capture'
        )
        
        # Schedule timelapse video creation at 18:00 daily
        scheduler.add_job(
            create_timelapse_video,
            'cron',
            hour=18,
            minute=5,
            id='timelapse_video_creation'
        )
        
        scheduler.start()
        print("Timelapse scheduler started")
        return scheduler
    except ImportError:
        print("APScheduler not available. Timelapse scheduling disabled.")
        return None

def run_streaming_server():
    """Run the main streaming server"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        print(f"Streaming server started on {HOST}:{PORT}")
        
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
    except Exception as e:
        print(f"Server error: {e}")
        traceback.print_exc()
    finally:
        server_socket.close()
        print("Server closed")

if __name__ == "__main__":
    print("Starting Camera Service with Timelapse Generation...")
    
    # Initialize the camera
    if initialize_camera():
        # Start frame capture thread
        frame_thread = threading.Thread(target=capture_frames, daemon=True)
        frame_thread.start()
        
        # Setup timelapse scheduler
        scheduler = setup_timelapse_scheduler()
        
        # Run the streaming server (this will run until interrupted)
        run_streaming_server()
    else:
        print("Camera initialization failed. Service cannot start.")