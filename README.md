Military Object Detection & Geolocation System 🛡️
This project transforms an ESP32-CAM and an ESP32 with a GPS module into a smart surveillance system. It offers two primary modes of operation: real-time threat detection via a live video stream and manual analysis of user-uploaded images.
In real-time mode, the ESP32-CAM streams live footage to a Python Flask server. This server uses a Roboflow AI model to detect military objects. 📹 When an object is detected, the system immediately draws a bounding box around it, displays a probability score, and raises a visual warning. 🚨 It then fetches the current GPS coordinates from the second ESP32 module, logs the captured frame with its location, and displays it on a captures page. 🛰️
In manual mode, a user can upload a static image directly through the web interface. The server will analyze the image using the same Roboflow model, and if a detection is made, the annotated image will be saved and displayed in the captures gallery.
<!-- Suggestion: Add a GIF of your project in action! -->
🚀 Features
Real-time Video Streaming: Live video feed from the ESP32-CAM directly to a web interface.
AI-Powered Detection: Utilizes a Roboflow model for accurate detection of military objects in both live video and static images.
Manual Image Upload: A dedicated mode for users to upload and analyze their own images for threats.
Geolocation Tagging: Automatically pairs GPS coordinates with every positive detection from the live stream.
Warning System: Displays a clear visual warning on the frontend whenever a threat is detected.
Automatic Capture & Logging: Saves a snapshot of any detected object (from either mode) to a dedicated captures gallery with its location.
Web-Based Frontend: A user-friendly interface built with Flask and HTML for both the live stream and the captures gallery.
Secure Configuration: Uses a .env file to safely store sensitive information like API keys and device URLs.
📁 Project Structure
Here is the file structure for the project:
Generated code
.
├── app.py                  # The main Flask application file
├── 32_GPS.ino              # Arduino code for the ESP32 with GPS module
├── CAM_GPS.ino             # Arduino code for the ESP32-CAM
├── templates/
│   ├── live_stream.html    # Frontend for the video stream and image upload form
│   └── captures.html       # Gallery to display captured images and their locations
├── static/
│   └── captures/           # Folder where captured images are stored
├── .env                    # Environment variables (API keys, URLs)
└── requirements.txt        # Python dependencies
Use code with caution.
🛠️ Hardware & Software Requirements
Hardware ⚙️
ESP32-CAM AI-Thinker Module
ESP32 DEVKIT V1 Module
GPS Module (e.g., NEO-6M)
FTDI Programmer (for flashing the ESP32-CAM)
Jumper Wires
USB Cables
Software & Libraries 💻
Python 3.7+
Flask: Web server framework.
OpenCV-Python: For image processing.
Roboflow: For the object detection model.
python-dotenv: To manage environment variables.
Arduino IDE
ESP32 Board Manager for Arduino IDE.
Arduino Libraries:
TinyGPS++
(The ESP32-CAM libraries are included with the board manager setup)
🔌 Connection Steps
1. ESP32-CAM Setup (For Live Stream)
To upload the CAM_GPS.ino sketch, connect the ESP32-CAM to your computer using an FTDI programmer.
ESP32-CAM Pin	FTDI Programmer
VCC	5V
GND	GND
U0T	RXD
U0R	TXD
Important: Before uploading, you must connect the IO0 pin to GND to put the ESP32-CAM into flashing mode. After the upload is complete, disconnect IO0 from GND for normal operation.
2. ESP32 DEV Module + GPS Setup (For Geolocation)
This module is responsible for fetching GPS data.
ESP32 DEV Pin	GPS Module (NEO-6M)
5V	VCC
GND	GND
GPIO 16 (RX2)	TXD
GPIO 17 (TX2)	RXD
This setup uses HardwareSerial on pins 16 and 17.
⚙️ Installation and Setup Guide
Follow these steps for different operating systems.
Step 1: Clone the Repository
Generated bash
git clone <your-repository-url>
cd <your-repository-name>
Use code with caution.
Bash
Step 2: Configure The ESP32 Modules (Arduino)
Install Arduino IDE and add the ESP32 Board URL in File > Preferences.
URL: https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
Go to Tools > Board > Boards Manager..., search for esp32 and install it.
Go to Sketch > Include Library > Manage Libraries..., search for TinyGPS++ and install it.
Open CAM_GPS.ino, update your Wi-Fi credentials (ssid and password), and upload it to the ESP32-CAM board (select "AI Thinker ESP32-CAM" as the board).
Open 32_GPS.ino, update your Wi-Fi credentials, and upload it to your ESP32 DEV Module.
Open the Serial Monitor for both devices to get their IP addresses. You will need these for the .env file.
Step 3: Configure the Python Environment
Create and activate a virtual environment.
Windows - Command Prompt 💻
Generated bash
python -m venv venv
venv\Scripts\activate
Use code with caution.
Bash
macOS / Linux - Terminal 🐧
Generated bash
python3 -m venv venv
source venv/bin/activate
Use code with caution.
Bash
Step 4: Install Dependencies
Create a requirements.txt file with the following content:
Generated code
Flask
opencv-python-headless
numpy
requests
python-dotenv
roboflow```

Now, install the packages:
```bash
pip install -r requirements.txt
Use code with caution.
Step 5: Setup Environment Variables
Create a file named .env in the root directory.
Add the following lines, replacing the placeholder values with your actual data.
Generated code
# .env file

