from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from auth import auth_bp
from water_quality_service import service
import pandas as pd
import os
from datetime import datetime
import uuid
import json
import firebase_admin
from firebase_admin import credentials, firestore


app = Flask(__name__)
# Firebase Initialization
firebase_admin.initialize_app()

db = firestore.client()
CORS(app, origins=["http://localhost:3000", "http://localhost:3001"])

# JWT Configuration
app.config['JWT_SECRET_KEY'] = 'aquawatch-secret-key-change-in-production'
jwt = JWTManager(app)

# Register blueprints
app.register_blueprint(auth_bp)

# Store analysis results (in production, use database)
analysis_results = {}
uploaded_files = {}
@app.route("/")
def home():
    return jsonify({
        "message": "AquaWatch API Running Successfully"
    }), 200


@app.route('/api/dashboard/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """Get dashboard statistics"""
    return jsonify({
        'total_readings': 1523,
        'anomalies_detected': 47,
        'average_dwsi': 72.4,
        'active_stations': 12,
        'readings_24h': 89
    }), 200

@app.route('/api/analyze/single', methods=['POST'])
@jwt_required()
def analyze_single():
    """Analyze a single water quality reading"""
    data = request.get_json()
    
    # Calculate DWSI
    dwsi = service.calculate_dwsi(data)
    quality = service.get_quality_label(dwsi)
    parameters = service.analyze_parameters(data)
    
    # Get historical data (mock)
    historical = [data]  # In production, fetch from DB
    
    # Predict future
    forecast = service.predict_future(historical)
    
    # Prepare response
    result = {
        'id': str(uuid.uuid4()),
        'timestamp': datetime.now().isoformat(),
        'dwsi': dwsi,
        'quality': quality,
        'parameters': parameters,
        'forecast': forecast,
        'is_anomaly': dwsi < 40,
        'recommendations': generate_recommendations(parameters)
    }
    
    # Store result
    analysis_results[result['id']] = result
    
    return jsonify(result), 200

@app.route('/api/analyze/upload', methods=['POST'])
@jwt_required()
def analyze_upload():
    """Analyze uploaded CSV/Excel file"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Save file temporarily
    file_ext = file.filename.split('.')[-1]
    file_id = str(uuid.uuid4())
    temp_dir = "temp_uploads"

    os.makedirs(temp_dir, exist_ok=True)

    file_path = os.path.join(temp_dir, f"{file_id}.{file_ext}")
    file.save(file_path)
    
    # Process based on file type
    try:
        if file_ext in ['csv', 'xlsx', 'xls']:
            results = service.process_csv_data(file_path)
            analysis_id = str(uuid.uuid4())
            db.collection("water_analysis").document(analysis_id).set({
            "analysis_id": analysis_id,
            "filename": file.filename,
            "uploaded_at": datetime.now().isoformat(),
            "user": get_jwt_identity(),
            "results": results
        })
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
        
        # Store results
        
        uploaded_files[analysis_id] = {
            'filename': file.filename,
            'results': results,
            'uploaded_at': datetime.now().isoformat(),
            'user': get_jwt_identity()
        }
        
        # Clean up temp file
        os.remove(file_path)
        
        return jsonify({
            'analysis_id': analysis_id,
            'total_records': len(results),
            'anomalies': sum(1 for r in results if r['is_anomaly']),
            'average_dwsi': sum(r['dwsi'] for r in results) / len(results) if results else 0,
            'results': results[:100]  # Return first 100 results
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/firebase/history', methods=['GET'])
@jwt_required()
def firebase_history():

    docs = db.collection("water_analysis")\
        .order_by("uploaded_at")\
        .stream()

    history = []

    for doc in docs:
        history.append(doc.to_dict())

    return jsonify(history)

@app.route('/api/results/<analysis_id>', methods=['GET'])
@jwt_required()
def get_results(analysis_id):
    """Get analysis results"""
    if analysis_id in uploaded_files:
        return jsonify(uploaded_files[analysis_id]), 200
    return jsonify({'error': 'Results not found'}), 404

@app.route('/api/results/export/<analysis_id>', methods=['GET'])
@jwt_required()
def export_results(analysis_id):
    """Export results as CSV"""
    if analysis_id not in uploaded_files:
        return jsonify({'error': 'Results not found'}), 404
    
    data = uploaded_files[analysis_id]
    df = pd.DataFrame(data['results'])
    
    # Flatten parameters for export
    for col in ['ph', 'temperature', 'do', 'turbidity', 'salinity']:
        df[col] = df['parameters'].apply(lambda x: x.get(col, {}).get('value', 0))
    
    export_path = f"/tmp/export_{analysis_id}.csv"
    df.to_csv(export_path, index=False)
    
    return send_file(
        export_path,
        as_attachment=True,
        download_name=f"water_quality_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mimetype='text/csv'
    )

@app.route('/api/history', methods=['GET'])
@jwt_required()
def get_history():
    """Get analysis history"""
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

def generate_recommendations(parameters):
    """Generate recommendations based on parameters"""
    recommendations = []
    
    for param, data in parameters.items():
        if not data['normal']:
            if param == 'ph':
                if data['value'] < data['min']:
                    recommendations.append("⚠️ pH is too low. Consider adding alkaline substances.")
                else:
                    recommendations.append("⚠️ pH is too high. Consider acidification treatment.")
            elif param == 'do':
                if data['value'] < data['min']:
                    recommendations.append("💨 Low dissolved oxygen. Increase aeration.")
            elif param == 'turbidity':
                if data['value'] > data['max']:
                    recommendations.append("🌫️ High turbidity. Check for sedimentation or runoff.")
            elif param == 'temperature':
                if data['value'] > data['max']:
                    recommendations.append("🌡️ Water temperature elevated. Check for thermal pollution.")
    
    if not recommendations:
        recommendations.append("✅ All parameters within normal range. Water quality is good.")
    
    return recommendations

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
