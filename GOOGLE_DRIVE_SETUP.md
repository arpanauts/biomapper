# Google Drive Setup Guide for Biomapper

## Prerequisites
You need:
1. ✅ Google Cloud service account JSON file (you have this)
2. ✅ Google Drive folder ID where you want to upload files
3. ✅ Proper permissions on the Drive folder

## Step 1: Set Up Credentials

### Option A: Using .env File (Recommended for Development)

1. **Create or update your .env file**:
```bash
# Copy template if you don't have .env yet
cp /home/ubuntu/biomapper/.env.template /home/ubuntu/biomapper/.env
```

2. **Add Google Drive configuration to .env**:
```bash
# Edit the .env file
nano /home/ubuntu/biomapper/.env

# Add these lines at the end:
# Google Drive Configuration
GOOGLE_APPLICATION_CREDENTIALS=/home/ubuntu/biomapper/google-credentials.json
GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here
GOOGLE_DRIVE_SYNC_ENABLED=true
GOOGLE_DRIVE_CREATE_SUBFOLDER=true
GOOGLE_DRIVE_CONFLICT_RESOLUTION=rename
```

3. **Save your service account JSON file**:
```bash
# Save your downloaded JSON file to the project
cp /path/to/your/downloaded-service-account.json /home/ubuntu/biomapper/google-credentials.json

# Set appropriate permissions (read-only for security)
chmod 400 /home/ubuntu/biomapper/google-credentials.json

# Add to .gitignore to prevent accidental commits
echo "google-credentials.json" >> /home/ubuntu/biomapper/.gitignore
echo ".env" >> /home/ubuntu/biomapper/.gitignore
```

### Option B: Store Credentials as Environment Variable (More Secure)

If you prefer not to have the JSON file on disk, you can store the entire JSON content in an environment variable:

1. **Extract and encode the JSON content**:
```bash
# View your JSON file content
cat /path/to/your/service-account.json

# Copy the entire JSON content
```

2. **Add to .env as a single-line string**:
```bash
# In your .env file, add:
GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"your-project","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n","client_email":"...","client_id":"...","auth_uri":"...","token_uri":"...","auth_provider_x509_cert_url":"...","client_x509_cert_url":"..."}'

# Make sure to escape any quotes in the JSON and keep it on one line
```

### Option C: Using Environment Variables Directly

For production or CI/CD:
```bash
# Export environment variables
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
export GOOGLE_DRIVE_FOLDER_ID=1A2B3C4D5E6F7G8H9I0J
```

## Step 2: Get Your Google Drive Folder ID

1. **Open Google Drive** in your browser
2. **Navigate to the folder** where you want to upload files
3. **Look at the URL**: 
   ```
   https://drive.google.com/drive/folders/1A2B3C4D5E6F7G8H9I0J
                                          ^^^^^^^^^^^^^^^^^^^^^
                                          This is your folder ID
   ```
4. **Copy the folder ID** and add it to your .env file

## Step 3: Grant Permissions to Service Account

1. **Get the service account email** from your JSON file:
```bash
# Extract the client_email from your JSON
grep "client_email" /path/to/your/service-account.json
# Output: "client_email": "your-service-account@project.iam.gserviceaccount.com"
```

2. **Share the Google Drive folder** with the service account:
   - Right-click on your Drive folder
   - Click "Share"
   - Add the service account email
   - Give it "Editor" permissions
   - Click "Send"

## Step 4: Test the Setup

### Quick Test Script
```python
# Create test script
cat > /tmp/test_google_drive.py << 'EOF'
import os
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load environment variables
load_dotenv('/home/ubuntu/biomapper/.env')

def test_google_drive_connection():
    """Test if we can connect to Google Drive."""
    try:
        # Get credentials path from environment
        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
        
        if not creds_path:
            print("❌ GOOGLE_APPLICATION_CREDENTIALS not set in .env")
            return False
            
        if not folder_id:
            print("❌ GOOGLE_DRIVE_FOLDER_ID not set in .env")
            return False
        
        print(f"✓ Credentials path: {creds_path}")
        print(f"✓ Folder ID: {folder_id}")
        
        # Create credentials
        credentials = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        
        # Build service
        service = build('drive', 'v3', credentials=credentials)
        
        # Try to get folder metadata
        folder = service.files().get(fileId=folder_id).execute()
        print(f"✅ Successfully connected! Folder name: {folder.get('name', 'Unknown')}")
        
        # Try to list files in the folder
        results = service.files().list(
            q=f"'{folder_id}' in parents",
            pageSize=5,
            fields="files(id, name)"
        ).execute()
        
        files = results.get('files', [])
        print(f"✓ Found {len(files)} files in the folder")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Google Drive connection...")
    print("=" * 50)
    success = test_google_drive_connection()
    print("=" * 50)
    if success:
        print("✅ Google Drive setup is working!")
    else:
        print("❌ Please check your configuration")
EOF

# Install required packages if needed
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client python-dotenv

# Run the test
python /tmp/test_google_drive.py
```

