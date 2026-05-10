"""
AquaWatch Cloud Run Backend
Deployed to: https://aquawatch-api-xxx-uc.a.run.app
"""

import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from google.cloud import aiplatform, firestore, storage, pubsub_v1
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

app = Flask(__name__)
CORS(app)

# Configuration
PROJECT_ID = os.environ.get("PROJECT_ID", "cloud-project-74451")
LOCATION = os.environ.get("LOCATION", "us-central1")
ENDPOINT_ID = os.environ.get("ENDPOINT_ID")  # Set from Vertex AI deployment
JWT_SECRET = os.environ.get("JWT_SECRET", "aquawatch-super-secret-key-2024")

app.config['JWT_SECRET_KEY'] = JWT_SECRET
jwt = JWTManager(app)

# Initialize GCP clients
db = firestore.Client(project=PROJECT_ID)
storage_client = storage.Client(project=PROJECT_ID)
publisher = pubsub_v1.PublisherClient()

# Initialize Vertex AI endpoint
aiplatform.init(project=PROJECT_ID, location=LOCATION)
endpoint = aiplatform.Endpoint(ENDPOINT_ID) if ENDPOINT_ID else None

# User database (in production, use Firestore Auth)
USERS = {
    "admin@aquawatch.com": {"password": "admin123", "name": "Administrator", "role": "admin"},
}

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'endpoint_ready': endpoint is not None,
        'firestore_ready': db is not None
    }), 200

@app.route('/api/login', methods=['POST'])
def login():
    """User authentication"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if email in USERS and USERS[email]['password'] == password:
        access_token = create_access_token(
            identity=email,
            expires_delta=timedelta(hours=24)
        )
        return jsonify({
            'success': True,
            'access_token': access_token,
            'user': {
                'email': email,
                'name': USERS[email]['name'],
                'role': USERS[email]['role']
            }
        }), 200
    
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/api/predict', methods=['POST'])
@jwt_required()
def predict():
    """Get prediction from Vertex AI"""
    try:
        data = request.get_json()
        
        # Prepare instance for Vertex AI
        instance = [{
            'ph': float(data.get('ph', 7.0)),
            'temperature': float(data.get('temperature', 22.0)),
            'do': float(data.get('do', 8.0)),
            'turbidity': float(data.get('turbidity', 2.0)),
            'salinity': float(data.get('salinity', 20.0))
        }]
        
        # Call Vertex AI endpoint
        if endpoint:
            prediction = endpoint.predict(instances=instance)
            probability = float(prediction.predictions[0][0] if prediction.predictions else 0.5)
        else:
            # Fallback for testing
            probability = 0.3
        
        is_anomaly = probability > 0.6
        dwsi = calculate_dwsi(data)
        
        # Store in Firestore
        doc_ref = db.collection('predictions').document()
        doc_ref.set({
            'input': data,
            'probability': probability,
            'is_anomaly': is_anomaly,
            'dwsi': dwsi,
            'timestamp': datetime.now(),
            'user': get_jwt_identity()
        })
        
        # Publish to Pub/Sub if anomaly
        if is_anomaly:
            topic_path = publisher.topic_path(PROJECT_ID, 'anomaly-alerts')
            message_data = json.dumps({
                'location': data.get('location', 'Unknown'),
                'dwsi': dwsi,
                'probability': probability,
                'timestamp': datetime.now().isoformat()
            }).encode('utf-8')
            publisher.publish(topic_path, data=message_data)
        
        return jsonify({
            'success': True,
            'probability': probability,
            'is_anomaly': is_anomaly,
            'dwsi': dwsi,
            'status': 'Anomaly detected!' if is_anomaly else 'Normal'
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/live-readings', methods=['GET'])
@jwt_required()
def get_live_readings():
    """Get recent live readings from Firestore"""
    try:
        readings_ref = db.collection('live_readings')
        docs = readings_ref.order_by('timestamp', direction='DESCENDING').limit(50).stream()
        
        readings = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            if data.get('timestamp'):
                data['timestamp'] = data['timestamp'].isoformat()
            readings.append(data)
        
        return jsonify(readings), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def calculate_dwsi(data):
    """Calculate Dynamic Water Quality Index"""
    scores = []
    
    # pH score (6.5-8.5 optimal)
    ph = float(data.get('ph', 7.0))
    if 6.5 <= ph <= 8.5:
        ph_score = 100
    elif 6.0 <= ph <= 9.0:
        ph_score = 50
    else:
        ph_score = 0
    scores.append(ph_score)
    
    # DO score (>6 optimal)
    do = float(data.get('do', 8.0))
    do_score = min(100, max(0, (do / 6) * 100))
    scores.append(do_score)
    
    # Turbidity score (<5 optimal)
    turbidity = float(data.get('turbidity', 2.0))
    turbidity_score = max(0, min(100, 100 - (turbidity * 10)))
    scores.append(turbidity_score)
    
    # Temperature score (15-30 optimal)
    temp = float(data.get('temperature', 22.0))
    if 15 <= temp <= 30:
        temp_score = 100
    elif 10 <= temp <= 35:
        temp_score = 50
    else:
        temp_score = 0
    scores.append(temp_score)
    
    return sum(scores) / len(scores)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)