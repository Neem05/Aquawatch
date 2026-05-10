import random
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# Firebase setup
cred = credentials.Certificate("serviceAcckey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

locations = [
    "Kochi River Station",
    "Vembanad Lake",
    "Kovalam Coast",
    "Periyar Basin"
]

while True:

    reading = {
        "location": random.choice(locations),
        "ph": round(random.uniform(6.5, 8.5), 2),
        "temperature": round(random.uniform(20, 30), 2),
        "do": round(random.uniform(6, 9), 2),
        "turbidity": round(random.uniform(1, 5), 2),
        "salinity": round(random.uniform(15, 35), 2),
        "dwsi": round(random.uniform(65, 90), 2),
        "timestamp": datetime.now().isoformat()
    }

    # Occasionally inject anomaly
    if random.random() < 0.70:  # 70% anomaly rate
        anomaly_type = random.choice(['ph_low', 'ph_high', 'do_low', 'turbidity_high', 'multiple'])
        
        if anomaly_type == 'ph_low':
            reading["ph"] = round(random.uniform(2.5, 5.5), 2)  # Very acidic
            reading["dwsi"] = round(random.uniform(10, 35), 2)  # Critical DWSI
            
        elif anomaly_type == 'ph_high':
            reading["ph"] = round(random.uniform(9.5, 11.5), 2)  # Very alkaline
            reading["dwsi"] = round(random.uniform(10, 35), 2)
            
        elif anomaly_type == 'do_low':
            reading["do"] = round(random.uniform(0.5, 3.0), 2)  # Severe oxygen depletion
            reading["dwsi"] = round(random.uniform(10, 35), 2)
            
        elif anomaly_type == 'turbidity_high':
            reading["turbidity"] = round(random.uniform(15, 50), 2)  # Very cloudy
            reading["dwsi"] = round(random.uniform(10, 35), 2)
            
        else:  # multiple anomalies
            reading["ph"] = round(random.uniform(3, 11), 2)
            reading["do"] = round(random.uniform(0.5, 4), 2)
            reading["turbidity"] = round(random.uniform(15, 50), 2)
            reading["dwsi"] = round(random.uniform(5, 25), 2)

    db.collection("live_readings").document().set(reading)

    print("New Reading:", reading)

    time.sleep(5)