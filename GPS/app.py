# Filename: app.py
from flask import Flask, render_template, Response, request, jsonify, url_for
import os, cv2, numpy as np, requests, base64, threading, time, json
from dotenv import load_dotenv

# --- INITIAL SETUP ---
load_dotenv()
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY")
ESP32_CAM_URL = os.getenv("ESP32_CAM_URL")
ESP32_LOCATOR_URL = os.getenv("ESP32_LOCATOR_URL")

if not all([ROBOFLOW_API_KEY, ESP32_CAM_URL, ESP32_LOCATOR_URL]):
    raise ValueError("FATAL ERROR: Please set all required variables (ROBOFLOW_API_KEY, ESP32_CAM_URL, ESP32_LOCATOR_URL) in your .env file.")

os.makedirs("static/captures", exist_ok=True)

# Updated models: A single category with multiple fine-tuned models
DETECTION_MODELS = {
    "gun_detection": {
        "name": "Gun Detection",
        "models": [
            {"id": "pistol-fire-and-gun/1", "name": "Pistol/Gun Fire", "conf": 0.4, "color": (255, 215, 0)},
            {"id": "gun-and-weapon-detection/1", "name": "Weapon Detection v1", "conf": 0.35, "color": (255, 192, 203)},
            {"id": "knife-and-gun-modelv2/2", "name": "Knife/Gun v2", "conf": 0.35, "color": (218, 112, 214)},
            {"id": "military-f5tbj/1", "name": "Military Equipment", "conf": 0.35, "color": (188, 143, 143)},
            {"id": "weapon-detection-ssvfk/1", "name": "Weapon Detection v2", "conf": 0.4, "color": (255, 20, 147)},
            {"id": "gun-d8mga/2", "name": "Gun Model v2", "conf": 0.45, "color": (219, 112, 147)},
        ]
    }
}


app = Flask(__name__)

