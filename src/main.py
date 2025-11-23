import sys
import json
import cv2
import time
import os
import csv
import datetime
import numpy as np
from PySide6.QtCore import QTimer, Qt, QObject, Signal, Slot, QUrl, QAbstractListModel, QModelIndex
from PySide6.QtGui import QImage, QColor
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider

# --- Constants ---
SNAPSHOT_DIR = "snapshots"
if not os.path.exists(SNAPSHOT_DIR):
    os.makedirs(SNAPSHOT_DIR)

# --- Alert Log Model for QML ---
class AlertLogModel(QAbstractListModel):
    TitleRole = Qt.UserRole + 1
    TimeRole = Qt.UserRole + 2
    CameraRole = Qt.UserRole + 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.alerts = []

    def rowCount(self, parent=QModelIndex()):
        return len(self.alerts)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self.alerts):
            return None
        alert = self.alerts[index.row()]
        if role == AlertLogModel.TitleRole:
            return alert["message"]
        elif role == AlertLogModel.TimeRole:
            return alert["time"]
        elif role == AlertLogModel.CameraRole:
            return alert["camera"]
        return None

    def roleNames(self):
        return {
            AlertLogModel.TitleRole: b"title",
            AlertLogModel.TimeRole: b"time",
            AlertLogModel.CameraRole: b"camera"
        }

    def add_alert(self, camera_name, message):
        self.beginInsertRows(QModelIndex(), 0, 0)
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.alerts.insert(0, {"camera": camera_name, "message": message, "time": timestamp})
        self.endInsertRows()
        
        # Auto-export to CSV
        with open("alert_log.csv", "a", newline='') as f:
            writer = csv.writer(f)
            writer.writerow([datetime.datetime.now().isoformat(), camera_name, message])

# --- Image Provider ---
class OpencvImageProvider(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.Image)
        self.streams = {}
        # Init black frames
        self.black_frame = QImage(640, 480, QImage.Format_RGB888)
        self.black_frame.fill(Qt.black)

    def requestImage(self, id, size, requestedSize):
        clean_id = id.split('?')[0]
        return self.streams.get(clean_id, self.black_frame)

    def update_image(self, stream_id, q_image):
        self.streams[stream_id] = q_image

