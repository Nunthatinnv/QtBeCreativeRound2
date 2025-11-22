import sys
import argparse
import cv2
import numpy as np
from PySide6.QtCore import QTimer, Qt, QObject, Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider

class OpencvImageProvider(QQuickImageProvider):
    """
    Standard Image Provider (Same as Phase 2)
    """
    def __init__(self):
        super().__init__(QQuickImageProvider.Image)
        self.streams = {}
        # Init black frames
        empty_image = QImage(640, 480, QImage.Format_RGB888)
        empty_image.fill(Qt.black)
        for i in range(1, 5):
            self.streams[f"cam{i}"] = empty_image

    def requestImage(self, id, size, requestedSize):
        clean_id = id.split('?')[0]
        if clean_id in self.streams:
            return self.streams[clean_id]
        return self.streams.get("cam1")

    def update_image(self, stream_id, cv_frame):
        try:
            rgb_frame = cv2.cvtColor(cv_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            img = QImage(rgb_frame.data, w, h, ch * w, QImage.Format_RGB888).copy()
            self.streams[stream_id] = img
        except Exception as e:
            pass

class MotionDetector:
    """
    The 'Watchdog'. Compares current frame vs previous frame.
    """
    def __init__(self):
        self.prev_frame = None
        self.min_area = 1000  # Sensitivity: smaller = more sensitive

    def process(self, frame):
        """
        Returns: (frame_with_boxes, is_motion_detected)
        """
        # 1. Prepare frame (Gray + Blur to remove noise)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        # Initialize previous frame if first run
        if self.prev_frame is None:
            self.prev_frame = gray
            return frame, False

        # 2. Compute Difference (Absolute Difference)
        # diff = |Current - Previous|
        frame_delta = cv2.absdiff(self.prev_frame, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        
        # Dilate to fill in holes
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        # 3. Find Contours (Shapes)
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        motion_found = False
        
        # Work on a copy so we don't ruin the original if needed elsewhere
        annotated_frame = frame.copy()

        for c in contours:
            # Ignore small movements (wind, noise)
            if cv2.contourArea(c) < self.min_area:
                continue
            
            motion_found = True
            
            # 4. Draw Red Box
            (x, y, w, h) = cv2.boundingRect(c)
            cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(annotated_frame, "MOTION DETECTED", (10, 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # Update previous frame for next loop
        # Note: In a real security system, we might update 'prev_frame' 
        # less frequently to detect slow movers.
        self.prev_frame = gray
        
        return annotated_frame, motion_found

class VideoController(QObject):
    def __init__(self, provider, camera_index=0):
        super().__init__()
        self.provider = provider
        self.cap = cv2.VideoCapture(camera_index)
        
        # Initialize our Watchdog
        self.detector = MotionDetector()
        
        self.timer = QTimer()
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.game_loop)
        self.timer.start()

    def game_loop(self):
        if not self.cap.isOpened(): return

        ret, frame = self.cap.read()
        if ret:
            # Resize for performance (optional, but good for heavy CV)
            frame = cv2.resize(frame, (640, 480))

            # --- 1. RUN MOTION DETECTION (Cam 1) ---
            # We process the frame to draw boxes on it
            motion_frame, has_motion = self.detector.process(frame)
            
            # Update Cam 1 (The "Smart" Camera)
            self.provider.update_image("cam1", motion_frame)
            
            # --- 2. SIMULATE OTHER FEEDS ---
            # Cam 2: Night Vision (We use the CLEAN frame, not the one with red boxes)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            self.provider.update_image("cam2", gray_bgr)
            
            # Cam 3: Mirror
            flipped = cv2.flip(frame, 1)
            self.provider.update_image("cam3", flipped)
            
            # Cam 4: Privacy
            blurred = cv2.GaussianBlur(frame, (35, 35), 0)
            self.provider.update_image("cam4", blurred)

    def release(self):
        if self.cap: self.cap.release()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--camera", type=int, default=0)
    args, _ = parser.parse_known_args()

    app = QApplication(sys.argv)
    engine = QQmlApplicationEngine()

    image_provider = OpencvImageProvider()
    engine.addImageProvider("live", image_provider)

    controller = VideoController(image_provider, camera_index=args.camera)
    app.aboutToQuit.connect(controller.release)

    import os
    qml_file = os.path.join(os.path.dirname(__file__), "Main.qml")
    engine.load(qml_file)

    if not engine.rootObjects(): sys.exit(-1)
    sys.exit(app.exec())