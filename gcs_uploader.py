"""
Google Cloud Storage Uploader for podcast files.
Replaces SFTP upload with GCS upload for Cloud Run environment.
"""
from google.cloud import storage
from datetime import datetime
import os

# GCS Configuration
BUCKET_NAME = "news-crawler-podcasts"
# Public URL pattern for Flask web server to download from
WEB_URL = "https://sosig.shop/podcast"

def upload_file_to_gcs(local_path):
    """
    Uploads a file to Google Cloud Storage.
    Returns the GCS path (gs://bucket/path) on success, None on failure.
    """
    
    # Generate timestamp for folder and filename
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    day = now.strftime("%d")
    time_str = now.strftime("%H-%M-%S")
    
    remote_filename = f"{time_str}.mp3"
    
    # Add index if present
    try:
        idx = local_path.split("_")[-1].replace(".mp3", "")
        if idx.isdigit():
            remote_filename = f"{time_str}_{idx}.mp3"
    except:
        pass

    # GCS path structure: podcast/YYYY/MM/DD/HH-MM-SS_idx.mp3
    gcs_path = f"podcast/{year}/{month}/{day}/{remote_filename}"
    
    try:
        # Initialize GCS client (uses default credentials in Cloud Run)
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(gcs_path)
        
        # Upload file
        print(f"[GCS Upload] Uploading to gs://{BUCKET_NAME}/{gcs_path}...")
        blob.upload_from_filename(local_path)
        
        # Make the file publicly readable
        blob.make_public()
        
        print(f"[GCS Upload] ✅ Upload successful!")
        print(f"[GCS Upload] Public URL: {blob.public_url}")
        
        # Return the GCS path for database storage
        # Format: /root/flask-app/static/podcast/YYYY/MM/DD/HH-MM-SS_idx.mp3
        # This matches the old SFTP format for compatibility
        db_path = f"/root/flask-app/static/podcast/{year}/{month}/{day}/{remote_filename}"
        
        return db_path
        
    except Exception as e:
        print(f"[GCS Upload] ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Test upload if run directly
    print("Creating test file...")
    with open("test_audio.mp3", "wb") as f:
        f.write(b"dummy audio content")
    
    result = upload_file_to_gcs("test_audio.mp3")
    print(f"Upload result: {result}")
    
    os.remove("test_audio.mp3")
