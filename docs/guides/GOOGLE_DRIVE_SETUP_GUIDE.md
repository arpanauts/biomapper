# 📁 Google Drive Setup Guide for Biomapper

## 🔍 Problem Diagnosis

The Google Drive integration has had chronic issues due to:

1. **Missing .env Loading** ❌ - Pipeline scripts weren't loading the `.env` file
2. **Service Account Limitations** ⚠️ - Service accounts can't create files in their own storage
3. **Folder Permissions** 🔒 - The target folder must be shared with the service account

## ✅ Complete Solution

### Step 1: Environment Setup (FIXED)

The `.env` file at `/home/ubuntu/biomapper/.env` contains:
```bash
GOOGLE_APPLICATION_CREDENTIALS=/home/ubuntu/biomapper/google-credentials.json
GOOGLE_DRIVE_FOLDER_ID=1oQ7CczccH2a6oYYFMo_sf8fXtxF8au_D
ENABLE_GOOGLE_DRIVE_SYNC=true
```

**✅ FIXED**: Pipeline scripts now load `.env` properly with:
```python
from dotenv import load_dotenv
load_dotenv('/home/ubuntu/biomapper/.env')
```

### Step 2: Service Account Configuration

**Service Account**: `biomapper@secret-lambda-468421-g6.iam.gserviceaccount.com`

**Critical Limitation**: Service accounts cannot create files in their own Google Drive storage. They MUST upload to a folder that has been shared with them.

### Step 3: Folder Sharing (REQUIRED)

**You must share your Google Drive folder with the service account:**

1. Go to Google Drive
2. Find the folder with ID: `1oQ7CczccH2a6oYYFMo_sf8fXtxF8au_D`
   - Or create a new folder
3. Right-click → Share
4. Add: `biomapper@secret-lambda-468421-g6.iam.gserviceaccount.com`
5. Set permission: **Editor**
6. Click "Send"

### Step 4: Verify Setup

Run the verification script:
```bash
poetry run python scripts/verify_google_drive_setup.py
```

Expected output:
```
✅ Environment
✅ Credentials  
✅ Authentication
✅ Folder Access    # This requires Step 3
✅ Upload           # This requires Step 3
```

### Step 5: Run Pipeline with Drive Sync

Once folder is shared:
```bash
poetry run python scripts/pipelines/metabolomics_progressive_production.py \
    --dataset arivale \
    --enable-drive-sync
```

## 🎯 What Was Fixed

1. **Added .env loading** to pipeline scripts
2. **Created verification script** to diagnose issues
3. **Identified service account limitation** - must use shared folders
4. **Clear error messages** when Drive sync is misconfigured

## ⚠️ Common Issues

### Issue 1: "Credentials not configured"
**Cause**: .env file not being loaded
**Solution**: ✅ FIXED - Scripts now load .env automatically

### Issue 2: "Service Accounts do not have storage quota"
**Cause**: Trying to create files in service account's own Drive
**Solution**: Share a folder from your personal/organizational Drive with the service account

### Issue 3: "Folder not found (404)"
**Cause**: Folder not shared with service account
**Solution**: Follow Step 3 above to share the folder

## 📊 Current Status

- ✅ **Credentials configured** in .env
- ✅ **Authentication works** 
- ✅ **Pipeline scripts fixed** to load .env
- ❌ **Folder needs sharing** with service account
- ✅ **Complete test script** available

## 🚀 Next Steps

1. **Share the folder** with `biomapper@secret-lambda-468421-g6.iam.gserviceaccount.com`
2. **Run verification** to confirm access
3. **Execute pipeline** with `--enable-drive-sync`
4. **Get shareable links** to uploaded results

Once the folder is shared, the pipeline will automatically:
- Upload all results to Google Drive
- Organize by strategy/version/date
- Generate shareable links
- Provide cloud-based collaboration

## 📝 Technical Details

The SYNC_TO_GOOGLE_DRIVE_V2 action:
1. Checks for credentials in this order:
   - `params.credentials_path` (explicit parameter)
   - `GOOGLE_APPLICATION_CREDENTIALS` env var (from .env)
2. Authenticates with Google Drive API
3. Creates folder structure: `strategy_name/version/timestamp/`
4. Uploads all output files
5. Returns shareable links

The chronic "credentials not configured" issue was simply missing `load_dotenv()` - now fixed!