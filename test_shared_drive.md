# Creating a Shared Drive for Biomapper

## Check if You Can Create a Shared Drive

1. Go to Google Drive: https://drive.google.com
2. Look in the left sidebar for "Shared drives"
3. If you see it, click on it and then click "New" or "+" to create one

## If "Shared drives" is Available:

### Create the Shared Drive
1. Click "New" or "+" in Shared drives
2. Name it something like "Biomapper Output"
3. Click "Create"

### Add Service Account
1. Right-click on the new Shared Drive
2. Click "Manage members" or "Share"
3. Add: `biomapper@secret-lambda-468421-g6.iam.gserviceaccount.com`
4. Set role to "Content Manager" or "Manager"
5. Click "Send"

### Get the Folder ID
1. Click into the Shared Drive
2. The URL will be like: `https://drive.google.com/drive/folders/[NEW_FOLDER_ID]`
3. Copy that folder ID

### Update Your .env
```bash
GOOGLE_DRIVE_FOLDER_ID=your_new_shared_drive_folder_id
```

### Test Again
```bash
poetry run python test_google_drive_sync.py
```

## If "Shared drives" is NOT Available:

This means you have a personal Google account, not Workspace. Shared Drives require:
- Google Workspace Business Starter or higher
- Google Workspace for Education
- Or a legacy G Suite account

For personal accounts, your options are:
1. Use OAuth authentication instead of service account
2. Save files locally and manually upload
3. Use a different cloud storage service (Dropbox, S3, etc.)

## Quick Check
Try this link: https://drive.google.com/drive/shared-drives

If it shows "Shared drives" or lets you create one, you're good to go!
If it redirects or shows an error, you'll need one of the alternative solutions.