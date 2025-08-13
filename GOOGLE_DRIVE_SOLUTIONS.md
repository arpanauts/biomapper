# Google Drive Upload Solutions

## The Problem
Service accounts cannot upload files to personal Google Drive folders due to storage quota limitations. You have three options:

## Option 1: Use a Shared Drive (Recommended for Teams)
If you have Google Workspace:
1. Create a Shared Drive
2. Add the service account as a member
3. Update GOOGLE_DRIVE_FOLDER_ID to the Shared Drive folder ID

## Option 2: Use OAuth 2.0 (Recommended for Personal Use)
Instead of a service account, use OAuth authentication:

```python
# Modified authentication for OAuth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def authenticate_oauth():
    creds = None
    token_file = 'token.json'
    
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Download credentials from Google Cloud Console as "OAuth 2.0 Client ID"
            flow = InstalledAppFlow.from_client_secrets_file(
                'oauth_credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    
    return build('drive', 'v3', credentials=creds)
```

## Option 3: Domain-Wide Delegation (For Google Workspace)
Configure the service account to impersonate a user:

```python
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    'google-credentials.json',
    scopes=['https://www.googleapis.com/auth/drive.file'],
    subject='your-email@domain.com'  # Impersonate this user
)
```

## Quick Workaround: Local File Export
For now, we can modify the strategy to export files locally and manually upload:

```yaml
# In your strategy YAML
steps:
  - name: export_results
    action:
      type: EXPORT_DATASET
      params:
        output_file: "${parameters.output_dir}/results_${timestamp}.csv"
        
  # Google Drive sync will log the attempt but files stay local
  - name: attempt_sync
    action:
      type: SYNC_TO_GOOGLE_DRIVE
      params:
        drive_folder_id: "${GOOGLE_DRIVE_FOLDER_ID}"
```

## What's Working Now
✅ Authentication is successful
✅ Google Drive API is enabled
✅ Folder permissions are correct
✅ The sync action executes properly

## What's Needed
The limitation is that service accounts can't store files in personal Drive folders. You need one of the solutions above.

## For Testing/Development
The files are being created locally in `/tmp/biomapper/gdrive_test/`. You can:
1. Check the files are created correctly
2. Manually upload them to verify the data pipeline works
3. Implement one of the solutions above for production