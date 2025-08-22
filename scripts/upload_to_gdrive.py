#!/usr/bin/env python3
"""
Direct Google Drive upload script for protein mapping results.
Bypasses action signature issues with direct API usage.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
except ImportError:
    print("❌ Google API client not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", 
                          "google-api-python-client", "google-auth"])
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError


def upload_to_google_drive(local_dir: str, folder_id: str = "1oQ7CczccH2a6oYYFMo_sf8fXtxF8au_D"):
    """
    Direct upload to Google Drive bypassing action signature issues.
    
    Args:
        local_dir: Local directory containing files to upload
        folder_id: Google Drive folder ID
    
    Returns:
        List of uploaded file information
    """
    
    print("📤 Google Drive Upload Script")
    print("=" * 50)
    print(f"Local directory: {local_dir}")
    print(f"Target folder ID: {folder_id}")
    print()
    
    # Check credentials
    creds_file = '/home/ubuntu/biomapper/google-credentials.json'
    if not Path(creds_file).exists():
        print(f"❌ Credentials not found: {creds_file}")
        return []
    
    try:
        # Authenticate
        print("🔐 Authenticating with Google Drive...")
        credentials = service_account.Credentials.from_service_account_file(
            creds_file,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        
        service = build('drive', 'v3', credentials=credentials)
        
        # Create timestamped folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"protein_mapping_99_percent_{timestamp}"
        
        print(f"📁 Creating folder: {folder_name}")
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [folder_id]
        }
        
        try:
            folder = service.files().create(
                body=folder_metadata, 
                fields='id,name,webViewLink'
            ).execute()
            new_folder_id = folder.get('id')
            folder_url = folder.get('webViewLink', 'N/A')
            print(f"✅ Created folder: {folder_url}")
        except HttpError as e:
            print(f"❌ Failed to create folder: {e}")
            return []
        
        # Priority files to upload
        priority_files = [
            "all_mappings_v3.0_CLEAN.tsv",
            "mapping_statistics_CLEAN.json",
            "validation_report.json",
            "coverage_summary.tsv",
            "99_percent_coverage_achievement.md",
            "technical_summary.json"
        ]
        
        # Add any existing visualization files
        local_path = Path(local_dir)
        for pattern in ["*.svg", "*.png", "*.pdf"]:
            priority_files.extend([f.name for f in local_path.glob(pattern)])
        
        # Remove duplicates while preserving order
        priority_files = list(dict.fromkeys(priority_files))
        
        uploaded = []
        failed = []
        
        print(f"\n📤 Uploading {len(priority_files)} files...")
        
        for filename in priority_files:
            filepath = local_path / filename
            
            if not filepath.exists():
                print(f"   ⏭️ Skipping (not found): {filename}")
                continue
            
            # Check file size
            file_size = filepath.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            
            # Skip very large files (>100MB) unless they're the main data file
            if file_size_mb > 100 and 'CLEAN.tsv' not in filename:
                print(f"   ⏭️ Skipping (too large): {filename} ({file_size_mb:.1f}MB)")
                continue
            
            print(f"   📤 Uploading: {filename} ({file_size_mb:.1f}MB)...")
            
            try:
                file_metadata = {
                    'name': filename,
                    'parents': [new_folder_id]
                }
                
                # Determine MIME type
                mime_type = 'application/octet-stream'
                if filename.endswith('.tsv'):
                    mime_type = 'text/tab-separated-values'
                elif filename.endswith('.json'):
                    mime_type = 'application/json'
                elif filename.endswith('.md'):
                    mime_type = 'text/markdown'
                elif filename.endswith('.svg'):
                    mime_type = 'image/svg+xml'
                elif filename.endswith('.png'):
                    mime_type = 'image/png'
                
                # Use resumable upload for large files
                media = MediaFileUpload(
                    str(filepath),
                    mimetype=mime_type,
                    resumable=file_size_mb > 5
                )
                
                file = service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id,name,webViewLink,size'
                ).execute()
                
                uploaded.append({
                    'name': filename,
                    'id': file.get('id'),
                    'url': file.get('webViewLink'),
                    'size_mb': file_size_mb
                })
                
                print(f"      ✅ Uploaded successfully")
                
            except HttpError as e:
                error_msg = str(e)
                if '403' in error_msg:
                    print(f"      ❌ Permission denied - check folder access")
                elif '404' in error_msg:
                    print(f"      ❌ Folder not found - check folder ID")
                else:
                    print(f"      ❌ Upload failed: {error_msg[:100]}")
                failed.append(filename)
            except Exception as e:
                print(f"      ❌ Unexpected error: {str(e)[:100]}")
                failed.append(filename)
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Upload Summary")
        print(f"   ✅ Successfully uploaded: {len(uploaded)} files")
        if failed:
            print(f"   ❌ Failed uploads: {len(failed)} files")
            for f in failed:
                print(f"      - {f}")
        
        if uploaded:
            print(f"\n📁 Google Drive Folder: {folder_url}")
            print("\n📎 Uploaded Files:")
            for file_info in uploaded[:10]:  # Show first 10
                print(f"   - {file_info['name']} ({file_info['size_mb']:.1f}MB)")
                print(f"     {file_info['url']}")
            
            if len(uploaded) > 10:
                print(f"   ... and {len(uploaded) - 10} more files")
        
        # Save upload manifest
        manifest = {
            'timestamp': datetime.now().isoformat(),
            'folder_id': new_folder_id,
            'folder_name': folder_name,
            'folder_url': folder_url,
            'uploaded_files': uploaded,
            'failed_files': failed,
            'total_size_mb': sum(f['size_mb'] for f in uploaded)
        }
        
        manifest_file = local_path / "gdrive_upload_manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        print(f"\n💾 Upload manifest saved: {manifest_file}")
        
        return uploaded
        
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        import traceback
        traceback.print_exc()
        return []


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Upload protein mapping results to Google Drive'
    )
    parser.add_argument(
        '--local',
        default='/tmp/biomapper/protein_mapping_CLEAN',
        help='Local directory containing files to upload'
    )
    parser.add_argument(
        '--folder',
        default='1oQ7CczccH2a6oYYFMo_sf8fXtxF8au_D',
        help='Google Drive folder ID'
    )
    
    args = parser.parse_args()
    
    # Run upload
    uploaded = upload_to_google_drive(args.local, args.folder)
    
    if uploaded:
        print(f"\n✅ Successfully uploaded {len(uploaded)} files to Google Drive!")
        sys.exit(0)
    else:
        print("\n❌ No files were uploaded")
        sys.exit(1)


if __name__ == "__main__":
    main()