### Test with Biomapper Action
```python
# Test the actual biomapper action
cat > /tmp/test_biomapper_drive_sync.py << 'EOF'
import asyncio
import os
from dotenv import load_dotenv

# Load environment
load_dotenv('/home/ubuntu/biomapper/.env')

async def test_sync_action():
    """Test the biomapper Google Drive sync action."""
    from biomapper.core.strategy_actions.io.sync_to_google_drive import (
        SyncToGoogleDriveAction,
        SyncToGoogleDriveParams
    )
    
    # Create test file
    test_file = '/tmp/test_upload.txt'
    with open(test_file, 'w') as f:
        f.write("This is a test file from biomapper!")
    
    # Set up parameters
    params = SyncToGoogleDriveParams(
        drive_folder_id=os.environ.get('GOOGLE_DRIVE_FOLDER_ID'),
        input_files=[test_file],
        create_subfolder=True,
        subfolder_name="biomapper_test",
        verbose=True,
        credentials_path=os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    )
    
    # Create action and execute
    action = SyncToGoogleDriveAction()
    result = await action.execute_typed(params, {})
    
    if result.success:
        print(f"✅ Upload successful!")
        print(f"   Uploaded {result.data.get('uploaded_count', 0)} files")
        print(f"   Folder ID: {result.data.get('folder_id', 'N/A')}")
        print(f"   Files: {result.data.get('uploaded_files', [])}")
    else:
        print(f"❌ Upload failed: {result.error}")
    
    return result

if __name__ == "__main__":
    asyncio.run(test_sync_action())
EOF

python /tmp/test_biomapper_drive_sync.py
```

## Step 5: Use in YAML Strategies

Once configured, you can use the sync action in your strategies:

```yaml
# configs/strategies/example_with_drive_sync.yaml
name: ANALYSIS_WITH_DRIVE_BACKUP
description: Run analysis and sync results to Google Drive
parameters:
  data_file: "/path/to/data.csv"
  output_dir: "/tmp/biomapper/results"

steps:
  - name: run_analysis
    action:
      type: METABOLITE_ANALYSIS
      params:
        input_file: "${parameters.data_file}"
        output_dir: "${parameters.output_dir}"
  
  - name: sync_to_drive
    action:
      type: SYNC_TO_GOOGLE_DRIVE
      params:
        drive_folder_id: "${env.GOOGLE_DRIVE_FOLDER_ID}"
        create_subfolder: true
        subfolder_name: "analysis_${env.RUN_ID}"
        sync_context_outputs: true
        verbose: true
```

## Security Best Practices

1. **Never commit credentials**:
   - Always add `.env` and `*.json` credential files to `.gitignore`
   - Use environment variables in CI/CD

2. **Use minimal permissions**:
   - The service account only needs "drive.file" scope
   - Only share specific folders, not entire Drive

3. **Rotate credentials regularly**:
   - Generate new service account keys periodically
   - Remove old keys from Google Cloud Console

4. **Monitor usage**:
   - Check Google Cloud Console for API usage
   - Set up alerts for unusual activity

## Troubleshooting

### Common Issues and Solutions

1. **"File not found" error**:
   - Check that `GOOGLE_APPLICATION_CREDENTIALS` path is absolute
   - Verify the JSON file exists and is readable

2. **"Permission denied" error**:
   - Make sure you shared the Drive folder with the service account email
   - Check that the service account has "Editor" permissions

3. **"Invalid grant" error**:
   - Service account key might be expired or invalid
   - Generate a new key from Google Cloud Console

4. **"Quota exceeded" error**:
   - Google Drive API has usage limits
   - Implement exponential backoff (already in the action)
   - Check quota in Google Cloud Console

## Example .env File

Here's a complete example of what your `.env` file should look like:

```bash
# Biomapper Environment Configuration

# Core directories
BIOMAPPER_DATA_DIR=/procedure/data/local_data
BIOMAPPER_CACHE_DIR=/tmp/biomapper/cache
BIOMAPPER_OUTPUT_DIR=/tmp/biomapper/output
BIOMAPPER_CONFIG_DIR=configs
BIOMAPPER_LOG_DIR=/tmp/biomapper/logs

# External services
QDRANT_HOST=localhost
QDRANT_PORT=6333
CTS_API_BASE=https://cts.fiehnlab.ucdavis.edu/rest
UNIPROT_API_BASE=https://rest.uniprot.org

# Performance settings
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=30
CACHE_TTL_HOURS=24

# Fallback modes
ENABLE_VECTOR_FALLBACK=true
ENABLE_API_FALLBACKS=true
ENABLE_FILE_PATH_FALLBACKS=true

# Validation settings
VALIDATE_FILE_PATHS=true
VALIDATE_PARAMETERS=true
STRICT_VALIDATION=false

# Google Drive Configuration
GOOGLE_APPLICATION_CREDENTIALS=/home/ubuntu/biomapper/google-credentials.json
GOOGLE_DRIVE_FOLDER_ID=1A2B3C4D5E6F7G8H9I0J  # Replace with your folder ID
GOOGLE_DRIVE_SYNC_ENABLED=true
GOOGLE_DRIVE_CREATE_SUBFOLDER=true
GOOGLE_DRIVE_CONFLICT_RESOLUTION=rename
```

## Next Steps

1. ✅ Set up your `.env` file with the credentials
2. ✅ Test the connection with the test script
3. ✅ Run a real biomapper strategy with Drive sync
4. ✅ Monitor uploads in your Google Drive folder

Need help? Check the logs in `/tmp/biomapper/logs/` for detailed error messages.