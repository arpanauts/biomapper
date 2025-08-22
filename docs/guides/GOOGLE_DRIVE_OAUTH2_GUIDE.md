# 🔐 Google Drive OAuth2 Authentication Guide

## Overview

Biomapper now supports **two authentication methods** for Google Drive integration:
1. **OAuth2** - Personal authentication (NEW!)
2. **Service Account** - Automated/programmatic authentication

This guide explains how to set up and use OAuth2 authentication, which solves the service account storage quota limitation.

## 🚨 The Problem We Solved

### Service Account Limitations
- ❌ **Cannot store files** - Service accounts have no storage quota
- ❌ **Must use shared folders** - Can only upload to folders shared with them
- ❌ **Cross-domain issues** - May not see folders from different domains

### OAuth2 Solution
- ✅ **Upload to personal Drive** - Files stored in your account
- ✅ **No quota limitations** - Use your personal storage
- ✅ **Full ownership** - You own and control the files
- ✅ **Easy sharing** - Share with anyone using Drive's native sharing

## 📋 Prerequisites

1. **Google Cloud Project** with Drive API enabled
2. **OAuth2 Client ID** (Desktop application type)
3. **Biomapper installed** with Google dependencies:
   ```bash
   poetry install --with google
   ```

## 🚀 Quick Start

### Step 1: Create OAuth2 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project (or create a new one)
3. Navigate to **APIs & Services** → **Credentials**
4. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
5. Choose **Application type**: Desktop app
6. Name it (e.g., "Biomapper OAuth2")
7. Click **CREATE**
8. Download the JSON file

### Step 2: Run Setup Script

```bash
# Run the OAuth2 setup wizard
poetry run python scripts/setup_oauth2_drive.py
```

The script will:
1. Guide you through credential setup
2. Open a browser for authentication
3. Save your token for future use
4. Test file upload capability

### Step 3: Configure Biomapper

Add to your `.env` file:
```bash
# Use OAuth2 authentication
GOOGLE_AUTH_TYPE=oauth2
GOOGLE_OAUTH_TOKEN_FILE=~/.biomapper/oauth2_token.json

# Optional: Keep service account as fallback
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

### Step 4: Use in Pipeline

```bash
# Run pipeline with OAuth2
poetry run python scripts/pipelines/metabolomics_progressive_production.py \
    --dataset arivale \
    --enable-drive-sync \
    --auth-type oauth2
```

## 🔧 Detailed Configuration

### Authentication Methods

#### Method 1: OAuth2 (Recommended for Interactive Use)
```python
from utils.google_auth_helper import GoogleAuthHelper

# Explicit OAuth2
helper = GoogleAuthHelper(auth_type="oauth2")
service = helper.get_drive_service()
```

**Pros:**
- Upload to personal Drive
- No storage limitations
- Files you own
- Browser-based auth

**Cons:**
- Requires interactive auth (first time)
- Token refresh needed periodically
- Not ideal for CI/CD

#### Method 2: Service Account (For Automation)
```python
# Explicit service account
helper = GoogleAuthHelper(auth_type="service_account")
service = helper.get_drive_service()
```

**Pros:**
- No interaction required
- Perfect for automation
- Consistent service identity

**Cons:**
- Cannot create files
- Must use shared folders
- Complex permissions

#### Method 3: Automatic (Best of Both)
```python
# Auto-detect best method
helper = GoogleAuthHelper(auth_type="auto")
service = helper.get_drive_service()
```

Tries OAuth2 first, falls back to service account.

### File Paths and Storage

OAuth2 configuration files are stored in:
```
~/.biomapper/
├── oauth2_client_secret.json  # OAuth2 client credentials
├── oauth2_token.json          # Saved authentication token
└── drive_config.json          # Drive configuration
```

## 📝 Usage Examples

### Example 1: Simple Upload with OAuth2

```python
from actions.io.sync_to_google_drive_v3 import (
    SyncToGoogleDriveV3Action,
    SyncToGoogleDriveV3Params
)

# Configure for OAuth2
params = SyncToGoogleDriveV3Params(
    drive_folder_id='root',  # Can use root with OAuth2
    auth_type='oauth2',
    auto_organize=True,
    strategy_name='my_analysis',
    strategy_version='1.0.0'
)

# Execute sync
action = SyncToGoogleDriveV3Action()
result = await action.execute_typed(params=params, context=context)
```

### Example 2: Pipeline with OAuth2

```python
# In your pipeline script
import os
os.environ['GOOGLE_AUTH_TYPE'] = 'oauth2'

# Run strategy
client = BiomapperClient()
result = client.run_strategy(
    'metabolomics_progressive_v3',
    enable_drive_sync=True
)
```

### Example 3: Testing Authentication

```bash
# Test OAuth2 setup
poetry run python -m utils.google_auth_helper --auth-type oauth2

# Test with folder access
poetry run python -m utils.google_auth_helper \
    --auth-type oauth2 \
    --folder-id YOUR_FOLDER_ID
