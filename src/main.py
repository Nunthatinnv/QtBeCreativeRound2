import sys
import argparse
import cv2
from PySide6.QtCore import QTimer, Qt, QObject, Signal, QSize
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider

class OpencvImageProvider(QQuickImageProvider):
    """
    This class acts as a bridge. QML asks this class for an image 
    by URL (e.g., "image://live/cam1"), and this class returns the latest frame.
    """
    def __init__(self):
        super().__init__(QQuickImageProvider.Image)
        self.current_image = None
        # Create a black placeholder image initially
        self.current_image = QImage(640, 480, QImage.Format_RGB888)
        self.current_image.fill(Qt.black)

    def requestImage(self, id, size, requestedSize):
        """
        Standard QQuickImageProvider method. 
        Called by QML when it needs a new frame.
        
        PySide6 expects a QImage to be returned (not a tuple).
        """
        if self.current_image:
            return self.current_image
        
        return QImage()

    def update_image(self, cv_frame):
        """
        Converts the raw OpenCV frame (BGR) to a QImage (RGB) 
        and stores it for the next request.
        """
        try:
            # 1. Convert BGR (OpenCV) to RGB (Qt)
            rgb_frame = cv2.cvtColor(cv_frame, cv2.COLOR_BGR2RGB)
            
            # 2. Get dimensions
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            
            # 3. Create QImage (Must copy to keep it safe in memory)
            self.current_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
        except Exception as e:
            print(f"Error converting image: {e}")

class VideoController(QObject):
    """
    Controls the camera logic (Start/Stop/Capture)
    """
    def __init__(self, provider, camera_index: int = 0):
        super().__init__()
        self.provider = provider
        self.camera_index = camera_index
        # allow caller to pick camera index
        self.cap = cv2.VideoCapture(camera_index)  # 0 = Default Webcam
        
        if not self.cap.isOpened():
            print(f"Warning: failed to open camera index {camera_index}")
        
        # Track if we've warned about black frames (for WiFi/virtual cams like Camo)
        self.black_frame_count = 0
        self.warned_about_black = False
        
        # Setup the "Game Loop" timer
        self.timer = QTimer()
        self.timer.setInterval(30) # 30ms ~ 33 FPS
        self.timer.timeout.connect(self.next_frame)
        self.timer.start()

    def next_frame(self):
        if not self.cap or not self.cap.isOpened():
            # avoid repeated noisy prints; just return early
            return
        ret, frame = self.cap.read()
        if ret:
            # Check if frame is all black (common with WiFi/virtual cameras like Camo)
            if frame.max() < 10:
                self.black_frame_count += 1
                if not self.warned_about_black and self.black_frame_count > 30:
                    print(f"\nCamera {self.camera_index} is sending black frames.")
                    print("   If using Camo Studio: Make sure the phone app is connected and streaming")
                    print("   If using another WiFi webcam: Check that the app is running and connected\n")
                    self.warned_about_black = True
            else:
                # Reset warning if we start getting real frames
                self.black_frame_count = 0
                self.warned_about_black = False
            
            # Send the frame to the provider
            self.provider.update_image(frame)
        else:
            # Camera read failed - keep this quiet to avoid spam
            pass
    
    def release(self):
        """Release the camera capture"""
        if self.cap:
            self.cap.release()

if __name__ == "__main__":
    # minimal CLI: allow listing cameras or selecting camera index
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--list-cameras", action="store_true", help="Probe and list available camera indices then exit")
    parser.add_argument("--camera", type=int, default=0, help="Camera index to use (default: 0)")
    parser.add_argument("--backend", type=str, default=None, help="Optional OpenCV backend name to use when probing (used only with --list-cameras)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output for camera probe")
    args, unknown = parser.parse_known_args()

    # Try to reduce OpenCV backend noise
    try:
        # OpenCV >=4.5
        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
    except Exception:
        try:
            # older OpenCV
            cv2.setLogLevel(cv2.LOG_LEVEL_ERROR)
        except Exception:
            pass

    if args.list_cameras:
        # import the probe helper from the small utility added in this repo
        try:
            from list_cameras import probe_cameras, resolve_backend

            backend = resolve_backend(args.backend)
            if args.backend and backend is None:
                print(f"Warning: unknown backend '{args.backend}', ignoring and using default.")

            cams = probe_cameras(max_index=8, timeout=1.0, backend=backend, verbose=args.verbose)
            if cams:
                print("Available camera indices:", cams)
                for c in cams:
                    print(c)
                sys.exit(0)
            else:
                print("No cameras found")
                sys.exit(1)
        except Exception as e:
            print("Error running camera probe:", e)
            sys.exit(2)

    # Launch the Qt UI with the selected camera index
    app = QApplication(sys.argv)
    engine = QQmlApplicationEngine()

    # 1. Initialize the Provider
    image_provider = OpencvImageProvider()
    
    # 2. Register it so QML can use "image://live/..."
    engine.addImageProvider("live", image_provider)

    # 3. Initialize the Controller (Starts the camera)
    controller = VideoController(image_provider, camera_index=args.camera)

    # Ensure camera is released when the app quits
    app.aboutToQuit.connect(controller.release)

    # 4. Load the UI
    import os
    qml_file = os.path.join(os.path.dirname(__file__), "Main.qml")
    engine.load(qml_file)

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())