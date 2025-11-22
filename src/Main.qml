import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    visible: true
    width: 1280
    height: 720
    title: "Extenly Surveillance - Phase 3 (Motion)"
    color: "#1e1e1e"

    // Component: Camera Tile
    component CameraTile: Rectangle {
        property string camName: "Camera"
        property string streamId: "cam1"
        property color statusColor: "#00FF00"

        Layout.fillWidth: true
        Layout.fillHeight: true
        color: "black"
        border.color: "#333"
        border.width: 1
        radius: 4
        clip: true

        Image {
            id: imgDisplay
            anchors.fill: parent
            anchors.margins: 2
            fillMode: Image.PreserveAspectFit
            cache: false
            source: "image://live/" + streamId
        }

        // Title Overlay
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.margins: 8
            width: lblObj.width + 16
            height: 24
            color: "#80000000"
            radius: 4
            Text {
                id: lblObj
                anchors.centerIn: parent
                text: camName
                color: "white"
                font.pixelSize: 12
                font.bold: true
            }
        }
        
        // Status Dot
        Rectangle {
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.margins: 10
            width: 10
            height: 10
            radius: 5
            color: statusColor
            border.color: "white"
            border.width: 1
        }

        Timer {
            interval: 30
            running: true
            repeat: true
            onTriggered: imgDisplay.source = "image://live/" + streamId + "?ts=" + Math.random()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Header
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 50
            color: "#252525"
            border.color: "#333"
            border.width: 1
            Text {
                anchors.centerIn: parent
                text: "SECURITY COMMAND CENTER - MOTION ACTIVE"
                color: "#ff4444" // Red text to show alert status
                font.letterSpacing: 2
                font.bold: true
            }
        }

        // Grid
        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: 2
            columnSpacing: 10
            rowSpacing: 10
            anchors.margins: 10

            // Cam 1 is now the Motion Detector
            CameraTile { 
                camName: "Entrance (Motion Detection)"; 
                streamId: "cam1"
                statusColor: "red" 
            }

            CameraTile { 
                camName: "Parking (Night)"; 
                streamId: "cam2" 
                statusColor: "#00FF00"
            }
            CameraTile { 
                camName: "Lobby (Mirror)"; 
                streamId: "cam3" 
            }
            CameraTile { 
                camName: "Privacy (Blurred)"; 
                streamId: "cam4"
                statusColor: "orange"
            }
        }
    }
}