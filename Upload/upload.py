# # from flask import Flask, render_template, request, jsonify
# # import os
# # import cv2
# # import numpy as np
# # import requests
# # import base64
# # from dotenv import load_dotenv
# # import io
# # from concurrent.futures import ThreadPoolExecutor
# # import json

# # # Load API key from .env file
# # load_dotenv()
# # ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY")

# # # A single, common group for all models
# # # Each model has a unique ID, a display name, a confidence threshold, and a color for the bounding box
# # ALL_MODELS = [
# #     {"id": "tank-2xykr/3", "name": "Tank Model 1", "conf": 0.45, "color": (255, 100, 0)},
# #     {"id": "squad2.0.1-3kc5d/1", "name": "Squad Detection", "conf": 0.4, "color": (0, 255, 0)},
# #     {"id": "vehicles-urcin/1", "name": "Vehicle Detection", "conf": 0.35, "color": (255, 255, 0)},
# #     {"id": "mrtod/2", "name": "MRTOD", "conf": 0.3, "color": (128, 0, 128)},
# #     {"id": "military-base-object-detection/12", "name": "Base Object Detection", "conf": 0.5, "color": (255, 0, 255)},
# #     {"id": "terrorist-and-no-terrorist-detection/2", "name": "Threat Detection", "conf": 0.4, "color": (255, 0, 0)},
# #     {"id": "potongpt/2", "name": "PotongPT", "conf": 0.25, "color": (0, 128, 128)},
# #     {"id": "military-aircraft-classification-jqcxg/3", "name": "Aircraft Classify v3", "conf": 0.4, "color": (0, 0, 255)},
# #     {"id": "military-aircraft-classification-jqcxg/4", "name": "Aircraft Classify v4", "conf": 0.4, "color": (0, 100, 255)},
# #     {"id": "data-bmhtk/2", "name": "Data BMHTK", "conf": 0.3, "color": (100, 100, 100)},
# #     {"id": "jet-plane/1", "name": "Jet Plane", "conf": 0.45, "color": (0, 200, 255)},
# #     {"id": "landmine-b4bhi/1", "name": "Landmine v1", "conf": 0.5, "color": (255, 165, 0)},
# #     {"id": "pistol-fire-and-gun/1", "name": "Pistol/Gun Fire", "conf": 0.4, "color": (255, 215, 0)},
# #     {"id": "gun-and-weapon-detection/1", "name": "Weapon Detection v1", "conf": 0.35, "color": (255, 192, 203)},
# #     {"id": "knife-and-gun-modelv2/2", "name": "Knife/Gun v2", "conf": 0.35, "color": (218, 112, 214)},
# #     {"id": "military-and-civilian-vehicles-lzha5/1", "name": "Mil/Civ Vehicles", "conf": 0.4, "color": (0, 255, 127)},
# #     {"id": "civil-soldier/1", "name": "Civilian/Soldier", "conf": 0.4, "color": (173, 255, 47)},
# #     {"id": "landmine-k5eze-ylmos/1", "name": "Landmine v2", "conf": 0.5, "color": (255, 140, 0)},
# #     {"id": "millitaryobjectdetection/6", "name": "Military Object v6", "conf": 0.35, "color": (32, 178, 170)},
# #     {"id": "hiit/9", "name": "HIIT Detection", "conf": 0.3, "color": (135, 206, 250)},
# #     {"id": "soldier-ijybv-wnxqu/1", "name": "Soldier Detection", "conf": 0.4, "color": (60, 179, 113)},
# #     {"id": "drone-uav-detection/3", "name": "Drone/UAV Detection", "conf": 0.45, "color": (106, 90, 205)},
# #     {"id": "fighter-jet-detection/1", "name": "Fighter Jet Detection", "conf": 0.45, "color": (72, 61, 139)},
# #     {"id": "tank-sl17s/1", "name": "Tank Model 2", "conf": 0.5, "color": (255, 99, 71)},
# #     {"id": "military-f5tbj/1", "name": "Military Equipment", "conf": 0.35, "color": (188, 143, 143)},
# #     {"id": "weapon-detection-ssvfk/1", "name": "Weapon Detection v2", "conf": 0.4, "color": (255, 20, 147)},
# #     {"id": "gun-d8mga/2", "name": "Gun Model v2", "conf": 0.45, "color": (219, 112, 147)},
# # ]

