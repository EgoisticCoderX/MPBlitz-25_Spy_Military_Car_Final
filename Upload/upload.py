from flask import Flask, render_template, request
import os
import cv2
import numpy as np
import requests
import base64
from dotenv import load_dotenv
import io
from flask import send_file
from collections import defaultdict
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load API key from .env file
load_dotenv()
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY")

DETECTION_MODELS = {
    "soldier_detection": {
        "name": "Soldier Detection",
        "models": [
            {"id": "civil-soldier/1", "weight": 0.3},
            {"id": "millitaryobjectdetection/6", "weight": 0.25},
            {"id": "hiit/9", "weight": 0.25},
            {"id": "soldier-ijybv-wnxqu/1", "weight": 0.2}
        ],
        "conf": 0.35,
        "color": (0, 255, 0)
    },
    "landmine_detection": {
        "name": "Landmine",
        "models": [{"id": "landmine-k5eze-ylmos/1", "weight": 1}],
        "conf": 0.45,
        "color": (0, 0, 255)
    },
    "aircraft_detection": {
        "name": "Aircraft",
        "models": [{"id": "drone-uav-detection/3", "weight": 0.5},
                   {"id": "fighter-jet-detection/1", "weight": 0.5}],
        "conf": 0.35,
        "color": (255, 0, 0)
    },
    "tank_detection": {
        "name": "Tank",
        "models": [{"id": "tank-sl17s/1", "weight": 1}],
        "conf": 0.45,
        "color": (0, 255, 255)
    },
    "military_equipment": {
        "name": "Equipment",
        "models": [{"id": "military-f5tbj/1", "weight": 0.5},
                   {"id": "weapon-detection-ssvfk/1", "weight": 0.5}],
        "conf": 0.35,
        "color": (255, 0, 255)
    },
    "gun_detection": {
        "name": "Gun",
        "models": [{"id": "weapon-detection-ssvfk/1", "weight": 0.5},
                   {"id": "gun-d8mga/2", "weight": 0.5}],
        "conf": 0.35,
        "color": (128, 0, 128)
    }
}

app = Flask(__name__)

def ensemble_predictions(predictions_list, weights, confidence_threshold):
    """Combine predictions from multiple models using weighted ensemble"""
    if not predictions_list:
        return []
    
    # Group predictions by spatial proximity (simple NMS-like approach)
    final_predictions = []
    
    for i, (predictions, weight) in enumerate(zip(predictions_list, weights)):
        for pred in predictions:
            # Weight the confidence
            weighted_conf = pred.get('confidence', 0) * weight
            if weighted_conf >= confidence_threshold:
                pred_copy = pred.copy()
                pred_copy['confidence'] = weighted_conf
                pred_copy['model_weight'] = weight
                final_predictions.append(pred_copy)
    
    return final_predictions

