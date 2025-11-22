import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    visible: true
    width: 1024
    height: 768
    title: "Extenly Surveillance - Phase 1"
    color: "#1e1e1e" // Dark background

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 10

        // Header
        Text {
            text: "Camera Feed 01"
            color: "#ffffff"
            font.pixelSize: 24
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }

        // Video Container
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "black"
            border.color: "#444"
            border.width: 2
            radius: 5

            Image {
                id: liveFeed
                anchors.fill: parent
                fillMode: Image.PreserveAspectFit
                cache: false // CRITICAL: Do not cache, or video won't update
                
                // Initial source
                source: "image://live/cam1"
            }

            // Overlay Text (FPS or Status)
            Text {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.margins: 10
                text: "LIVE"
                color: "red"
                font.bold: true
                font.pixelSize: 16
                
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: -4
                    color: "black"
                    opacity: 0.5
                    z: -1
                }
            }
        }

        // Footer Controls
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 20

            Button {
                text: "Quit"
                onClicked: Qt.quit()
                contentItem: Text {
                    text: parent.text
                    color: "white"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    color: parent.down ? "#d32f2f" : "#b71c1c"
                    radius: 5
                }
            }
        }
    }

    // The Refresh Loop
    // QML Image elements are static by default. 
    // This timer forces the Image to reload from the C++ provider every 30ms.
    Timer {
        interval: 30
        running: true
        repeat: true
        onTriggered: {
            // We append a random number (or timestamp) to the URL.
            // This tricks QML into thinking it's a new image source.
            liveFeed.source = "image://live/cam1?ts=" + Math.random()
        }
    }
}