# # app = Flask(__name__)

# # def call_roboflow_api(image_bytes, model_info):
# #     model_id = model_info["id"]
# #     confidence_threshold = model_info["conf"]
# #     print(f"Executing analysis with model: {model_info['name']}...")
# #     url = f"https://detect.roboflow.com/{model_id}?api_key={ROBOFLOW_API_KEY}"
# #     params = {"confidence": confidence_threshold, "overlap": 30, "format": "json"}
# #     img_base64 = base64.b64encode(image_bytes).decode('utf-8')
# #     try:
# #         response = requests.post(url, params=params, data=img_base64, headers={"Content-Type": "application/x-www-form-urlencoded"})
# #         if response.status_code == 200:
# #             print(f"SUCCESS: Model '{model_info['name']}' analysis complete.")
# #             return model_info, response.json().get('predictions', [])
# #         else:
# #             print(f"WARNING: API call failed for '{model_info['name']}'. Status: {response.status_code}.")
# #             return model_info, []
# #     except Exception as e:
# #         print(f"ERROR: Exception during API call for '{model_info['name']}': {e}")
# #         return model_info, []

# # def process_image(image_file):
# #     try:
# #         image_bytes = image_file.read()
# #         image_np = np.frombuffer(image_bytes, np.uint8)
# #         image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
# #         if image is None: return None, None, []
# #     except Exception as e:
# #         print(f"ERROR: Could not read image '{image_file.filename}'. Details: {e}")
# #         return None, None, []

# #     original_img_encoded = base64.b64encode(cv2.imencode('.jpg', image)[1]).decode('utf-8')
# #     processed_img = image.copy()
# #     all_detections = []

# #     with ThreadPoolExecutor(max_workers=len(ALL_MODELS)) as executor:
# #         _, buffer = cv2.imencode('.jpg', image)
# #         image_bytes_for_api = buffer.tobytes()
# #         future_to_model = {executor.submit(call_roboflow_api, image_bytes_for_api, model): model for model in ALL_MODELS}
        
# #         for future in future_to_model:
# #             model_info, predictions = future.result()
# #             if predictions:
# #                 for pred in predictions:
# #                     all_detections.append({"model_name": model_info['name'], "class": pred.get('class', 'Unknown'), "confidence": f"{pred.get('confidence', 0):.2f}"})
# #                     x1, y1, x2, y2 = int(pred['x'] - pred['width']/2), int(pred['y'] - pred['height']/2), int(pred['x'] + pred['width']/2), int(pred['y'] + pred['height']/2)
# #                     cv2.rectangle(processed_img, (x1, y1), (x2, y2), model_info['color'], 2)
# #                     label = f"{model_info['name']}: {pred.get('class', 'N/A')} ({pred.get('confidence', 0):.2f})"
# #                     label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
# #                     cv2.rectangle(processed_img, (x1, y1 - label_size[1] - 10), (x1 + label_size[0], y1), model_info['color'], -1)
# #                     cv2.putText(processed_img, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

# #     processed_img_encoded = base64.b64encode(cv2.imencode('.jpg', processed_img)[1]).decode('utf-8')
# #     all_detections.sort(key=lambda x: x['confidence'], reverse=True)
# #     return original_img_encoded, processed_img_encoded, all_detections

# # @app.route('/', methods=['GET', 'POST'])
# # def index():
# #     model_names_json = json.dumps([model['name'] for model in ALL_MODELS])
# #     if request.method == 'POST':
# #         if 'image' not in request.files or request.files['image'].filename == '':
# #             return render_template('upload.html', error='No image file provided. Please select a file to scan.', model_names_json=model_names_json)
        
# #         file = request.files['image']
# #         print(f"\n🚀 INITIATING TACTICAL SCAN FOR: {file.filename}")
# #         original, processed, results = process_image(file)

# #         if original is None:
# #             return render_template('upload.html', error=f"Failed to process {file.filename}. The file may be unsupported or corrupt.", model_names_json=model_names_json)