```

## 🔄 Migration from Service Account

If you've been using service account authentication:

### Option 1: Complete Migration
1. Set up OAuth2 as shown above
2. Update `.env`:
   ```bash
   GOOGLE_AUTH_TYPE=oauth2
   # Comment out or remove:
   # GOOGLE_APPLICATION_CREDENTIALS=...
   ```
3. All uploads will now use OAuth2

### Option 2: Dual Authentication
1. Set up OAuth2
2. Keep both in `.env`:
   ```bash
   GOOGLE_AUTH_TYPE=auto  # Will try OAuth2 first
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   GOOGLE_OAUTH_TOKEN_FILE=~/.biomapper/oauth2_token.json
   ```
3. System will use best available method

## 🐛 Troubleshooting

### Issue: "OAuth2 client secret not found"
**Solution:** Download credentials from Google Cloud Console and save to:
```
~/.biomapper/oauth2_client_secret.json
```

### Issue: "Token expired"
**Solution:** Delete token and re-authenticate:
```bash
rm ~/.biomapper/oauth2_token.json
poetry run python scripts/setup_oauth2_drive.py
```

### Issue: "Access blocked: This app is blocked"
**Solution:** In Google Cloud Console:
1. Go to OAuth consent screen
2. Add your email as a test user
3. Or publish the app (requires review)

### Issue: "Redirect URI mismatch"
**Solution:** Ensure OAuth2 client is "Desktop" type, not "Web application"

## 🔒 Security Considerations

### Token Storage
- OAuth2 tokens are stored locally in `~/.biomapper/`
- Tokens are user-specific, don't commit to git
- Add to `.gitignore`:
  ```
  .biomapper/
  oauth2_token.json
  ```

### Token Refresh
- Tokens auto-refresh when possible
- Manual refresh may be needed after extended periods
- Run setup script again if auth fails

### Scopes
- Default scope: `drive.file` (only files created by app)
- For full access, modify scopes in auth helper:
  ```python
  SCOPES = ['https://www.googleapis.com/auth/drive']
  ```

## 📊 Comparison Table

| Feature | OAuth2 | Service Account |
|---------|--------|-----------------|
| Storage Location | Personal Drive | Shared folders only |
| Storage Quota | Your quota | None (cannot store) |
| Interactive Auth | Yes (first time) | No |
| CI/CD Friendly | No | Yes |
| File Ownership | You | Service account |
| Sharing | Native Drive sharing | Complex permissions |
| Best For | Interactive, personal | Automation, CI/CD |

## 🎯 Best Practices

1. **Development**: Use OAuth2 for testing and development
2. **Production**: Use service account with shared folders
3. **Hybrid**: Use `auth_type="auto"` for flexibility
4. **Security**: Never commit tokens or credentials
5. **Backup**: Keep both auth methods configured

## 🚦 Implementation Status

✅ **Completed:**
- OAuth2 setup script (`scripts/setup_oauth2_drive.py`)
- Authentication helper (`src/utils/google_auth_helper.py`)
- Updated sync action (`src/actions/io/sync_to_google_drive_v3.py`)
- Demo script (`demo_oauth2_drive_sync.py`)
- Comprehensive documentation

⏳ **Next Steps:**
- Test with real metabolomics pipeline
- Add OAuth2 support to CLI
- Create GitHub Action for CI/CD with service account

## 📚 Additional Resources

- [Google Drive API Documentation](https://developers.google.com/drive/api/v3/about-sdk)
- [OAuth2 for Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Service Account Documentation](https://cloud.google.com/iam/docs/service-accounts)
- [Biomapper Documentation](../README.md)

## 💡 Tips and Tricks

### Tip 1: Check Available Auth Methods
```python
from utils.google_auth_helper import GoogleAuthHelper
methods = GoogleAuthHelper.get_available_auth_methods()
print(f"Available: {methods}")  # ['oauth2', 'service_account']
```

### Tip 2: Force Re-authentication
```bash
# Clear OAuth2 token
rm ~/.biomapper/oauth2_token.json

# Clear all auth
rm -rf ~/.biomapper/
```

### Tip 3: Use Different Accounts
```python
# Specify custom token location
helper = GoogleAuthHelper(
    auth_type="oauth2",
    oauth2_token_path="/path/to/custom/token.json"
)
```

### Tip 4: Debugging Auth Issues
```bash
# Verbose mode
GOOGLE_AUTH_DEBUG=true poetry run python your_script.py

# Check current auth
poetry run python -c "
from utils.google_auth_helper import GoogleAuthHelper
h = GoogleAuthHelper()
print(h.test_access())
"
```

## 🎉 Success!

You now have OAuth2 authentication working with biomapper! This solves the chronic Google Drive integration issues by:

1. ✅ Allowing uploads to personal Drive
2. ✅ Eliminating storage quota errors
3. ✅ Providing flexible authentication options
4. ✅ Supporting both interactive and automated workflows

For questions or issues, please check the [troubleshooting](#-troubleshooting) section or open an issue on GitHub.