def call_roboflow_api(image, model_id, confidence_threshold):
    """Call Roboflow API for a single model"""
    url = f"https://detect.roboflow.com/{model_id}?api_key={ROBOFLOW_API_KEY}"
    params = {
        "confidence": confidence_threshold,
        "overlap": 30,
        "format": "json"
    }
    
    _, buffer = cv2.imencode('.jpg', image)
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    
    try:
        response = requests.post(
            url,
            params=params,
            data=img_base64,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            return response.json().get('predictions', [])
        else:
            print(f"API call failed for {model_id}: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error calling API for {model_id}: {str(e)}")
        return []

def process_image_with_models(image, selected_model="all", image_index=0, total_images=1):
    """Process a single image with selected models"""
    print(f"Processing image {image_index + 1}/{total_images}")
    
    original_img = image.copy()
    processed_img = image.copy()
    results = {}
    
    # Determine which models to use based on selection
    if selected_model == "all":
        models_to_process = DETECTION_MODELS
    else:
        # Map dropdown values to model keys
        model_mapping = {
            "soldier": "soldier_detection",
            "landmine": "landmine_detection", 
            "tank": "tank_detection",
            "aircraft": "aircraft_detection",
            "equipment": "military_equipment",
            "gun": "gun_detection"
        }
        if selected_model in model_mapping:
            models_to_process = {model_mapping[selected_model]: DETECTION_MODELS[model_mapping[selected_model]]}
        else:
            models_to_process = DETECTION_MODELS
    
    # Process each detection type
    for detection_key, detection_info in models_to_process.items():
        print(f"Processing {detection_info['name']} for image {image_index + 1}...")
        
        # Get predictions from all models for this detection type
        all_predictions = []
        weights = []
        
        for model_info in detection_info['models']:
            model_id = model_info['id']
            weight = model_info['weight']
            
            predictions = call_roboflow_api(image, model_id, detection_info['conf'])
            all_predictions.append(predictions)
            weights.append(weight)
        
        # Combine predictions using ensemble
        final_predictions = ensemble_predictions(all_predictions, weights, detection_info['conf'])
        
        # Process final predictions for this detection type
        results[detection_key] = []
        color = detection_info['color']
        
        for pred in final_predictions:
            x_center = pred.get('x', 0)
            y_center = pred.get('y', 0)
            width = pred.get('width', 0)
            height = pred.get('height', 0)
            
            x1 = int(x_center - width / 2)
            y1 = int(y_center - height / 2)
            x2 = int(x_center + width / 2)
            y2 = int(y_center + height / 2)
            
            class_name = pred.get('class', 'Unknown')
            confidence = pred.get('confidence', 0)
            
            results[detection_key].append({
                'class': class_name, 
                'confidence': confidence,
                'detection_type': detection_info['name']
            })
            
            # Draw rectangle and label on processed_img
            cv2.rectangle(processed_img, (x1, y1), (x2, y2), color, 2)
            label = f"{detection_info['name']}: {class_name} ({confidence:.2f})"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            cv2.rectangle(processed_img, (x1, y1 - label_size[1] - 10), (x1 + label_size[0], y1), color, -1)
            cv2.putText(processed_img, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    print(f"Completed processing image {image_index + 1}/{total_images}")
    return original_img, processed_img, results

def process_single_image(file, selected_model, image_index, total_images):
    """Process a single image file"""
    try:
        file_bytes = np.frombuffer(file.read(), np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        if image is None:
            print(f"Invalid image file: {file.filename}")
            return None, None, {}
        
        return process_image_with_models(image, selected_model, image_index, total_images)
    except Exception as e:
        print(f"Error processing image {image_index + 1}: {str(e)}")
        return None, None, {}

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Check if files were uploaded
        if 'images' not in request.files:
            return render_template('upload.html', error='No images uploaded')
        
        files = request.files.getlist('images')
        if not files or files[0].filename == '':
            return render_template('upload.html', error='No images selected')
        
        # Check for maximum image limit
        MAX_IMAGES = 10
        valid_files = [f for f in files if f.filename != '']
        if len(valid_files) > MAX_IMAGES:
            return render_template('upload.html', error=f'Maximum {MAX_IMAGES} images allowed. You uploaded {len(valid_files)} images.')
        
        # Get selected model
        selected_model = request.form.get('model', 'all')
        
        print(f"🚀 Processing {len(valid_files)} images with model: {selected_model}")
        print(f"⏱️ Starting tactical scan...")
        
        # Process all uploaded images (parallel processing for better performance)
        all_results = {}
        all_original_images = []
        all_processed_images = []
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=min(len(valid_files), 4)) as executor:
            # Submit all image processing tasks
            future_to_index = {
                executor.submit(process_single_image, file, selected_model, i, len(valid_files)): i 
                for i, file in enumerate(valid_files)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_index):
                original_img, processed_img, results = future.result()
                
                if original_img is not None and processed_img is not None:
                    # Encode images for display
                    _, original_buffer = cv2.imencode('.jpg', original_img)
                    _, processed_buffer = cv2.imencode('.jpg', processed_img)
                    
                    original_base64 = base64.b64encode(original_buffer).decode('utf-8')
                    processed_base64 = base64.b64encode(processed_buffer).decode('utf-8')
                    
                    all_original_images.append(original_base64)
                    all_processed_images.append(processed_base64)
                    
                    # Combine results
                    for key, value in results.items():
                        if key not in all_results:
                            all_results[key] = []
                        all_results[key].extend(value)
        
        total_detections = sum(len(detections) for detections in all_results.values())
        print(f"✅ Completed processing {len(all_original_images)} images")
        print(f"🎯 Total detections found: {total_detections}")
        print(f"⏱️ Tactical scan completed successfully!")
        
        return render_template('upload.html', 
                            results=all_results, 
                            original_images=all_original_images,
                            processed_images=all_processed_images,
                            image_uploaded=True,
                            selected_model=selected_model)
    
    return render_template('upload.html')

if __name__ == "__main__":
    print("🚀 Military AI Detection System Starting...")
    print("📡 API Key Status:", "✅ Loaded" if ROBOFLOW_API_KEY else "❌ Missing")
    print("🌐 Server will be available at: http://localhost:5008")
    app.run(host='0.0.0.0', port=5008, debug=True)  