# #         print(f"✅ TACTICAL SCAN COMPLETE. TOTAL DETECTIONS: {len(results)}\n")
# #         return render_template('upload.html', original_image=original, processed_image=processed, results=results, image_uploaded=True, model_names_json=model_names_json)

# #     return render_template('upload.html', model_names_json=model_names_json)

# # if __name__ == "__main__":
# #     if not ROBOFLOW_API_KEY:
# #         print("!!! ERROR: ROBOFLOW_API_KEY not found in .env file !!!")
# #     else:
# #         print("✅ Roboflow API Key loaded.")
# #     print("🚀 TACTICAL MILITARY AI DETECTION SYSTEM BOOTING UP...")
# #     print("🌐 Server operational at: http://127.0.0.1:5008")
# #     app.run(host='0.0.0.0', port=5008)
# from flask import Flask, render_template, request, jsonify
# import os
# import cv2
# import numpy as np
# import requests
# import base64
# from dotenv import load_dotenv
# from concurrent.futures import ThreadPoolExecutor
# import json

# # Load environment variables from the .env file
# load_dotenv()
# ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY")

# # A single, unified list of all AI models for the comprehensive analysis
# ALL_MODELS = [
#     {"id": "tank-2xykr/3", "name": "Tank Model 1", "conf": 0.45, "color": (255, 100, 0)},
#     {"id": "squad2.0.1-3kc5d/1", "name": "Squad Detection", "conf": 0.4, "color": (0, 255, 0)},
#     {"id": "vehicles-urcin/1", "name": "Vehicle Detection", "conf": 0.35, "color": (255, 255, 0)},
#     {"id": "mrtod/2", "name": "MRTOD", "conf": 0.3, "color": (128, 0, 128)},
#     {"id": "military-base-object-detection/12", "name": "Base Object Detection", "conf": 0.5, "color": (255, 0, 255)},
#     {"id": "terrorist-and-no-terrorist-detection/2", "name": "Threat Detection", "conf": 0.4, "color": (255, 0, 0)},
#     {"id": "potongpt/2", "name": "PotongPT", "conf": 0.25, "color": (0, 128, 128)},
#     {"id": "military-aircraft-classification-jqcxg/3", "name": "Aircraft Classify v3", "conf": 0.4, "color": (0, 0, 255)},
#     {"id": "military-aircraft-classification-jqcxg/4", "name": "Aircraft Classify v4", "conf": 0.4, "color": (0, 100, 255)},
#     {"id": "data-bmhtk/2", "name": "Data BMHTK", "conf": 0.3, "color": (100, 100, 100)},
#     {"id": "jet-plane/1", "name": "Jet Plane", "conf": 0.45, "color": (0, 200, 255)},
#     {"id": "landmine-b4bhi/1", "name": "Landmine v1", "conf": 0.5, "color": (255, 165, 0)},
#     {"id": "pistol-fire-and-gun/1", "name": "Pistol/Gun Fire", "conf": 0.4, "color": (255, 215, 0)},
#     {"id": "gun-and-weapon-detection/1", "name": "Weapon Detection v1", "conf": 0.35, "color": (255, 192, 203)},
#     {"id": "knife-and-gun-modelv2/2", "name": "Knife/Gun v2", "conf": 0.35, "color": (218, 112, 214)},
#     {"id": "military-and-civilian-vehicles-lzha5/1", "name": "Mil/Civ Vehicles", "conf": 0.4, "color": (0, 255, 127)},
#     {"id": "civil-soldier/1", "name": "Civilian/Soldier", "conf": 0.4, "color": (173, 255, 47)},
#     {"id": "landmine-k5eze-ylmos/1", "name": "Landmine v2", "conf": 0.5, "color": (255, 140, 0)},
#     {"id": "millitaryobjectdetection/6", "name": "Military Object v6", "conf": 0.35, "color": (32, 178, 170)},
#     {"id": "hiit/9", "name": "HIIT Detection", "conf": 0.3, "color": (135, 206, 250)},
#     {"id": "soldier-ijybv-wnxqu/1", "name": "Soldier Detection", "conf": 0.4, "color": (60, 179, 113)},
#     {"id": "drone-uav-detection/3", "name": "Drone/UAV Detection", "conf": 0.45, "color": (106, 90, 205)},
#     {"id": "fighter-jet-detection/1", "name": "Fighter Jet Detection", "conf": 0.45, "color": (72, 61, 139)},
#     {"id": "tank-sl17s/1", "name": "Tank Model 2", "conf": 0.5, "color": (255, 99, 71)},
#     {"id": "military-f5tbj/1", "name": "Military Equipment", "conf": 0.35, "color": (188, 143, 143)},
#     {"id": "weapon-detection-ssvfk/1", "name": "Weapon Detection v2", "conf": 0.4, "color": (255, 20, 147)},
#     {"id": "gun-d8mga/2", "name": "Gun Model v2", "conf": 0.45, "color": (219, 112, 147)},
# ]