class ESP32CamStream:
    def __init__(self):
        self.stream_url = f"{ESP32_CAM_URL}:81/stream"
        self.raw_frame, self.display_frame = None, None
        self.state_lock, self.frame_lock = threading.Lock(), threading.Lock()
        self.state, self.running, self.stream_active = "STREAMING_LIVE", False, False
        self.active_model_id = "all" # Can be 'all' or a specific model ID
        self.last_detection_time, self.detection_cooldown = 0, 3.0
        self.last_detection_info = None

    def start(self):
        if self.running: return
        self.running = True
        threading.Thread(target=self._stream_loop, daemon=True).start()
        threading.Thread(target=self._detection_loop, daemon=True).start()

    def _stream_loop(self):
        try:
            r = requests.get(self.stream_url, stream=True, timeout=10)
            r.raise_for_status()
            self.stream_active = True
            buffer = bytes()
            for chunk in r.iter_content(chunk_size=4096):
                if not self.running: break
                buffer += chunk
                start, end = buffer.find(b'\xff\xd8'), buffer.find(b'\xff\xd9')
                if start != -1 and end != -1:
                    frame_data = buffer[start:end+2]
                    frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)
                    with self.frame_lock: self.raw_frame = frame.copy()
                    buffer = buffer[end+2:]
        except Exception as e:
            print(f"ERROR: Stream disconnected from CAM. Reason: {e}")
        finally:
            self.stream_active = False

    def _detection_loop(self):
        while self.running:
            with self.state_lock:
                if self.state == "PAUSED_FOR_CONFIRMATION":
                    time.sleep(0.5); continue
            
            if time.time() - self.last_detection_time < self.detection_cooldown:
                time.sleep(0.2); continue

            with self.frame_lock:
                if self.raw_frame is None: time.sleep(0.1); continue
                frame_to_process = self.raw_frame.copy()
            
            detected_threat_names, frame_with_boxes = self.run_detection_on_frame(frame_to_process)
            
            with self.state_lock:
                if self.state == "STREAMING_LIVE" and detected_threat_names:
                    print(f"🚨 THREAT DETECTED: {', '.join(detected_threat_names)}. Pausing.")
                    self.state = "PAUSED_FOR_CONFIRMATION"
                    
                    location = self.get_gps_location()
                    self.last_detection_info = {"threats": detected_threat_names, "location": location}
                    self.last_detection_time = time.time()
                    
                    with self.frame_lock: self.display_frame = frame_with_boxes.copy()

                    timestamp = time.strftime('%Y%m%d_%H%M%S')
                    filename_img = f"capture_{timestamp}.jpg"
                    filepath_img = os.path.join("static/captures", filename_img)
                    cv2.imwrite(filepath_img, frame_with_boxes)
                    print(f"📸 Evidence image saved: {filepath_img}")
                    
                    filename_meta = f"capture_{timestamp}.json"
                    filepath_meta = os.path.join("static/captures", filename_meta)
                    with open(filepath_meta, 'w') as f:
                        json.dump(self.last_detection_info, f, indent=4)
                    print(f"📝 Evidence metadata saved: {filepath_meta}")
                else:
                    # Keep showing the live annotated feed even if no threats are paused
                    with self.frame_lock: self.display_frame = frame_with_boxes.copy()

            time.sleep(0.5)

    def run_detection_on_frame(self, frame):
        annotated_frame = frame.copy()
        all_detected_threat_names = set()
        
        models_to_run = []
        all_models = DETECTION_MODELS["gun_detection"]["models"]
        if self.active_model_id == "all":
            models_to_run = all_models
        else:
            models_to_run = [m for m in all_models if m['id'] == self.active_model_id]

        for model in models_to_run:
            predictions = call_roboflow_api(frame, model['id'], model['conf'])
            for p in predictions:
                all_detected_threat_names.add(model['name'])
                x1, y1 = int(p['x']-p['width']/2), int(p['y']-p['height']/2)
                x2, y2 = int(p['x']+p['width']/2), int(p['y']+p['height']/2)
                
                # Use model-specific color and create label
                color = model['color']
                label = f"{model['name']} ({p['confidence']:.1%})"
                (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                
                # Draw boxes and labels
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                cv2.rectangle(annotated_frame, (x1, y1 - h - 5), (x1 + w, y1), color, -1)
                cv2.putText(annotated_frame, label, (x1, y1 - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
                
        return list(all_detected_threat_names), annotated_frame

    def get_display_frame(self):
        with self.frame_lock:
            # Always prefer display_frame (annotated/paused) over raw_frame
            if self.display_frame is not None: return self.display_frame.copy()
            if self.raw_frame is not None: return self.raw_frame.copy()
            return None # Return None if no frames are available

    def get_gps_location(self):
        try:
            location_url = f"{ESP32_LOCATOR_URL}/get-location"
            print(f"-> Requesting GPS location from: {location_url}...")
            response = requests.get(location_url, timeout=3)
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "success":
                location = {"lat": data["lat"], "lon": data["lon"]}
                print(f"-> GPS location acquired: {location}")
                return location
            else: 
                print(f"WARNING: GPS Locator reported no valid fix.")
                return None
        except Exception as e:
            print(f"ERROR: Could not get GPS location. Reason: {e}")
            return None
            
    def resume_streaming(self):
        with self.state_lock:
            if self.state == "PAUSED_FOR_CONFIRMATION":
                self.state = "STREAMING_LIVE"
                self.last_detection_info = None
                with self.frame_lock: self.display_frame = None
                print("✅ Stream resumed by user.")

    def stop(self): self.running = False

# --- Global Instance & Helper Functions ---
cam_stream = None

def call_roboflow_api(image, model_id, confidence):
    try:
        _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 85])
        response = requests.post(
            f"https://detect.roboflow.com/{model_id}?api_key={ROBOFLOW_API_KEY}",
            data=base64.b64encode(buffer), headers={'Content-Type': 'application/x-www-form-urlencoded'},
            params={"confidence": confidence}, timeout=3)
        response.raise_for_status()
        return response.json().get('predictions', [])
    except Exception as e: 
        print(f"API Error for {model_id}: {e}")
        return []

def generate_frames():
    while True:
        frame, status_text, color = None, "OFFLINE", (255,0,0) # Red for OFFLINE
        if cam_stream and cam_stream.running:
            frame = cam_stream.get_display_frame()
            if cam_stream.stream_active:
                 status_text, color = "LIVE", (0,255,0) # Green for LIVE
            else:
                 status_text, color = "CONNECTING...", (255,255,0) # Yellow for CONNECTING
        
        if frame is None: 
            frame = np.zeros((480, 640, 3), np.uint8)

        # Draw status bar at the bottom
        cv2.rectangle(frame, (0, 455), (640, 480), (0,0,0), -1)
        cv2.circle(frame, (15, 468), 5, color, -1)
        cv2.putText(frame, status_text, (30, 472), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
        
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if ret: 
            yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        
        time.sleep(1/30) # 30 FPS

# --- FLASK ROUTES ---
@app.route('/')
def index(): return render_template('live_stream.html', models=DETECTION_MODELS['gun_detection']['models'])

@app.route('/video_feed')
def video_feed(): return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_stream', methods=['POST'])
def start_stream_route():
    global cam_stream
    if not cam_stream or not cam_stream.running:
        cam_stream = ESP32CamStream()
        cam_stream.start()
    return jsonify(status="success", message="Stream started.")

@app.route('/stop_stream', methods=['POST'])
def stop_stream_route():
    global cam_stream
    if cam_stream:
        cam_stream.stop()
        cam_stream = None
    return jsonify(status="success", message="Stream stopped.")

@app.route('/set_active_model', methods=['POST'])
def set_active_model_route():
    model_id = request.json.get('model_id', 'all')
    if cam_stream:
        cam_stream.active_model_id = model_id
        print(f"✅ Active model set to: {model_id}")
        return jsonify(status="success")
    return jsonify(status="error", message="Stream not active"), 400

@app.route('/set_brightness', methods=['POST'])
def set_brightness_route():
    level = request.json.get('level')
    if level is None: return jsonify(status="error", message="Missing level"), 400
    try:
        requests.get(f"{ESP32_CAM_URL}/led?level={level}", timeout=2)
        return jsonify(status="success")
    except Exception as e: 
        return jsonify(status="error", message=str(e)), 502

@app.route('/get_status', methods=['GET'])
def get_status_route():
    if not (cam_stream and cam_stream.running):
        return jsonify(state="OFFLINE")
    if not cam_stream.stream_active and cam_stream.state == "STREAMING_LIVE":
        return jsonify(state="CONNECTING")

    with cam_stream.state_lock:
        status_data = {"state": cam_stream.state}
        if cam_stream.state == "PAUSED_FOR_CONFIRMATION":
            status_data.update(cam_stream.last_detection_info or {})
        return jsonify(status_data)

@app.route('/resume_stream', methods=['POST'])
def resume_stream_route():
    if cam_stream:
        cam_stream.resume_streaming()
        return jsonify(status="success")
    return jsonify(status="error", message="Stream not active"), 400

@app.route('/captures')
def view_captures():
    captures_dir = "static/captures"
    capture_data = []
    if os.path.exists(captures_dir):
        files = sorted([f for f in os.listdir(captures_dir) if f.endswith('.jpg')], reverse=True)
        for f in files:
            base_name = os.path.splitext(f)[0]
            meta_file = base_name + '.json'
            capture_item = {"image_file": f, "location": None, "threats": "N/A"}
            meta_path = os.path.join(captures_dir, meta_file)
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, 'r') as mf:
                        meta = json.load(mf)
                        capture_item["location"] = meta.get("location")
                        capture_item["threats"] = ", ".join(meta.get("threats", ["Unknown"]))
                except Exception as e: 
                    print(f"Could not read metadata for {f}: {e}")
            capture_data.append(capture_item)
    return render_template('captures.html', captures=capture_data)


if __name__ == '__main__':
    print(f"🚀 Starting Detection Server -> http://127.0.0.1:5001")
    print(f"✅ Configured to use Camera at: {ESP32_CAM_URL}")
    print(f"✅ Configured to use GPS Locator at: {ESP32_LOCATOR_URL}")
    app.run(host='0.0.0.0', port=5001, debug=False)
