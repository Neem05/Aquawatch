import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model
import joblib
import os
from datetime import datetime
import json

class WaterQualityService:
    def __init__(self):
        self.models_path = "./models"
        self.lstm_model = None
        self.scaler = None
        self.anomaly_threshold = 0.004
        
        self.safe_ranges = {
            'ph': (6.5, 8.5),
            'temperature': (15, 30),
            'do': (5, 12),
            'turbidity': (0, 5),
            'salinity': (0, 35)
        }
        
        self.load_models()
    
    def load_models(self):
        """Load trained models"""
        lstm_path = os.path.join(self.models_path, "water_forecast_model.keras")
        if os.path.exists(lstm_path):
            print(lstm_path)
            self.lstm_model = load_model(lstm_path)
            print("✅ LSTM model loaded")
        
        scaler_path = os.path.join(self.models_path, "scaler.pkl")
        if os.path.exists(scaler_path):
            self.scaler = joblib.load(scaler_path)
            print("✅ Scaler loaded")
    
    def calculate_dwsi(self, data):
        """Dynamic Water Quality Index (0-100)"""
        scores = []
        for param, (low, high) in self.safe_ranges.items():
            if param in data:
                value = float(data[param])
                optimal = (low + high) / 2
                tolerance = (high - low) / 2
                if tolerance > 0:
                    distance = abs(value - optimal) / tolerance
                    score = max(0, min(1, 1 - distance)) * 100
                else:
                    score = 100 if low <= value <= high else 0
                scores.append(score)
        
        if scores:
            return round(sum(scores) / len(scores), 1)
        return 50.0
    
    def get_quality_label(self, dwsi):
        """Get quality label based on DWSI"""
        if dwsi >= 80:
            return {"label": "Excellent", "color": "#00d4aa", "status": "safe"}
        elif dwsi >= 60:
            return {"label": "Good", "color": "#3a9eff", "status": "good"}
        elif dwsi >= 40:
            return {"label": "Moderate", "color": "#f59e0b", "status": "warning"}
        elif dwsi >= 20:
            return {"label": "Poor", "color": "#ef4444", "status": "danger"}
        else:
            return {"label": "Critical", "color": "#dc2626", "status": "critical"}
    
    def analyze_parameters(self, data):
        """Analyze each parameter and return status"""
        results = {}
        for param, (low, high) in self.safe_ranges.items():
            if param in data:
                value = float(data[param])
                is_normal = low <= value <= high
                deviation = 0
                if not is_normal:
                    if value < low:
                        deviation = ((low - value) / low) * 100
                    else:
                        deviation = ((value - high) / high) * 100
                
                results[param] = {
                    "value": value,
                    "min": low,
                    "max": high,
                    "normal": is_normal,
                    "deviation": round(abs(deviation), 1)
                }
        return results
    
    def predict_future(self, historical_data):
        """Predict future water quality"""
        if not historical_data or len(historical_data) < 5:
            return {"trend": "stable", "forecast": [], "confidence": 70}
        
        # Simple trend analysis
        recent_ph = [d.get('ph', 7) for d in historical_data[-10:]]
        if len(recent_ph) > 1:
            trend = recent_ph[-1] - recent_ph[0]
            if trend > 0.2:
                trend_label = "increasing"
                confidence = 75
            elif trend < -0.2:
                trend_label = "decreasing"
                confidence = 75
            else:
                trend_label = "stable"
                confidence = 85
        else:
            trend_label = "stable"
            confidence = 70
        
        # Generate forecast for next 6 hours
        forecast = []
        last_value = recent_ph[-1] if recent_ph else 7
        for i in range(1, 7):
            change = trend * (i / 6) if trend_label != "stable" else 0
            forecast.append({
                "hour": i,
                "ph": round(last_value + change, 2),
                "confidence": max(50, confidence - i * 5)
            })
        
        return {
            "trend": trend_label,
            "forecast": forecast,
            "confidence": confidence
        }
    
    def process_csv_data(self, file_path):
        """Process uploaded CSV file"""
        df = pd.read_csv(file_path)
        results = []
        alias = {
        'pH': 'ph',
        'Dissolved Oxygen': 'do',
        'Temperature': 'temperature',
        'Turbidity': 'turbidity',
        'Salinity': 'salinity'
        }

        required = ['ph', 'temperature', 'do', 'turbidity', 'salinity']
        for col in required:
            if col not in df.columns:
                df[col] = 7.0
        # Rename columns if they exist in the alias
        df.rename(columns=alias, inplace=True)
    # =====================================
        
        for idx, row in df.iterrows():
            data = {
                'ph': row.get('ph', 7),
                'temperature': row.get('temperature', 20),
                'do': row.get('do', 8),
                'turbidity': row.get('turbidity', 2),
                'salinity': row.get('salinity', 20)
            }
            
            dwsi = self.calculate_dwsi(data)
            quality = self.get_quality_label(dwsi)
            parameters = self.analyze_parameters(data)
            
            results.append({
                "id": idx,
                "timestamp": row.get('timestamp', datetime.now().isoformat()),
                "dwsi": dwsi,
                "quality_label": quality['label'],
                "quality_status": quality['status'],
                "parameters": parameters,
                "is_anomaly": dwsi < 40
            })
        
        return results

service = WaterQualityService()