# app = Flask(__name__)

# def call_roboflow_api(image_bytes, model_info):
#     """Makes a single API call to Roboflow for a given model."""
#     model_id, conf, name = model_info["id"], model_info["conf"], model_info["name"]
#     url = f"https://detect.roboflow.com/{model_id}?api_key={ROBOFLOW_API_KEY}"
#     params = {"confidence": conf, "overlap": 30, "format": "json"}
#     img_base64 = base64.b64encode(image_bytes).decode('utf-8')
#     try:
#         response = requests.post(url, params=params, data=img_base64, headers={"Content-Type": "application/x-www-form-urlencoded"})
#         response.raise_for_status() # Raise an exception for bad HTTP status codes
#         return model_info, response.json().get('predictions', [])
#     except requests.exceptions.RequestException as e:
#         print(f"WARNING: API call failed for '{name}'. Details: {e}")
#         return model_info, []

# def process_single_image(image_file):
#     """Processes one image against all models."""
#     filename = image_file.filename
#     print(f"\nProcessing Image: {filename}")
#     try:
#         image_bytes = image_file.read()
#         image_np = np.frombuffer(image_bytes, np.uint8)
#         image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
#         if image is None: raise ValueError("Image could not be decoded by OpenCV.")
#     except Exception as e:
#         print(f"ERROR: Could not read or decode image '{filename}'. Details: {e}")
#         return None

#     original_img_encoded = base64.b64encode(cv2.imencode('.jpg', image)[1]).decode('utf-8')
#     processed_img = image.copy()
#     all_detections = []

#     # Use a ThreadPoolExecutor to call all models concurrently for this single image
#     with ThreadPoolExecutor(max_workers=len(ALL_MODELS)) as executor:
#         _, buffer = cv2.imencode('.jpg', image)
#         image_bytes_for_api = buffer.tobytes()
#         future_to_model = {executor.submit(call_roboflow_api, image_bytes_for_api, model): model for model in ALL_MODELS}
        
#         for future in future_to_model:
#             try:
#                 model_info, predictions = future.result()
#                 if predictions:
#                     for pred in predictions:
#                         all_detections.append({
#                             "model_name": model_info['name'],
#                             "class": pred.get('class', 'Unknown'),
#                             "confidence": f"{pred.get('confidence', 0):.2f}"
#                         })
#                         x, y, w, h = pred['x'], pred['y'], pred['width'], pred['height']
#                         x1, y1 = int(x - w / 2), int(y - h / 2)
#                         x2, y2 = int(x + w / 2), int(y + h / 2)
                        
#                         color = model_info['color']
#                         cv2.rectangle(processed_img, (x1, y1), (x2, y2), color, 2)
#                         label = f"{model_info['name']}: {pred.get('class', 'N/A')} ({pred.get('confidence', 0):.2f})"
#                         label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
#                         cv2.rectangle(processed_img, (x1, y1 - label_size[1] - 10), (x1 + label_size[0], y1), color, -1)
#                         cv2.putText(processed_img, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
#             except Exception as exc:
#                  print(f"An exception occurred while processing a model's prediction result: {exc}")

#     processed_img_encoded = base64.b64encode(cv2.imencode('.jpg', processed_img)[1]).decode('utf-8')
#     all_detections.sort(key=lambda x: float(x['confidence']), reverse=True)
    
