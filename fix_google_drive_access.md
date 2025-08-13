# Fix Google Drive Access for Service Account

## The Issue
The service account can authenticate but gets "File not found" error for your folder ID. This means the service account doesn't have permission to access the folder.

## Solution

### Step 1: Get the Service Account Email
Look in your `google-credentials.json` file for the `client_email` field. It will look like:
```
"client_email": "biomapper-sync@your-project.iam.gserviceaccount.com"
```

### Step 2: Share the Folder with Service Account
1. Go to your Google Drive folder: https://drive.google.com/drive/folders/1tGkQps5DwaYn761J5DD-BNbETuGkLTeZ
2. Click the "Share" button (or right-click → Share)
3. Add the service account email (from Step 1)
4. Give it "Editor" permissions
5. Click "Send" (the service account won't actually receive an email, but will get access)

### Step 3: Verify Folder ID
Make sure the folder ID in your .env matches the one in the URL:
- URL: `https://drive.google.com/drive/folders/[FOLDER_ID]`
- Your folder ID: `1tGkQps5DwaYn761J5DD-BNbETuGkLTeZ`

### Step 4: Test Again
Once you've shared the folder, run the test again:
```bash
poetry run python test_google_drive_sync.py
```

## Alternative: Create a New Folder
If you prefer, the service account can create its own folder:

```python
# Modify the sync action to create a root folder
# This would require modifying the action to support root folder creation
```

## Expected Success Output
When it works, you should see:
- Files actually uploaded
- URLs returned for each file
- Files visible in your Google Drive folder