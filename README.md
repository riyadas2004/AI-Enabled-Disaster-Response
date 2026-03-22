Overview:
This project is an AI-enabled dual-drone system designed to assist in disaster response operations. It performs real-time aerial surveillance to detect survivors using computer vision techniques and maps their locations using GPS-based geotagging. The system also enables delivery of essential medical kits using a servo-based payload mechanism, integrating detection, mapping, and response into a unified solution.

Problem:
In disaster scenarios such as floods, earthquakes, or landslides, locating survivors quickly is a major challenge due to inaccessible terrain and lack of real-time information. Traditional search operations are time-consuming, resource-intensive, and often delayed, reducing the chances of timely rescue and assistance.

Solution:
The system uses a YOLO-based deep learning model to perform real-time human detection from live RTSP video streams. A GPS module provides location data, which is processed by the flight controller along with orientation parameters such as altitude and yaw. This telemetry data is transmitted via MAVLink to the ground system, where detected pixel positions are converted into real-world GPS coordinates. Multiple readings are averaged for accuracy, and results are stored and visualized using dynamically generated KML files. Additionally, a servo-based hatch mechanism enables the drone to deliver medical kits directly to detected survivors.

Features:
1. Real-time human detection using YOLO
2. RTSP video streaming
3. GPS geotagging and mapping
4. KML file generation
5. Ground Control Station (GCS) monitoring (Mission Planner)
6. Servo-based payload delivery system

Technologies Used:
Software:
1. Python
2. OpenCV
3. YOLO (Ultralytics)
4. PyMAVLink
5.  Mission Planner

Hardware:
1. Flight Controller
2. GPS Module
3. Telemetry System
4. Receiver & Transmitter
5. Electronic Speed Controllers (ESC)
6. Brushless Motors
7. Propellers
8. Camera (RTSP-enabled)
9. Servo Motor
10. Payload Hatch Mechanism

System Workflow:
1. Camera captures live video via RTSP
2. YOLO performs real-time human detection
3. GPS module provides location data (lat, lon)
4. Flight controller processes GPS and orientation (altitude, yaw)
5. Telemetry (MAVLink) sends data to ground system
6. Pixel coordinates are converted to real-world GPS positions
7. Multiple readings are averaged for accuracy
8. Data is stored in CSV format
9. KML file is generated for mapping
10. Ground Control Station displays results
11. Servo motor activates hatch to deliver medical kit

My Contribution:
1. Developed YOLO-based human detection with custom dataset
2. Implemented RTSP video processing pipeline
3. Built GPS-based geotagging and KML generation
4. Worked on Ground Control Station (GCS) monitoring
5. Assisted in hardware integration and payload system