#     print(f"Completed processing for {filename}. Total detections found: {len(all_detections)}")
    
#     # Return a dictionary with all the data for one image
#     return {
#         "filename": filename,
#         "original": original_img_encoded,
#         "processed": processed_img_encoded,
#         "results": all_detections
#     }


# @app.route('/')
# def index():
#     """Serves the main HTML page."""
#     return render_template('upload.html')

# @app.route('/process_batch', methods=['POST'])
# def process_batch_route():
#     """API endpoint to handle the batch processing of multiple images."""
#     if 'images' not in request.files:
#         return jsonify({"error": "No files part in the request."}), 400

#     files = request.files.getlist('images')
#     if not files or files[0].filename == '':
#         return jsonify({"error": "No selected files."}), 400
        
#     if len(files) > 10:
#         return jsonify({"error": f"Cannot process more than 10 images at a time. You sent {len(files)}."}), 400

#     print(f"🚀 INITIATING TACTICAL SCAN FOR A BATCH OF {len(files)} IMAGES.")
    
#     batch_results = []
#     # Use a ThreadPoolExecutor to process multiple IMAGES in parallel.
#     # Each image processing task will itself use another ThreadPoolExecutor to process MODELS in parallel.
#     with ThreadPoolExecutor(max_workers=4) as executor: # Adjust max_workers based on your machine's CPU/network capability
#         future_to_file = {executor.submit(process_single_image, f): f for f in files}
#         for future in future_to_file:
#             result = future.result()
#             if result:
#                 batch_results.append(result)
    
#     print(f"✅ BATCH SCAN COMPLETE. SUCCESSFULLY PROCESSED {len(batch_results)} OF {len(files)} IMAGES.")
    
#     return jsonify({"batch_results": batch_results})


# if __name__ == "__main__":
#     if not ROBOFLOW_API_KEY:
#         print("!!! FATAL ERROR: ROBOFLOW_API_KEY not found in .env file. The application cannot start.")
#     else:
#         print("✅ Roboflow API Key loaded successfully.")
    
#     print("🚀 TACTICAL MILITARY AI DETECTION SYSTEM BOOTING UP...")
#     print("🌐 Server operational at: http://127.0.0.1:5008")
#     app.run(host='0.0.0.0', port=5008)
from flask import Flask, render_template, request, jsonify
import os
import cv2
import numpy as np
import requests
import base64
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
import google.generativeai as genai
from PIL import Image
import io
import json

