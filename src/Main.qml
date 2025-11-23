import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    visible: true
    width: 1280
    height: 800
    title: "Extenly Surveillance - Production Ready"
    color: "#121212"

    // --- Notifications ---
    Rectangle {
        id: notificationBanner
        width: parent.width
        height: 40
        color: "#d32f2f"
        y: -40
        z: 100
        Text {
            id: notifText
            anchors.centerIn: parent
            color: "white"
            font.bold: true
        }
        Behavior on y { NumberAnimation { duration: 200 } }
    }

    Connections {
        target: backend
        function onAlertOccurred(cam, msg) {
            notifText.text = "ALERT [" + cam + "]: " + msg
            notificationBanner.y = 0
            notifTimer.restart()
        }
    }

    Timer {
        id: notifTimer
        interval: 3000
        onTriggered: notificationBanner.y = -40
    }

    // --- Camera Tile Component ---
    component CameraTile: Rectangle {
        property string camId: "cam1"
        property string camName: "Camera"
        property bool isRunning: false
        
        // ROI Drawing State
        property bool drawingMode: false
        property var startPoint: null

        Layout.fillWidth: true
        Layout.fillHeight: true
        color: "black"
        border.color: drawingMode ? "yellow" : "#333"
        border.width: drawingMode ? 2 : 1
        clip: true

        // Video Output
        Image {
            id: vid
            anchors.fill: parent
            fillMode: Image.PreserveAspectFit
            cache: false
            source: "image://live/" + camId
            
            MouseArea {
                anchors.fill: parent
                enabled: drawingMode
                onClicked: (mouse) => {
                    if (startPoint == null) {
                        startPoint = {x: mouse.x, y: mouse.y}
                        console.log("Start Point set")
                    } else {
                        // Calculate normalized coords (0.0 to 1.0)
                        var x1 = startPoint.x / width
                        var y1 = startPoint.y / height
                        var x2 = mouse.x / width
                        var y2 = mouse.y / height
                        
                        backend.setRoi(camId, x1, y1, x2, y2)
                        
                        startPoint = null
                        drawingMode = false
                    }
                }
            }
        }

        // Overlay UI
        Column {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.margins: 10
            spacing: 5
            
            Rectangle {
                width: lbl.width + 10
                height: 20
                color: "#80000000"
                Text { id: lbl; anchors.centerIn: parent; text: camName; color: "white"; font.bold: true }
            }
        }

        // Toolbar (Appears on Hover)
        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 40
            color: "#CC000000"
            opacity: mouseHover.containsMouse || drawingMode ? 1.0 : 0.0
            Behavior on opacity { NumberAnimation { duration: 200 } }

            RowLayout {
                anchors.centerIn: parent
                
                Button {
                    text: isRunning ? "STOP" : "START"
                    onClicked: {
                        backend.toggleCamera(camId)
                        isRunning = !isRunning
                    }
                }
                Button {
                    text: "SNAP"
                    onClicked: backend.captureSnapshot(camId)
                }
                Button {
                    text: drawingMode ? "CANCEL ROI" : "SET TRIPWIRE"
                    background: Rectangle { color: drawingMode ? "yellow" : "#444" }
                    onClicked: {
                        drawingMode = !drawingMode
                        startPoint = null
                    }
                }
                Text {
                    text: "Sensitivity:"
                    color: "white"
                    font.pixelSize: 12
                }
                Slider {
                    id: sensitivitySlider
                    from: 100
                    to: 3000
                    value: 1000
                    stepSize: 100
                    onValueChanged: backend.setSensitivity(camId, value)
                    Layout.preferredWidth: 120
                }
                Text {
                    text: Math.round(sensitivitySlider.value)
                    color: "white"
                    font.pixelSize: 12
                    font.bold: true
                }
            }
        }
        MouseArea { id: mouseHover; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
        
        // Refresher
        Timer {
            interval: 33; running: true; repeat: true
            onTriggered: vid.source = "image://live/" + camId + "?t=" + Math.random()
        }
    }

    // --- Main Layout ---
    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Header
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 50
            color: "#1f1f1f"
            Text {
                text: "EXTENLY SURVEILLANCE OPS"
                color: "white"
                anchors.centerIn: parent
                font.letterSpacing: 3
                font.bold: true
            }
        }

        // Grid
        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: 2
            rowSpacing: 2
            columnSpacing: 2
            
            CameraTile { camId: "cam1"; camName: "Front Door"; isRunning: false }
            CameraTile { camId: "cam2"; camName: "Backyard"; isRunning: false }
            CameraTile { camId: "cam3"; camName: "Garage"; isRunning: false }
            CameraTile { camId: "cam4"; camName: "Living Room"; isRunning: false }
        }

        // Alert Log
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 150
            color: "#0a0a0a"
            
            // Top border line
            Rectangle {
                width: parent.width
                height: 1
                color: "#333"
                anchors.top: parent.top
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                Text { text: "SYSTEM LOG"; color: "#666"; font.bold: true }
                
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: alertModel
                    clip: true
                    
                    delegate: Rectangle {
                        width: parent.width
                        height: 25
                        color: "transparent"
                        RowLayout {
                            spacing: 20
                            Text { text: time; color: "#888"; font.family: "Courier" }
                            Text { text: camera; color: "#00aaff"; font.bold: true }
                            Text { text: title; color: "#ddd" }
                        }
                    }
                }
            }
        }
    }
}