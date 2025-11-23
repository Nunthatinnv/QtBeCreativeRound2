# Extenly Surveillance System

This project is a real-time surveillance system designed for monitoring multiple video feeds. It is built using Python (PySide6) for the application backend and processing logic, and QML (Qt Quick) for a modern, responsive user interface. It heavily relies on OpenCV for video capture, image processing, and critical features like motion detection and tripwire monitoring.

## Features

- Multi-Source Video: Handles video streams from various sources (USB cameras, IP cameras via RTSP, or local video files).

- Real-time Motion Detection: Uses background subtraction and contour analysis to identify and highlight movement with bounding boxes.

- Tripwire / Region of Interest (ROI): Allows users to define a line on the video feed to trigger an alert when motion crosses it.

- Adjustable Sensitivity: Fine-tune the motion detection threshold per camera.

- Alert Notifications: Real-time visual banners and logging for motion and tripwire events.

- Snapshot Capture: Save current frames to disk on demand.

- Alert Logging: Automatically records all alerts to an alert_log.csv file.

## Setup and Installation

This project requires Python 3.x.

1. Clone the Repository

First, clone the project files to your local machine:
```
git clone https://github.com/Nunthatinnv/QtBeCreativeRound2.git
cd QtBeCreativeRound2/src
```

2. Setup Virtual Environment (Recommended)

It is highly recommended to use a virtual environment to manage dependencies for the project.
Windows (Command Prompt / PowerShell):
```
# Create the virtual environment
python -m venv venv

# Activate the virtual environment
.\venv\Scripts\activate
```

macOS / Linux (Bash / Zsh):
```
# Create the virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate
```

3. Install Dependencies

Once the virtual environment is active, install the required Python packages from the requirements.txt file:
```
pip install -r requirements.txt
```

4. Configuration (config.json)

The application loads its cameras from the config.json file. Ensure this file is present and configured correctly.

Example config.json structure:
```
{
    "cameras": [
        {
            "id": "cam1",
            "name": "Front Door",
            "source": 0,  // Index 0 for the first detected USB/Webcam
            "sensitivity": 500, // Minimum area for motion in pixels
            "roi": [0.2, 0.5, 0.8, 0.5] // Normalized coordinates [x1, y1, x2, y2]
        },
        {
            "id": "cam3",
            "name": "Garage (Video)",
            "source": "testing_video/walking.mp4", // Path to a local video file
            "sensitivity": 800,
            "roi": []
        }
    ]
}
```


### Camera Source Examples

The `source` field determines the video input:

| Source Type | `source` Example | Description |
| :--- | :--- | :--- |
| **USB/Webcam** | `0`, `1`, `2`, etc. | Integer index of the physical camera connected to your PC. |
| **Local Video File**| `"path/to/my/video.mp4"` | Relative or absolute path to an existing video file for testing. |


### Running the Application

Execute the main Python script from the project `src` directory **while the virtual environment is active**:
```
python main.py
```

The QML GUI window will launch, displaying the surveillance dashboard with all configured camera tiles.


## Demo Steps

1. Start a Camera Feed
    1. Locate a Camera Tile (e.g., "Front Door").
    2. Click the START button located in the toolbar that appears when you hover over the tile.
    3. The button will change to STOP, and the video stream should begin to display.

2. Configure Motion Detection
    1. Once the stream is running, any movement will be highlighted by a red bounding box.
    2. Use the Sensitivity Slider (labeled Sensitivity:) in the tile's toolbar.
        - Lower Value (e.g., 300): Increases sensitivity, detecting smaller movements.
        - Higher Value (e.g., 1500): Decreases sensitivity, filtering out minor fluctuations like shadows or noise.

3. Set and Trigger a Tripwire (ROI)
    1. Click the SET TRIPWIRE button. The tile border will turn yellow to indicate drawing mode.
    2. Click once on the video feed to set the start point (P1) of the tripwire.
    3. Click a second time on the video feed to set the end point (P2).
    4. The tripwire is now active. When a moving object (red bounding box) crosses this line, a flashing red alert banner will appear at the top of the application, and an entry will be logged to the **SYSTEM LOG**.


4. Manage Snapshots and Logs
- Click the SNAP button at any time to capture the current frame of the camera feed. The snapshot is saved to the snapshots/ directory.
- View all historical motion and tripwire events in the SYSTEM LOG panel at the bottom of the window. A permanent record of all alerts is also maintained in the alert_log.csv file.