# --- Configuration ---
load_dotenv()
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Unified list of all AI models
ALL_MODELS = [
    {"id": "tank-2xykr/3", "name": "Tank Model 1", "conf": 0.45, "color": (255, 100, 0)},
    {"id": "squad2.0.1-3kc5d/1", "name": "Squad Detection", "conf": 0.4, "color": (0, 255, 0)},
    {"id": "vehicles-urcin/1", "name": "Vehicle Detection", "conf": 0.35, "color": (255, 255, 0)},
    {"id": "mrtod/2", "name": "MRTOD", "conf": 0.3, "color": (128, 0, 128)},
    {"id": "military-base-object-detection/12", "name": "Base Object Detection", "conf": 0.5, "color": (255, 0, 255)},
    {"id": "terrorist-and-no-terrorist-detection/2", "name": "Threat Detection", "conf": 0.4, "color": (255, 0, 0)},
    {"id": "potongpt/2", "name": "PotongPT", "conf": 0.25, "color": (0, 128, 128)},
    {"id": "military-aircraft-classification-jqcxg/3", "name": "Aircraft Classify v3", "conf": 0.4, "color": (0, 0, 255)},
    {"id": "military-aircraft-classification-jqcxg/4", "name": "Aircraft Classify v4", "conf": 0.4, "color": (0, 100, 255)},
    {"id": "data-bmhtk/2", "name": "Data BMHTK", "conf": 0.3, "color": (100, 100, 100)},
    {"id": "jet-plane/1", "name": "Jet Plane", "conf": 0.45, "color": (0, 200, 255)},
    {"id": "landmine-b4bhi/1", "name": "Landmine v1", "conf": 0.5, "color": (255, 165, 0)},
    {"id": "pistol-fire-and-gun/1", "name": "Pistol/Gun Fire", "conf": 0.4, "color": (255, 215, 0)},
    {"id": "gun-and-weapon-detection/1", "name": "Weapon Detection v1", "conf": 0.35, "color": (255, 192, 203)},
    {"id": "knife-and-gun-modelv2/2", "name": "Knife/Gun v2", "conf": 0.35, "color": (218, 112, 214)},
    {"id": "military-and-civilian-vehicles-lzha5/1", "name": "Mil/Civ Vehicles", "conf": 0.4, "color": (0, 255, 127)},
    {"id": "civil-soldier/1", "name": "Civilian/Soldier", "conf": 0.4, "color": (173, 255, 47)},
    {"id": "landmine-k5eze-ylmos/1", "name": "Landmine v2", "conf": 0.5, "color": (255, 140, 0)},
    {"id": "millitaryobjectdetection/6", "name": "Military Object v6", "conf": 0.35, "color": (32, 178, 170)},
    {"id": "hiit/9", "name": "HIIT Detection", "conf": 0.3, "color": (135, 206, 250)},
    {"id": "soldier-ijybv-wnxqu/1", "name": "Soldier Detection", "conf": 0.4, "color": (60, 179, 113)},
    {"id": "drone-uav-detection/3", "name": "Drone/UAV Detection", "conf": 0.45, "color": (106, 90, 205)},
    {"id": "fighter-jet-detection/1", "name": "Fighter Jet Detection", "conf": 0.45, "color": (72, 61, 139)},
    {"id": "tank-sl17s/1", "name": "Tank Model 2", "conf": 0.5, "color": (255, 99, 71)},
    {"id": "military-f5tbj/1", "name": "Military Equipment", "conf": 0.35, "color": (188, 143, 143)},
    {"id": "weapon-detection-ssvfk/1", "name": "Weapon Detection v2", "conf": 0.4, "color": (255, 20, 147)},
    {"id": "gun-d8mga/2", "name": "Gun Model v2", "conf": 0.45, "color": (219, 112, 147)},
]

app = Flask(__name__)

def calculate_iou(boxA, boxB):
    xA, yA = max(boxA['x1'], boxB['x1']), max(boxA['y1'], boxB['y1'])
    xB, yB = min(boxA['x2'], boxB['x2']), min(boxA['y2'], boxB['y2'])
    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = (boxA['x2'] - boxA['x1']) * (boxA['y2'] - boxA['y1'])
    boxBArea = (boxB['x2'] - boxB['x1']) * (boxB['y2'] - boxB['y1'])
    return interArea / float(boxAArea + boxBArea - interArea) if (boxAArea + boxBArea - interArea) > 0 else 0

def non_max_suppression(predictions, iou_threshold=0.4):
    predictions = sorted(predictions, key=lambda p: p['confidence'], reverse=True)
    kept_predictions = []
    while predictions:
        best_pred = predictions.pop(0)
        kept_predictions.append(best_pred)
        predictions = [p for p in predictions if calculate_iou(best_pred, p) < iou_threshold]
    return kept_predictions

def call_roboflow_api(image_bytes, model_info):
    model_id, conf, name = model_info["id"], model_info["conf"], model_info["name"]
    url = f"https://detect.roboflow.com/{model_id}?api_key={ROBOFLOW_API_KEY}"
    params = {"confidence": conf, "overlap": 30, "format": "json"}
    try:
        response = requests.post(url, params=params, data=base64.b64encode(image_bytes).decode('utf-8'), headers={"Content-Type": "application/x-www-form-urlencoded"})
        response.raise_for_status()
        return model_info, response.json().get('predictions', [])
    except requests.exceptions.RequestException as e:
        # This will now print the error but not stop the entire process
        print(f"WARNING: Roboflow API call failed for '{name}'. Status: {e.response.status_code if e.response else 'N/A'}")
        return model_info, []