# --- Single Camera Worker ---
class CameraAgent:
    def __init__(self, config, provider, alert_callback):
        self.id = config["id"]
        self.name = config["name"]
        self.source = config["source"]
        self.sensitivity = config.get("sensitivity", 1000) # Min contour area
        self.roi_line = config.get("roi", []) # [x1, y1, x2, y2] normalized 0-1
        
        self.provider = provider
        self.on_alert = alert_callback
        
        self.cap = None
        self.running = False
        self.active = False # User toggle
        
        self.prev_frame = None
        self.fps = 0
        self.frame_count = 0
        self.last_time = time.time()
        
        # Cooldown to prevent alert spam
        self.last_alert_time = 0 

    def start(self):
        if self.active: return
        self.cap = cv2.VideoCapture(self.source)
        self.active = True

    def stop(self):
        self.active = False
        if self.cap:
            self.cap.release()
        self.cap = None
        # Send black frame to indicate stopped
        self.provider.update_image(self.id, self.provider.black_frame)

    def set_roi(self, points):
        """ points: [x1, y1, x2, y2] normalized """
        self.roi_line = points

    def process(self):
        if not self.active or not self.cap or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if not ret:
            # Loop video files
            if isinstance(self.source, str) and not self.source.startswith("rtsp"):
                 self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return

        # Resize for consistent processing
        frame = cv2.resize(frame, (640, 480))
        display_frame = frame.copy()

        # --- Motion Detection ---
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.prev_frame is None:
            self.prev_frame = gray
        else:
            diff = cv2.absdiff(self.prev_frame, gray)
            thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            motion_detected = False
            
            for c in contours:
                area = cv2.contourArea(c)
                if area < self.sensitivity:
                    continue
                
                motion_detected = True
                (x, y, w, h) = cv2.boundingRect(c)
                
                # Draw motion box with area label
                cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(display_frame, f"Area: {int(area)}", (x, y-5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                
                # --- Tripwire Logic ---
                if len(self.roi_line) == 4 and time.time() - self.last_alert_time > 2.0:
                    # Unpack normalized coords to pixels
                    lx1, ly1, lx2, ly2 = self.roi_line
                    lx1, ly1, lx2, ly2 = int(lx1*640), int(ly1*480), int(lx2*640), int(ly2*480)
                    
                    # Check if motion bounding box crosses tripwire
                    if self.line_intersects_rect((lx1, ly1), (lx2, ly2), (x, y, w, h)):
                        self.on_alert(self.name, f"Tripwire Crossed! (Area: {int(area)})")
                        self.last_alert_time = time.time()
                        cv2.putText(display_frame, "ALERT!", (10, 50), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
                        # Flash the tripwire red briefly
                        cv2.line(display_frame, (lx1, ly1), (lx2, ly2), (0, 0, 255), 4)

            self.prev_frame = gray

            # Draw ROI Line (Yellow)
            if len(self.roi_line) == 4:
                lx1, ly1, lx2, ly2 = self.roi_line
                lx1, ly1, lx2, ly2 = int(lx1*640), int(ly1*480), int(lx2*640), int(ly2*480)
                cv2.line(display_frame, (lx1, ly1), (lx2, ly2), (0, 255, 255), 3)
                # Add endpoint markers
                cv2.circle(display_frame, (lx1, ly1), 5, (0, 255, 255), -1)
                cv2.circle(display_frame, (lx2, ly2), 5, (0, 255, 255), -1)

            # Display sensitivity threshold on frame
            cv2.putText(display_frame, f"Sensitivity: {self.sensitivity}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            # FPS Calculation
            self.frame_count += 1
            if time.time() - self.last_time >= 1.0:
                self.fps = self.frame_count
                self.frame_count = 0
                self.last_time = time.time()
            
            cv2.putText(display_frame, f"FPS: {self.fps}", (550, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Convert to QImage
            rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qt_img = QImage(rgb.data, w, h, ch*w, QImage.Format_RGB888).copy()
            self.provider.update_image(self.id, qt_img)

    def line_intersects_rect(self, p1, p2, rect):
        """
        Proper line-rectangle intersection using Liang-Barsky algorithm
        Returns True if the line segment intersects the bounding box
        """
        x, y, w, h = rect
        x1, y1 = p1
        x2, y2 = p2
        
        # Check if line endpoints are inside rectangle
        if (x <= x1 <= x+w and y <= y1 <= y+h) or (x <= x2 <= x+w and y <= y2 <= y+h):
            return True
        
        # Check if line crosses any of the four rectangle edges
        # Top edge
        if self.line_segment_intersection((x1,y1), (x2,y2), (x,y), (x+w,y)):
            return True
        # Bottom edge
        if self.line_segment_intersection((x1,y1), (x2,y2), (x,y+h), (x+w,y+h)):
            return True
        # Left edge
        if self.line_segment_intersection((x1,y1), (x2,y2), (x,y), (x,y+h)):
            return True
        # Right edge
        if self.line_segment_intersection((x1,y1), (x2,y2), (x+w,y), (x+w,y+h)):
            return True
        
        return False
    
    def line_segment_intersection(self, p1, p2, p3, p4):
        """Check if line segment p1-p2 intersects with line segment p3-p4"""
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4
        
        denom = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
        if abs(denom) < 1e-10:
            return False
        
        t = ((x1-x3)*(y3-y4) - (y1-y3)*(x3-x4)) / denom
        u = -((x1-x2)*(y1-y3) - (y1-y2)*(x1-x3)) / denom
        
        return 0 <= t <= 1 and 0 <= u <= 1

    def take_snapshot(self):
        if self.cap:
            ret, frame = self.cap.read()
            if ret:
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{SNAPSHOT_DIR}/{self.name}_{ts}.jpg"
                cv2.imwrite(filename, frame)
                return filename
        return ""

# --- System Controller ---
class SystemController(QObject):
    alertOccurred = Signal(str, str) # title, msg

    def __init__(self, provider, config_path="config.json"):
        super().__init__()
        self.provider = provider
        self.agents = {}
        self.alert_model = AlertLogModel()

        # Load Config
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
                for cam_conf in data["cameras"]:
                    agent = CameraAgent(cam_conf, provider, self.handle_alert)
                    self.agents[agent.id] = agent
        except Exception as e:
            print(f"Config Error: {e}")

        # Global Timer
        self.timer = QTimer()
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.update_all)
        self.timer.start()

    def update_all(self):
        for agent in self.agents.values():
            agent.process()

    def handle_alert(self, cam_name, msg):
        print(f"ALERT: {cam_name} - {msg}")
        self.alert_model.add_alert(cam_name, msg)
        self.alertOccurred.emit(cam_name, msg)

    # --- QML Callable Methods ---

    @Slot(str)
    def toggleCamera(self, cam_id):
        if cam_id in self.agents:
            agent = self.agents[cam_id]
            if agent.active: agent.stop()
            else: agent.start()

    @Slot(str)
    def captureSnapshot(self, cam_id):
        if cam_id in self.agents:
            path = self.agents[cam_id].take_snapshot()
            if path: self.handle_alert(self.agents[cam_id].name, f"Snapshot saved: {path}")

    @Slot(str, float, float, float, float)
    def setRoi(self, cam_id, x1, y1, x2, y2):
        if cam_id in self.agents:
            self.agents[cam_id].set_roi([x1, y1, x2, y2])
            print(f"ROI Set for {cam_id}: {x1:.2f},{y1:.2f} -> {x2:.2f},{y2:.2f}")

    @Slot(str, int)
    def setSensitivity(self, cam_id, val):
        if cam_id in self.agents:
            self.agents[cam_id].sensitivity = val

if __name__ == "__main__":
    app = QApplication(sys.argv)
    engine = QQmlApplicationEngine()

    provider = OpencvImageProvider()
    engine.addImageProvider("live", provider)

    controller = SystemController(provider)
    
    # Expose Controller and Models to QML
    engine.rootContext().setContextProperty("backend", controller)
    engine.rootContext().setContextProperty("alertModel", controller.alert_model)

    engine.load("Main.qml")
    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())