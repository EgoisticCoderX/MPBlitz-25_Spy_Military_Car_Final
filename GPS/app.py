import os, cv2, numpy as np, requests, base64, threading, time, json
from flask import Flask, render_template, Response, request, jsonify, url_for
from dotenv import load_dotenv
import google.generativeai as genai
from urllib.parse import urljoin

# --- Setup: Load all keys and URLs ---
load_dotenv()
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ESP32_CONTROL_URL = os.getenv("ESP32_CONTROL_URL")
ESP32_STREAM_URL = os.getenv("ESP32_STREAM_URL")
ESP32_FLASHLIGHT_URL = os.getenv("ESP32_FLASHLIGHT_URL")

if not all([ROBOFLOW_API_KEY, GEMINI_API_KEY, ESP32_CONTROL_URL, ESP32_STREAM_URL, ESP32_FLASHLIGHT_URL]):
    raise ValueError("FATAL ERROR: Please set ALL FIVE required variables in your .env file.")

genai.configure(api_key=GEMINI_API_KEY)
os.makedirs("static/captures", exist_ok=True)
app = Flask(__name__)

# --- Model Config ---
DETECTION_MODELS = [
    {"id": "pistol-fire-and-gun/1", "name": "Pistol/Gun Fire", "conf": 0.50}, 
    {"id": "gun-and-weapon-detection/1", "name": "Weapon Detection v1", "conf": 0.80}, 
    {"id": "knife-and-gun-modelv2/2", "name": "Knife/Gun v2", "conf": 0.50}, 
    {"id": "military-f5tbj/1", "name": "Military Equipment", "conf": 0.50}, 
    {"id": "weapon-detection-ssvfk/1", "name": "Weapon Detection v2", "conf": 0.99}, 
    {"id": "gun-d8mga/2", "name": "Gun Model v2", "conf": 0.69}
]

for model in DETECTION_MODELS: 
    model['color'] = tuple(np.random.randint(100, 255, size=3).tolist())

# --- Helper Functions ---
def calculate_iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    
    if xB <= xA or yB <= yA:
        return 0.0
    
    interArea = (xB - xA) * (yB - yA)
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    
    if boxAArea + boxBArea - interArea == 0:
        return 0.0
    
    return interArea / float(boxAArea + boxBArea - interArea)