def apply_heuristic_filter(predictions):
    print("INFO: Applying Stage 1 Heuristic Filter...")
    ground_vehicles = [p for p in predictions if any(cls in p['class_name'] for cls in ['tank', 'vehicle'])]
    aircraft = [p for p in predictions if any(cls in p['class_name'] for cls in ['aircraft', 'jet', 'plane', 'drone', 'uav'])]
    
    final_predictions = []
    for pred in predictions:
        is_error = False
        pred_class = pred['class_name']

        # Rule 1: Remove landmines found on any vehicle
        if 'landmine' in pred_class:
            if any(calculate_iou(pred, v) > 0.01 for v in ground_vehicles + aircraft):
                print(f"FILTERED (Heuristic): Suppressed illogical '{pred_class}' on a vehicle.")
                is_error = True
        
        # Rule 2: Remove any aircraft detection that significantly overlaps with a ground vehicle
        if pred in aircraft:
            if any(calculate_iou(pred, gv) > 0.2 for gv in ground_vehicles):
                print(f"FILTERED (Heuristic): Suppressed illogical '{pred_class}' overlapping with a ground vehicle.")
                is_error = True

        # Rule 3: Remove any ground vehicle detection that significantly overlaps with an aircraft
        if pred in ground_vehicles:
             if any(calculate_iou(pred, ac) > 0.2 for ac in aircraft):
                print(f"FILTERED (Heuristic): Suppressed illogical '{pred_class}' overlapping with an aircraft.")
                is_error = True

        if not is_error:
            final_predictions.append(pred)
    
    print(f"INFO: Heuristic filter complete. Kept {len(final_predictions)} of {len(predictions)} detections.")
    return final_predictions

def verify_detections_with_gemini(image_bytes, predictions_log):
    if not GEMINI_API_KEY or not predictions_log:
        print("INFO: Gemini API key not found or no detections to verify. Skipping AI verification.")
        return predictions_log

    print("INFO: Initiating Stage 2 AI Verification with Gemini...")
    try:
        img = Image.open(io.BytesIO(image_bytes))
        # FIXED: Updated to a current and powerful vision model name
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        prompt = (
             "You are an expert military intelligence analyst AI. I will provide an image and a JSON list of initial object detections. "
             "Your task is to review these detections for contextual and logical accuracy. Remove any detections that are implausible. "
             "Keep plausible but unusual events (e.g., a civilian car on a military base is plausible). "
             "Focus on removing clear errors based on these rules:\n"
             "1. **Attachment Errors:** A tank's wheel cannot be a 'landmine'. An antenna cannot be a 'pistol'.\n"
             "2. **Containment Errors:** A 'fighter jet' cannot be inside a 'tank', or vice versa.\n"
             "3. **Environmental Errors:** A 'soldier' or 'tank' cannot be floating in the open sky. A 'jet' cannot be driving on a normal road unless it is being transported.\n"
             "4. **Severe Misidentification:** If an object is clearly a tree but labeled a 'soldier', remove the 'soldier' label.\n\n"
             "Your final output must be ONLY the provided JSON, filtered to include just the detections you deem valid. Do not add, re-label, or explain. Just return the corrected JSON list.\n\n"
             f"INITIAL DETECTIONS:\n{json.dumps(predictions_log, indent=2)}"
        )
        
        response = model.generate_content([prompt, img])
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        verified_predictions = json.loads(cleaned_response)
        
        print(f"INFO: Gemini verification complete. Kept {len(verified_predictions)} of {len(predictions_log)} detections.")
        return verified_predictions
    except Exception as e:
        print(f"ERROR: Gemini verification failed. Returning unverified detections. Details: {e}")
        return predictions_log

