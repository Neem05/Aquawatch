"""
Vertex AI Model Deployment for AquaWatch
Run this ONCE to deploy your trained models to Vertex AI
"""

import os
import tensorflow as tf
from google.cloud import aiplatform, storage
from datetime import datetime

# Initialize Vertex AI
PROJECT_ID = "cloud-project-74451"
LOCATION = "us-central1"

aiplatform.init(project=PROJECT_ID, location=LOCATION)

def upload_models_to_gcs():
    """Upload your trained models to Cloud Storage"""
    storage_client = storage.Client()
    
    # Create bucket if not exists
    bucket_name = f"aquawatch-models-{PROJECT_ID}"
    bucket = storage_client.bucket(bucket_name)
    
    if not bucket.exists():
        bucket = storage_client.create_bucket(bucket_name, location=LOCATION)
        print(f"✅ Created bucket: {bucket_name}")
    
    # Upload models
    model_files = [
        "../backend/models/water_forecast_model.keras",
        "../backend/models/lstm_model.h5",
        "../backend/models/scaler.pkl",
    ]
    
    for model_file in model_files:
        if os.path.exists(model_file):
            blob_name = f"models/{os.path.basename(model_file)}"
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(model_file)
            print(f"✅ Uploaded: {model_file} -> {blob_name}")
    
    return bucket_name

def deploy_vertex_endpoint():
    """Deploy model to Vertex AI Endpoint"""
    
    # Upload to GCS first
    bucket_name = upload_models_to_gcs()
    model_uri = f"gs://{bucket_name}/models/water_forecast_model.keras"
    
    # Upload model to Vertex AI Model Registry
    model = aiplatform.Model.upload(
        display_name="aquawatch-lstm-model",
        artifact_uri=model_uri,
        serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/tf2-cpu.2-11:latest",
        description="LSTM model for water quality anomaly detection",
    )
    
    print(f"✅ Model uploaded: {model.resource_name}")
    
    # Create endpoint
    endpoint = model.deploy(
        machine_type="n1-standard-2",
        min_replica_count=1,
        max_replica_count=3,
        traffic_split={"0": 100},
    )
    
    print(f"✅ Endpoint created: {endpoint.resource_name}")
    print(f"✅ Endpoint ID: {endpoint.name}")
    
    # Save endpoint ID for backend
    with open("endpoint_id.txt", "w") as f:
        f.write(endpoint.name)
    
    return endpoint

def test_endpoint(endpoint_id):
    """Test the deployed endpoint"""
    endpoint = aiplatform.Endpoint(endpoint_id)
    
    # Test prediction
    test_instance = [{
        "ph": 7.2,
        "temperature": 22.5,
        "do": 8.1,
        "turbidity": 2.3,
        "salinity": 18.5,
    }]
    
    prediction = endpoint.predict(instances=test_instance)
    print(f"✅ Test prediction: {prediction}")
    
    return prediction

if __name__ == "__main__":
    print("🚀 Deploying AquaWatch models to Vertex AI...")
    
    # Deploy endpoint
    endpoint = deploy_vertex_endpoint()
    
    # Test it
    test_endpoint(endpoint.name)
    
    print("\n✅ Vertex AI deployment complete!")
    print(f"📡 Use this Endpoint ID in your backend: {endpoint.name}")