def test_esp32_connection():
    """Test if ESP32 is reachable"""
    try:
        # Test stream URL first
        response = requests.get(ESP32_STREAM_URL, timeout=3, stream=True)
        if response.status_code == 200:
            print("✅ ESP32 stream connection successful")
            return True
        else:
            print(f"❌ ESP32 stream returned status: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"❌ ESP32 connection failed: {e}")
        return False

def verify_with_gemini(image_bytes):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        safety_settings = {
            'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
            'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE', 
            'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
            'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE'
        }
        response = model.generate_content([
            "Does this image contain a real weapon (gun, rifle, knife)? Respond only 'yes' or 'no'.", 
            {"mime_type": "image/jpeg", "data": image_bytes}
        ], safety_settings=safety_settings)
        response.resolve()
        print(f"🧠 Gemini Verification Response: '{response.text.strip().lower()}'")
        return "yes" in response.text.strip().lower()
    except Exception as e: 
        print(f"❌ ERROR: Gemini verification failed: {e}")
        return False

# --- Core Detection and Control Class ---
class DetectionStreamer:
    def __init__(self):
        self.stream_url = ESP32_STREAM_URL
        self.last_frame = None
        self.running = False
        self.connection_established = False
        self.frame_lock = threading.Lock()
        self.state_lock = threading.Lock()
        self.state = "OFFLINE"
        self.last_detection_info = None
        self.processed_frame = None
        self.stream_thread = None
        self.detection_thread = None

    def start(self):
        if self.running:
            print("⚠️  Streamer already running")
            return False
            
        # Test connection first
        if not test_esp32_connection():
            print("❌ Cannot connect to ESP32")
            return False
            
        self.running = True
        self.connection_established = False
        
        with self.state_lock:
            self.state = "CONNECTING"
        
        # Start threads
        self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.detection_thread = threading.Thread(target=self._detection_pipeline, daemon=True)
        
        self.stream_thread.start()
        self.detection_thread.start()
        
        # Wait a moment to see if connection establishes
        time.sleep(2)
        return self.connection_established

    def stop(self):
        print("🛑 Stopping streamer...")
        self.running = False
        self.connection_established = False
        
        with self.state_lock:
            self.state = "OFFLINE"
        
        # Wait for threads to finish
        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=2)
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=2)
            
        print("✅ Streamer stopped")

    def _stream_loop(self):
        consecutive_failures = 0
        max_failures = 5
        
        while self.running:
            try:
                print(f"🔄 Attempting to connect to: {self.stream_url}")
                response = requests.get(self.stream_url, stream=True, timeout=10)
                response.raise_for_status()
                
                print("✅ Stream connection established")
                self.connection_established = True
                consecutive_failures = 0
                
                with self.state_lock:
                    if self.state == "CONNECTING":
                        self.state = "STREAMING"
                
                buffer = bytes()
                
                for chunk in response.iter_content(chunk_size=4096):
                    if not self.running:
                        break
                        
                    buffer += chunk
                    
                    # Look for JPEG boundaries
                    start = buffer.find(b'\xff\xd8')  # JPEG start
                    end = buffer.find(b'\xff\xd9')    # JPEG end
                    
                    if start != -1 and end != -1 and end > start:
                        # Extract JPEG frame
                        jpeg_data = buffer[start:end+2]
                        
                        try:
                            # Decode image
                            frame = cv2.imdecode(
                                np.frombuffer(jpeg_data, dtype=np.uint8), 
                                cv2.IMREAD_COLOR
                            )
                            
                            if frame is not None:
                                with self.frame_lock:
                                    self.last_frame = frame.copy()
                        except Exception as e:
                            print(f"⚠️  Frame decode error: {e}")
                        
                        # Remove processed data from buffer
                        buffer = buffer[end+2:]
                        
            except requests.exceptions.RequestException as e:
                consecutive_failures += 1
                print(f"❌ Stream connection error (attempt {consecutive_failures}): {e}")
                
                if consecutive_failures >= max_failures:
                    print(f"💀 Too many consecutive failures ({max_failures}), stopping stream")
                    break
                    
                # Wait before retrying
                time.sleep(min(consecutive_failures * 2, 10))
                
            except Exception as e:
                print(f"❌ Unexpected stream error: {e}")
                break
        
        self.connection_established = False
        with self.state_lock:
            self.state = "OFFLINE"
        print("🔴 Stream loop ended")

    def _detection_pipeline(self):
        while self.running:
            # Wait for connection to establish
            if not self.connection_established:
                time.sleep(0.5)
                continue
                
            with self.state_lock:
                if self.state not in ["STREAMING", "VERIFYING"]:
                    time.sleep(0.5)
                    continue
                    
            # Get current frame
            with self.frame_lock:
                if self.last_frame is None:
                    time.sleep(0.1)
                    continue
                frame = self.last_frame.copy()

            try:
                # Run detection on multiple models
                all_preds = []
                GLOBAL_MIN_CONFIDENCE = 0.60
                
                for model in DETECTION_MODELS:
                    try:
                        preds = self._call_roboflow(frame, model['id'], max(model['conf'], GLOBAL_MIN_CONFIDENCE))
                        for p in preds:
                            p.update({
                                'model_name': model['name'], 
                                'color': model['color']
                            })
                            all_preds.append(p)
                    except Exception as e:
                        print(f"⚠️  Detection failed for {model['name']}: {e}")
                        continue

                # Filter and verify detections
                verified_candidates = self._heuristic_filter(all_preds)
                
                if verified_candidates:
                    with self.state_lock:
                        self.state = "VERIFYING"
                    
                    # Verify with Gemini
                    confirmed_threats = []
                    for det in verified_candidates:
                        try:
                            x1, y1, x2, y2 = det['box']
                            cropped = frame[y1:y2, x1:x2]
                            _, img_bytes = cv2.imencode('.jpg', cropped)
                            
                            if verify_with_gemini(img_bytes.tobytes()):
                                confirmed_threats.append(det)
                        except Exception as e:
                            print(f"⚠️  Gemini verification error: {e}")
                    
                    if confirmed_threats:
                        self._handle_confirmed_threat(frame, confirmed_threats)
                    else:
                        with self.state_lock:
                            self.state = "STREAMING"
                
                # Always update processed frame for display
                self.processed_frame = self._annotate_frame(frame, all_preds, [])
                
            except Exception as e:
                print(f"❌ Detection pipeline error: {e}")
            
            # Control detection rate
            time.sleep(1/5)  # 5 FPS detection rate

    def _heuristic_filter(self, predictions):
        if len(predictions) < 2:
            return []
        
        # Reset visited flag
        for p in predictions:
            p['visited'] = False
            
        boxes = []
        for p in predictions:
            x, y, w, h = p['x'], p['y'], p['width'], p['height']
            boxes.append([
                int(x - w/2), int(y - h/2), 
                int(x + w/2), int(y + h/2)
            ])
        
        clusters = []
        for i, boxA in enumerate(boxes):
            if predictions[i].get('visited'):
                continue
                
            current_cluster = {
                'boxes': [boxA], 
                'models': {predictions[i]['model_name']}
            }
            predictions[i]['visited'] = True
            
            for j, boxB in enumerate(boxes):
                if i == j or predictions[j].get('visited'):
                    continue
                    
                if calculate_iou(boxA, boxB) > 0.3:  # 30% overlap threshold
                    current_cluster['boxes'].append(boxB)
                    current_cluster['models'].add(predictions[j]['model_name'])
                    predictions[j]['visited'] = True
            
            # Require at least 2 different models to agree
            if len(current_cluster['models']) >= 2:
                # Calculate average bounding box
                x_coords = []
                y_coords = []
                for box in current_cluster['boxes']:
                    x_coords.extend([box[0], box[2]])
                    y_coords.extend([box[1], box[3]])
                
                avg_box = [
                    min(x_coords), min(y_coords),
                    max(x_coords), max(y_coords)
                ]
                
                clusters.append({
                    'box': avg_box,
                    'models': list(current_cluster['models'])
                })
        
        return clusters
    
    def _handle_confirmed_threat(self, frame, detections):
        with self.state_lock:
            self.state = "PAUSED"
            
            # Create annotated frame
            annotated_frame = self._annotate_frame(frame.copy(), [], detections)
            
            # Get location (placeholder for now)
            location = self._get_gps_location()
            
            # Collect threat information
            threat_models = []
            for det in detections:
                threat_models.extend(det['models'])
            threat_models = list(set(threat_models))  # Remove duplicates
            
            self.last_detection_info = {
                "threats": threat_models,
                "location": location
            }
            
            # Save capture
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            img_filepath = os.path.join(app.static_folder, "captures", f"capture_{timestamp}.jpg")
            
            try:
                success = cv2.imwrite(img_filepath, annotated_frame)
                if success:
                    # Save metadata
                    meta_filepath = os.path.join(app.static_folder, "captures", f"capture_{timestamp}.json")
                    with open(meta_filepath, 'w') as f:
                        json.dump(self.last_detection_info, f, indent=2)
                    print(f"💾 Threat capture saved: {img_filepath}")
                else:
                    print("❌ Failed to save capture")
                    with self.state_lock:
                        self.state = "STREAMING"
            except Exception as e:
                print(f"❌ Error saving capture: {e}")
                with self.state_lock:
                    self.state = "STREAMING"
            
            self.processed_frame = annotated_frame
    
    def send_control_command(self, action, value):
        """Send control commands to ESP32"""
        if not self.running or not self.connection_established:
            print("⚠️  Cannot send control - not connected")
            return False
            
        try:
            if action == "flashlight":
                url = f"{ESP32_FLASHLIGHT_URL}/flashlight"
                params = {"intensity": int(value)}
            elif action == "pan":
                url = f"{ESP32_CONTROL_URL}/pan"
                params = {"angle": int(value)}
            elif action == "tilt":
                url = f"{ESP32_CONTROL_URL}/tilt"  
                params = {"angle": int(value)}
            else:
                print(f"⚠️  Unknown action: {action}")
                return False
            
            response = requests.get(url, params=params, timeout=2)
            if response.status_code == 200:
                print(f"✅ Control sent: {action}={value}")
                return True
            else:
                print(f"⚠️  Control failed: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            print(f"❌ Control command failed: {e}")
            return False

    def _call_roboflow(self, image, model_id, confidence):
        """Call Roboflow API for object detection"""
        try:
            _, img_encoded = cv2.imencode('.jpg', image)
            
            response = requests.post(
                f"https://detect.roboflow.com/{model_id}?api_key={ROBOFLOW_API_KEY}",
                data=base64.b64encode(img_encoded).decode('utf-8'),
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                params={"confidence": confidence},
                timeout=5
            )
            response.raise_for_status()
            return response.json().get('predictions', [])
        except Exception as e:
            print(f"❌ Roboflow API error: {e}")
            return []

    def _get_gps_location(self):
        """Placeholder for GPS location"""
        return None

    def _annotate_frame(self, frame, regular_preds, confirmed_threats):
        """Annotate frame with detection boxes"""
        try:
            if confirmed_threats:
                # Draw confirmed threat boxes in red
                for det in confirmed_threats:
                    x1, y1, x2, y2 = det['box']
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                    cv2.putText(
                        frame, "CONFIRMED THREAT", 
                        (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2
                    )
            else:
                # Draw regular prediction boxes
                for pred in regular_preds:
                    x, y, w, h = pred['x'], pred['y'], pred['width'], pred['height']
                    x1, y1 = int(x - w/2), int(y - h/2)
                    x2, y2 = int(x + w/2), int(y + h/2)
                    
                    color = pred.get('color', (255, 255, 255))
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    
                    label = f"{pred['model_name']} {pred['confidence']:.0%}"
                    cv2.putText(
                        frame, label, (x1, y1 - 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1
                    )
        except Exception as e:
            print(f"⚠️  Annotation error: {e}")
        
        return frame

    def get_frame_bytes(self):
        """Get current frame as JPEG bytes"""
        with self.frame_lock:
            if self.processed_frame is not None:
                frame = self.processed_frame
            elif self.last_frame is not None:
                frame = self.last_frame
            else:
                # Create offline image
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(
                    frame, "SYSTEM OFFLINE", (180, 240), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2
                )
        
        try:
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                return buffer.tobytes()
        except Exception as e:
            print(f"❌ Frame encoding error: {e}")
        
        return None

    def resume(self):
        """Resume streaming after threat detection"""
        with self.state_lock:
            self.state = "STREAMING"
            self.last_detection_info = None
            self.processed_frame = None
        print("✅ Stream resumed")

    def get_status(self):
        """Get current system status"""
        with self.state_lock:
            status = {"state": self.state}
            if self.last_detection_info:
                status.update(self.last_detection_info)
            return status

# --- Global Instance & Routes ---
streamer = None

def generate_frames():
    """Generate video frames for streaming"""
    while True:
        if streamer and streamer.running:
            frame_bytes = streamer.get_frame_bytes()
            if frame_bytes:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(1/30)  # 30 FPS
        else:
            # Offline frame
            try:
                offline_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(offline_frame, "SYSTEM OFFLINE", (180, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
                _, buffer = cv2.imencode('.jpg', offline_frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            except:
                pass
            time.sleep(1)

@app.route('/')
def index():
    return render_template('live_stream.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_stream', methods=['POST'])
def start_stream():
    global streamer
    try:
        if streamer and streamer.running:
            return jsonify({"status": "already_running"})
        
        streamer = DetectionStreamer()
        success = streamer.start()
        
        if success:
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "connection_failed"}), 500
            
    except Exception as e:
        print(f"❌ Start stream error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/stop_stream', methods=['POST'])
def stop_stream():
    global streamer
    try:
        if streamer:
            streamer.stop()
            streamer = None
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"❌ Stop stream error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/resume_stream', methods=['POST'])
def resume_stream():
    global streamer
    try:
        if streamer and streamer.running:
            streamer.resume()
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "not_running"}), 400
    except Exception as e:
        print(f"❌ Resume stream error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_status', methods=['GET'])
def get_status():
    global streamer
    try:
        if streamer and streamer.running:
            return jsonify(streamer.get_status())
        else:
            return jsonify({"state": "OFFLINE"})
    except Exception as e:
        print(f"❌ Get status error: {e}")
        return jsonify({"state": "OFFLINE"})

@app.route('/control', methods=['POST'])
def control():
    global streamer
    try:
        if not (streamer and streamer.running):
            return jsonify({"status": "not_running"}), 400
        
        data = request.json
        action = data.get('action')
        value = data.get('value')
        
        if not action or value is None:
            return jsonify({"status": "invalid_data"}), 400
        
        success = streamer.send_control_command(action, value)
        
        if success:
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "command_failed"}), 500
            
    except Exception as e:
        print(f"❌ Control error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/captures')
def captures():
    """View captured threat images"""
    captures_data = []
    captures_dir = os.path.join(app.static_folder, "captures")
    
    if os.path.exists(captures_dir):
        image_files = [f for f in os.listdir(captures_dir) if f.endswith('.jpg')]
        
        for img_file in sorted(image_files, reverse=True):
            item = {
                "image_url": url_for('static', filename=f'captures/{img_file}'),
                "threats": "N/A",
                "location": None
            }
            
            # Load metadata if available
            meta_path = os.path.join(captures_dir, os.path.splitext(img_file)[0] + '.json')
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, 'r') as f:
                        meta = json.load(f)
                    item.update({
                        'location': meta.get('location'),
                        'threats': ", ".join(meta.get('threats', []))
                    })
                except Exception as e:
                    print(f"⚠️  Error loading metadata: {e}")
            
            captures_data.append(item)
    
    return render_template('captures.html', captures=captures_data)

@app.route('/test_connection')
def test_connection():
    """Test ESP32 connection endpoint"""
    try:
        success = test_esp32_connection()
        return jsonify({
            "status": "success" if success else "failed",
            "esp32_urls": {
                "control": ESP32_CONTROL_URL,
                "stream": ESP32_STREAM_URL,
                "flashlight": ESP32_FLASHLIGHT_URL
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Create offline image if it doesn't exist
    offline_path = "static/offline.jpg"
    if not os.path.exists(offline_path):
        try:
            offline_img = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(offline_img, "SYSTEM OFFLINE", (180, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
            cv2.imwrite(offline_path, offline_img)
        except Exception as e:
            print(f"⚠️  Could not create offline image: {e}")
    
    print("🚀 Starting Tactical Detection System...")
    print(f"📡 ESP32 Stream URL: {ESP32_STREAM_URL}")
    print(f"🎮 ESP32 Control URL: {ESP32_CONTROL_URL}")
    print(f"💡 ESP32 Flashlight URL: {ESP32_FLASHLIGHT_URL}")
    
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
