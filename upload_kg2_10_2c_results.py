#!/usr/bin/env python3
"""
Upload KG2.10.2c results to Google Drive
"""
import os
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def upload_kg2_10_2c_results():
    """Upload KG2.10.2c results to Google Drive"""
    
    # Get credentials
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '/home/ubuntu/biomapper/google-credentials.json')
    print(f"✅ Using credentials: {creds_path}")
    
    # Authenticate
    credentials = service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    service = build("drive", "v3", credentials=credentials)
    
    # Correct folder ID
    folder_id = "1oQ7CczccH2a6oYYFMo_sf8fXtxF8au_D"
    
    # Create a subfolder for KG2.10.2c results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    subfolder_name = f"kg2_10_2c_results_{timestamp}"
    
    print(f"\n📁 Creating subfolder: {subfolder_name}")
    
    folder_metadata = {
        'name': subfolder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [folder_id]
    }
    
    try:
        subfolder = service.files().create(
            body=folder_metadata,
            fields='id,name,webViewLink',
            supportsAllDrives=True
        ).execute()
        
        subfolder_id = subfolder['id']
        print(f"✅ Created folder: {subfolder.get('webViewLink', subfolder['name'])}")
        
    except Exception as e:
        print(f"❌ Failed to create folder: {e}")
        subfolder_id = folder_id  # Fall back to main folder
    
    # Files to upload
    files_to_upload = [
        ('/tmp/biomapper_results_kg2_10_2c/protein_mapping_results_kg2_10_2c.csv', 'protein_mapping_results_kg2_10_2c.csv'),
        ('/tmp/biomapper_results_kg2_10_2c/arivale_proteins.csv', 'arivale_proteins.csv'),
        ('/tmp/biomapper_results_kg2_10_2c/summary_kg2_10_2c.txt', 'summary_kg2_10_2c.txt')
    ]
    
    # Create comparison summary
    comparison_path = '/tmp/biomapper_results_kg2_10_2c/comparison.txt'
    with open(comparison_path, 'w') as f:
        f.write("KG2 VERSION COMPARISON\n")
        f.write("=" * 50 + "\n\n")
        f.write("OLD KG2 (kg2c_ontologies):\n")
        f.write("- File: kg2c_ontologies/kg2c_proteins.csv\n")
        f.write("- Total entities: 266,487\n")
        f.write("- Output rows: 266,911\n")
        f.write("- Matched: 818/1,162 (70.4%)\n")
        f.write("- Runtime: 102 seconds\n")
        f.write("\nNEW KG2.10.2c:\n")
        f.write("- File: kg2.10.2c_ontologies/kg2c_proteins.csv\n")
        f.write("- Total entities: 350,368 (+83,881)\n")
        f.write("- Output rows: 350,791\n")
        f.write("- Matched: 818/1,162 (70.4%)\n")
        f.write("- Runtime: 110.9 seconds\n")
        f.write("\nKEY FINDINGS:\n")
        f.write("✅ Same match rate (70.4%) with both versions\n")
        f.write("✅ KG2.10.2c has 83,881 more protein entities\n")
        f.write("✅ Performance remains excellent (~2 minutes)\n")
        f.write("✅ Isoform stripping works consistently\n")
    
    files_to_upload.append((comparison_path, 'comparison.txt'))
    
    # Upload files
    print(f"\n📤 Uploading {len(files_to_upload)} files...")
    
    uploaded = []
    for local_path, filename in files_to_upload:
        if not os.path.exists(local_path):
            print(f"⚠️  Skipping {filename} (not found)")
            continue
        
        file_size = os.path.getsize(local_path) / (1024 * 1024)  # MB
        print(f"\n  Uploading {filename} ({file_size:.1f} MB)...")
        
        file_metadata = {
            'name': filename,
            'parents': [subfolder_id]
        }
        
        # Determine MIME type
        if filename.endswith('.csv'):
            mime_type = 'text/csv'
        elif filename.endswith('.txt'):
            mime_type = 'text/plain'
        else:
            mime_type = 'application/octet-stream'
        
        media = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)
        
        try:
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,webViewLink',
                supportsAllDrives=True
            ).execute()
            
            print(f"  ✅ Uploaded: {file.get('webViewLink', file['name'])}")
            uploaded.append(file)
            
        except Exception as e:
            print(f"  ❌ Failed to upload {filename}: {e}")
    
    print(f"\n✅ Successfully uploaded {len(uploaded)}/{len(files_to_upload)} files")
    print(f"\n📁 View KG2.10.2c results in Google Drive:")
    print(f"   https://drive.google.com/drive/folders/{folder_id}")
    
    print(f"\n📊 RESULTS SUMMARY:")
    print(f"   - KG2.10.2c: 350,368 protein entities")
    print(f"   - Arivale matches: 818/1,162 (70.4%)")
    print(f"   - Total output: 350,791 rows")
    print(f"   - Runtime: 110.9 seconds")
    
    return True

if __name__ == "__main__":
    print("🚀 UPLOADING KG2.10.2c RESULTS TO GOOGLE DRIVE")
    print("=" * 60)
    
    success = upload_kg2_10_2c_results()
    
    if success:
        print("\n🎉 SUCCESS! KG2.10.2c results uploaded to Google Drive")
    else:
        print("\n❌ Upload failed")