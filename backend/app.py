from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token
import pandas as pd
import os
from datetime import datetime, timedelta
import uuid
import json

app = Flask(__name__)

# CORS - Allow all origins for development
CORS(app, supports_credentials=True, origins=[
    "http://localhost:3000",
    "http://localhost:3001",
    "https://cloud-project-74451-495908.web.app"
])

# JWT Configuration
app.config['JWT_SECRET_KEY'] = 'aquawatch-secret-key-change-in-production'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
jwt = JWTManager(app)

# Create temp directory for uploads
os.makedirs("temp_uploads", exist_ok=True)

# Store analysis results
uploaded_files = {}
analysis_results = {}

def calculate_dwsi(data):
    """Calculate Dynamic Water Quality Index"""
    score = 0
    ph = float(data.get('ph', 7.0))
    if 6.5 <= ph <= 8.5:
        score += 25
    elif 6.0 <= ph <= 9.0:
        score += 12.5
    
    do = float(data.get('do', 8.0))
    if do >= 6:
        score += 25
    elif do >= 4:
        score += 12.5
    
    turbidity = float(data.get('turbidity', 2.0))
    if turbidity <= 5:
        score += 25
    elif turbidity <= 10:
        score += 12.5
    
    temp = float(data.get('temperature', 22.0))
    if 15 <= temp <= 30:
        score += 25
    elif 10 <= temp <= 35:
        score += 12.5
    
    return score

def process_csv_data(file_path):
    """Process uploaded CSV file and return results"""
    df = pd.read_csv(file_path)
    results = []
    
    for idx, row in df.iterrows():
        data = {
            'ph': float(row.get('ph', 7.0)) if pd.notna(row.get('ph', 7.0)) else 7.0,
            'temperature': float(row.get('temperature', 22.0)) if pd.notna(row.get('temperature', 22.0)) else 22.0,
            'do': float(row.get('do', 8.0)) if pd.notna(row.get('do', 8.0)) else 8.0,
            'turbidity': float(row.get('turbidity', 2.0)) if pd.notna(row.get('turbidity', 2.0)) else 2.0,
            'salinity': float(row.get('salinity', 20.0)) if pd.notna(row.get('salinity', 20.0)) else 20.0
        }
        
        dwsi = calculate_dwsi(data)
        is_anomaly = data['ph'] < 6.5 or data['ph'] > 8.5 or data['do'] < 5 or data['turbidity'] > 10
        
        result = {
            'id': idx,
            'timestamp': datetime.now().isoformat(),
            'dwsi': dwsi,
            'is_anomaly': is_anomaly,
            'quality_label': get_quality_label(dwsi)['label'],
            'quality_status': get_quality_label(dwsi)['status'],
            'parameters': {
                'ph': {'value': data['ph'], 'normal': 6.5 <= data['ph'] <= 8.5},
                'temperature': {'value': data['temperature'], 'normal': 15 <= data['temperature'] <= 30},
                'do': {'value': data['do'], 'normal': data['do'] >= 5},
                'turbidity': {'value': data['turbidity'], 'normal': data['turbidity'] <= 5},
                'salinity': {'value': data['salinity'], 'normal': 15 <= data['salinity'] <= 35}
            }
        }
        results.append(result)
    
    return results

def get_quality_label(dwsi):
    if dwsi >= 80:
        return {"label": "Excellent", "color": "#00d4aa", "status": "safe", "icon": "✅"}
    elif dwsi >= 60:
        return {"label": "Good", "color": "#3a9eff", "status": "good", "icon": "👍"}
    elif dwsi >= 40:
        return {"label": "Moderate", "color": "#f59e0b", "status": "warning", "icon": "⚠️"}
    elif dwsi >= 20:
        return {"label": "Poor", "color": "#ef4444", "status": "danger", "icon": "🔴"}
    else:
        return {"label": "Critical", "color": "#dc2626", "status": "critical", "icon": "💀"}

@app.route("/")
def home():
    return jsonify({"message": "AquaWatch API Running Successfully"}), 200

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()}), 200

@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return '', 200
    
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if email == "admin@aquawatch.com" and password == "admin123":
        access_token = create_access_token(identity=email)
        return jsonify({
            "success": True,
            "access_token": access_token,
            "user": {"email": email, "name": "Administrator", "role": "admin"}
        }), 200
    
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

# ========== FIREBASE COMPATIBLE ENDPOINTS (MISSING ONES ADDED) ==========
@app.route('/api/firebase/live', methods=['GET', 'OPTIONS'])
def firebase_live():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify([]), 200

@app.route('/api/firebase/alerts', methods=['GET', 'OPTIONS'])
def firebase_alerts():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify([]), 200

@app.route('/api/firebase/history', methods=['GET', 'OPTIONS'])
@jwt_required()
def firebase_history():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify([]), 200

# ========== CORE ENDPOINTS ==========
@app.route('/api/dashboard/stats', methods=['GET', 'OPTIONS'])
@jwt_required()
def get_dashboard_stats():
    if request.method == 'OPTIONS':
        return '', 200
    
    return jsonify({
        'total_readings': 1523,
        'anomalies_detected': 47,
        'average_dwsi': 72.4,
        'active_stations': 12,
        'readings_24h': 89
    }), 200

@app.route('/api/live-readings', methods=['GET', 'OPTIONS'])
def get_live_readings():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify([]), 200

@app.route('/api/analyze/upload', methods=['POST', 'OPTIONS'])
@jwt_required()
def analyze_upload():
    if request.method == 'OPTIONS':
        return '', 200
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    file_ext = file.filename.split('.')[-1].lower()
    file_id = str(uuid.uuid4())
    file_path = os.path.join("temp_uploads", f"{file_id}.{file_ext}")
    file.save(file_path)
    
    try:
        if file_ext == 'csv':
            results = process_csv_data(file_path)
        else:
            return jsonify({'error': 'Unsupported file format. Please upload CSV files only.'}), 400
        
        analysis_id = str(uuid.uuid4())
        uploaded_files[analysis_id] = {
            'filename': file.filename,
            'results': results,
            'uploaded_at': datetime.now().isoformat(),
            'user': get_jwt_identity()
        }
        
        os.remove(file_path)
        
        return jsonify({
            'analysis_id': analysis_id,
            'total_records': len(results),
            'anomalies': sum(1 for r in results if r['is_anomaly']),
            'average_dwsi': sum(r['dwsi'] for r in results) / len(results) if results else 0,
            'results': results[:100]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history', methods=['GET', 'OPTIONS'])
@jwt_required()
def get_history():
    if request.method == 'OPTIONS':
        return '', 200
    
    history = []
    for aid, data in list(uploaded_files.items())[-20:]:
        history.append({
            'id': aid,
            'filename': data['filename'],
            'uploaded_at': data['uploaded_at'],
            'total_records': len(data['results']),
            'anomalies': sum(1 for r in data['results'] if r['is_anomaly'])
        })
    return jsonify(history), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