# Your Roboflow API Key
ROBOFLOW_API_KEY="YOUR_ROBOFLOW_API_KEY_HERE"

# The full URL for the ESP32-CAM video stream
ESP32_CAM_URL="http://192.168.1.XX"  # Replace with your CAM IP

# The full URL for the ESP32 GPS module's data endpoint
ESP32_GPS_URL="http://192.168.1.YY" # Replace with your GPS module's IP
Use code with caution.
▶️ How to Run the System
Power On: (For live mode) Connect both the ESP32-CAM and the ESP32 DEV Module to a power source.
Start the Server: Run the Flask application from your terminal.
Generated bash
python app.py
Use code with caution.
Bash
View the Frontend: Open your web browser and navigate to the address shown in the terminal, usually http://127.0.0.1:5000.
Modes of Operation
Live Stream Detection: The main page will immediately start streaming from the ESP32-CAM. If a military object is detected, a warning will appear, and a snapshot will be automatically sent to the /captures page along with its GPS location.
Manual Upload Mode: On the main page, use the file upload form. Select an image from your computer, give it an optional location tag, and click "Upload and Analyze". You will be redirected to the /captures gallery to see the processed result.
📚 Core Libraries Used
from flask import Flask, render_template, Response, request, jsonify, url_for: The heart of our web application. It handles routing (/, /upload, /captures), serving HTML pages (live_stream.html, captures.html), handling file uploads, and streaming video data.
import os, cv2, numpy as np, requests, base64, threading, time: Essential libraries for backend logic.
os: To manage file paths and create directories (static/captures).
cv2 (OpenCV) & numpy: For fetching and decoding the camera image, reading uploaded files, and drawing rectangles on them.
requests: To fetch the video stream from the ESP32-CAM and the GPS data from the ESP32 DEV module.
threading & time: To handle tasks concurrently, such as fetching frames without blocking the server.
base64: To encode the image data.
from dotenv import load_dotenv: To load the secure variables from our .env file.
ESP32/Arduino Libraries:
#include <WiFi.h> & #include <WebServer.h>: To connect the ESP32 modules to your network and create web servers to serve video and GPS data.
#include "esp_camera.h": Specific library to control the ESP32-CAM's camera functions.
#include <TinyGPS++.h> & #include <HardwareSerial.h>: To parse the NMEA data coming from the GPS module via a hardware serial port.