def process_single_image(image_file):
    filename = image_file.filename
    print(f"\n--- Starting Full Analysis for {filename} ---")
    try:
        image_bytes = image_file.read()
        image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if image is None: raise ValueError("OpenCV could not decode image.")
    except Exception as e:
        print(f"ERROR: Failed to read/decode image file {filename}. Reason: {e}")
        return None

    # Step 1: Roboflow Raw Detections
    all_raw_predictions = []
    with ThreadPoolExecutor(max_workers=len(ALL_MODELS)) as executor:
        _, buffer = cv2.imencode('.jpg', image); api_image_bytes = buffer.tobytes()
        future_to_model = {executor.submit(call_roboflow_api, api_image_bytes, model): model for model in ALL_MODELS}
        for future in future_to_model:
            model_info, predictions = future.result()
            for p in predictions:
                x, y, w, h = p['x'], p['y'], p['width'], p['height']
                all_raw_predictions.append({
                    'x1': int(x - w / 2), 'y1': int(y - h / 2), 'x2': int(x + w / 2), 'y2': int(y + h / 2),
                    'class_name': p.get('class', 'Unknown').lower(),
                    'confidence': p.get('confidence', 0), 'model_info': model_info
                })
    
    # Step 2: Non-Maximal Suppression
    suppressed_predictions = non_max_suppression(all_raw_predictions, iou_threshold=0.4)
    
    # Step 3: Stage 1 Verification (Heuristics)
    heuristically_filtered_predictions = apply_heuristic_filter(suppressed_predictions)
    
    # Step 4: Stage 2 Verification (AI)
    log_for_gemini = [{"model_name": p['model_info']['name'], "class": p['class_name'], "confidence": f"{p['confidence']:.2f}"} for p in heuristically_filtered_predictions]
    final_verified_log = verify_detections_with_gemini(api_image_bytes, log_for_gemini)

    # Step 5: Draw final, doubly-verified boxes
    processed_img = image.copy()
    verified_items_set = {(item['class'], item['model_name']) for item in final_verified_log}
    
    for pred in heuristically_filtered_predictions:
        if (pred['class_name'], pred['model_info']['name']) in verified_items_set:
            color = pred['model_info']['color']
            cv2.rectangle(processed_img, (pred['x1'], pred['y1']), (pred['x2'], pred['y2']), color, 2)
            label = f"{pred['model_info']['name']}: {pred['class_name'].capitalize()} ({pred['confidence']:.2f})"
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(processed_img, (pred['x1'], pred['y1'] - label_size[1] - 10), (pred['x1'] + label_size[0], pred['y1']), color, -1)
            cv2.putText(processed_img, label, (pred['x1'], pred['y1'] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    original_img_encoded = base64.b64encode(cv2.imencode('.jpg', image)[1]).decode('utf-8')
    processed_img_encoded = base64.b64encode(cv2.imencode('.jpg', processed_img)[1]).decode('utf-8')
    final_verified_log.sort(key=lambda x: float(x['confidence']), reverse=True)
    
    print(f"--- Analysis Complete for {filename}. Final verified detections: {len(final_verified_log)} ---")
    
    return {"filename": filename, "original": original_img_encoded, "processed": processed_img_encoded, "results": final_verified_log}


# --- Flask routes are unchanged ---
@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/process_batch', methods=['POST'])
def process_batch_route():
    if 'images' not in request.files: return jsonify({"error": "No files part."}), 400
    files = request.files.getlist('images')
    if not files or files[0].filename == '': return jsonify({"error": "No selected files."}), 400
    
    batch_results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_file = {executor.submit(process_single_image, f): f for f in files}
        for future in future_to_file:
            result = future.result()
            if result:
                batch_results.append(result)
    
    return jsonify({"batch_results": batch_results})

if __name__ == "__main__":
    # Crucial check for API keys on startup
    if not ROBOFLOW_API_KEY:
        print("!!! FATAL ERROR: ROBOFLOW_API_KEY not found in .env file. The application cannot start.")
    elif len(ROBOFLOW_API_KEY) < 10: # Simple check to see if the key is just a placeholder
        print(f"!!! FATAL ERROR: The ROBOFLOW_API_KEY in your .env file seems invalid. Please check it.")
    else:
        print("✅ Roboflow API Key loaded successfully.")
    
    if not GEMINI_API_KEY:
        print("!!! WARNING: GEMINI_API_KEY not found. The AI verification step (Stage 2) will be skipped.")
    elif len(GEMINI_API_KEY) < 20:
        print(f"!!! WARNING: The GEMINI_API_KEY in your .env file seems invalid. AI verification may fail.")
    else:
        print("✅ Gemini API Key loaded successfully. Stage 2 Verification is enabled.")

    print("🚀 TACTICAL MILITARY AI DETECTION SYSTEM BOOTING UP...")
    app.run(host='0.0.0.0', port=5008)
