Google Drive Integration
========================

Overview
--------

Biomapper supports seamless integration with Google Drive for storing and sharing analysis results. This integration offers two authentication methods to suit different use cases: OAuth2 for personal use and Service Accounts for automated workflows.

The Google Drive integration solves the common problem of sharing large biological datasets and analysis results with collaborators, while providing organized folder structures and automatic uploads.

Authentication Methods
-----------------------

OAuth2 Authentication (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

OAuth2 authentication allows biomapper to upload files directly to your personal Google Drive, using your own storage quota and permissions.

**Benefits:**
  - ✅ Upload to personal Drive storage
  - ✅ No storage quota limitations (uses your personal allocation)
  - ✅ Full ownership and control of uploaded files
  - ✅ Easy sharing using Drive's native sharing features
  - ✅ No cross-domain permission issues

**Best for:** Personal research, individual analysis, small teams

Service Account Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Service Account authentication provides programmatic access without user interaction, ideal for automated pipelines and server deployments.

**Benefits:**
  - ✅ Automated access without user intervention
  - ✅ Suitable for server-side automation
  - ✅ Can be shared across team members
  - ✅ Consistent API access

**Limitations:**
  - ❌ Cannot store files directly (no storage quota)
  - ❌ Must upload to folders shared with the service account
  - ❌ More complex permission management

**Best for:** Automated pipelines, continuous integration, enterprise deployments

Setup Instructions
------------------

OAuth2 Setup (Personal Use)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Step 1: Create Google Cloud Project
""""""""""""""""""""""""""""""""""""

1. Go to `Google Cloud Console <https://console.cloud.google.com>`_
2. Create a new project or select existing one
3. Enable the Google Drive API:
   
   - Navigate to **APIs & Services** → **Library**
   - Search for "Google Drive API"
   - Click **Enable**

Step 2: Create OAuth2 Credentials
""""""""""""""""""""""""""""""""""

1. Navigate to **APIs & Services** → **Credentials**
2. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
3. Configure the consent screen (if prompted):
   
   - User Type: **External** (for personal use)
   - App name: "Biomapper Integration"
   - User support email: Your email
   - Developer contact: Your email

4. Create OAuth client ID:
   
   - Application type: **Desktop app**
   - Name: "Biomapper OAuth2"
   - Click **CREATE**

5. Download the credentials JSON file
6. Save it securely (never commit to version control)

Step 3: Run Biomapper OAuth2 Setup
"""""""""""""""""""""""""""""""""""

.. code-block:: bash

   # Ensure dependencies are installed (Google dependencies included in main install)
   poetry install --with dev,docs,api
   
   # Run the OAuth2 setup wizard
   poetry run python scripts/setup_oauth2_drive.py
   
   # Follow the interactive prompts:
   # 1. Provide path to OAuth2 credentials JSON
   # 2. Complete browser authorization flow
   # 3. Verify upload permissions

Step 4: Test the Setup
"""""""""""""""""""""""

.. code-block:: bash

   # Verify Google Drive integration
   poetry run python scripts/verify_google_drive_setup.py
   
   # Expected output:
   # ✅ OAuth2 credentials found
   # ✅ Google Drive API accessible
   # ✅ Test file upload successful
   # ✅ Setup complete!

Service Account Setup (Automation)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Step 1: Create Service Account
"""""""""""""""""""""""""""""""

1. Go to `Google Cloud Console <https://console.cloud.google.com>`_
2. Navigate to **IAM & Admin** → **Service Accounts**
3. Click **+ CREATE SERVICE ACCOUNT**
4. Configure:
   
   - Service account name: "biomapper-drive-integration"
   - Service account ID: Auto-generated
   - Description: "Service account for biomapper Google Drive uploads"

5. Grant roles (optional): **Editor** or **Storage Admin**
6. Click **CREATE AND CONTINUE**

Step 2: Generate Credentials
"""""""""""""""""""""""""""""

1. Find your service account in the list
2. Click **Actions** (⋮) → **Manage keys**
3. Click **ADD KEY** → **Create new key**
4. Select **JSON** format
5. Click **CREATE**
6. Download and securely store the JSON file

Step 3: Configure Environment
""""""""""""""""""""""""""""""

.. code-block:: bash

   # Set environment variable for service account
   export GOOGLE_SERVICE_ACCOUNT_PATH="/path/to/service-account-key.json"
   
   # Or add to your .bashrc/.zshrc for persistence
   echo 'export GOOGLE_SERVICE_ACCOUNT_PATH="/path/to/service-account-key.json"' >> ~/.bashrc

Step 4: Create Shared Folder
"""""""""""""""""""""""""""""

1. In Google Drive, create a folder for biomapper results
2. Right-click the folder → **Share**
3. Add the service account email as **Editor**
   
   - Service account email format: ``service-account-name@project-id.iam.gserviceaccount.com``
   - Find the email in the downloaded JSON file under ``client_email``

4. Note the folder ID from the URL for configuration

Usage Examples
--------------

Basic Upload with OAuth2
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from client.client_v2 import BiomapperClient

   client = BiomapperClient(base_url="http://localhost:8000")
   
   # Simple file upload using OAuth2
   result = await client.run_action(
       action_type="SYNC_TO_GOOGLE_DRIVE_V3",
       params={
           "input_key": "analysis_results",
           "output_key": "drive_metadata", 
           "file_path": "/results/metabolomics_analysis.csv",
           "drive_folder_id": "your_folder_id_here",
           "auth_type": "oauth2"
       },
       context={"datasets": {"analysis_results": results_df}}
   )
   
   print(f"File uploaded: {result.context['datasets']['drive_metadata']['drive_url']}")

Complete Pipeline with Drive Upload
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   name: "metabolomics_with_drive_backup"
   description: "Complete metabolomics pipeline with automatic Google Drive backup"
   
   parameters:
     input_file: "/data/metabolites.csv"
     project_name: "arivale_analysis_2025"
     
   steps:
     # Data processing pipeline
     - name: load_metabolites
       action:
         type: LOAD_DATASET_IDENTIFIERS
         params:
           file_path: "${parameters.input_file}"
           identifier_column: "metabolite_name"
           output_key: "raw_metabolites"
           
     - name: progressive_matching
       action:
         type: PROGRESSIVE_SEMANTIC_MATCH
         params:
           input_key: "raw_metabolites"
           output_key: "matched_metabolites"
           identifier_column: "metabolite_name"
           
     # Results export and upload
     - name: export_results
       action:
         type: EXPORT_DATASET
         params:
           input_key: "matched_metabolites"
           file_path: "/tmp/${parameters.project_name}_results.csv"
           
     - name: upload_to_drive
       action:
         type: SYNC_TO_GOOGLE_DRIVE_V3
         params:
           input_key: "matched_metabolites"
           output_key: "drive_upload_status"
           file_path: "/tmp/${parameters.project_name}_results.csv"
           drive_folder_id: "your_folder_id_here"
           auth_type: "oauth2"
           
     - name: generate_summary_report
       action:
         type: GENERATE_LLM_ANALYSIS
         params:
           input_key: "matched_metabolites"
           output_key: "analysis_report"
           report_type: "coverage_summary"
           
     - name: upload_report
       action:
         type: SYNC_TO_GOOGLE_DRIVE_V3
         params:
           input_key: "analysis_report"
           output_key: "report_upload_status"
           file_path: "/tmp/${parameters.project_name}_report.md"
           drive_folder_id: "your_folder_id_here"
           auth_type: "oauth2"

Batch Upload Multiple Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def upload_analysis_batch():
       client = BiomapperClient(base_url="http://localhost:8000")
       
       files_to_upload = [
           {"path": "/results/metabolites.csv", "name": "metabolite_results"},
           {"path": "/results/proteins.csv", "name": "protein_results"},
           {"path": "/results/summary.json", "name": "analysis_summary"}
       ]
       
       upload_results = []
       
       for file_info in files_to_upload:
           result = await client.run_action(
               action_type="SYNC_TO_GOOGLE_DRIVE_V3",
               params={
                   "input_key": "dummy",  # Not used for file uploads
                   "output_key": f"upload_{file_info['name']}",
                   "file_path": file_info["path"],
                   "drive_folder_id": "your_folder_id_here",
                   "auth_type": "oauth2"
               },
               context={"datasets": {"dummy": {}}}
           )
           
           upload_results.append(result)
       
       return upload_results

Folder Organization
-------------------

Automatic Folder Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Biomapper automatically creates organized folder structures in Google Drive:

::

   Biomapper Results/
   ├── metabolomics_pipeline_v3/
   │   ├── 2025-08-22_14-30-15/
   │   │   ├── metabolite_mapping_results.csv
   │   │   ├── coverage_statistics.json
   │   │   ├── unmatched_metabolites.csv
   │   │   └── analysis_summary.md
   │   ├── 2025-08-21_09-15-42/
   │   └── latest/  # Always points to most recent run
   ├── protein_harmonization/
   │   ├── 2025-08-22_15-45-30/
   │   └── latest/
   └── shared/
       ├── reference_data/
       └── templates/

Custom Folder Organization
~~~~~~~~~~~~~~~~~~~~~~~~~~

You can customize the folder structure:

.. code-block:: yaml

   # Custom folder hierarchy using folder ID
   drive_folder_id: "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
   auto_organize: true
   folder_prefix: "progressive_matching"
   
   # Results in organized folder structure within the specified folder

Sharing and Permissions
~~~~~~~~~~~~~~~~~~~~~~~

**OAuth2 Files:**
- Uploaded to your personal Drive
- You own the files and control sharing
- Use Drive's native sharing (right-click → Share)
- Can set view/edit/comment permissions

**Service Account Files:**
- Uploaded to shared folders
- Folder owner controls overall access
- Files inherit folder permissions
- Can be accessed by all folder collaborators

Advanced Configuration
----------------------

Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~

For large files and datasets:

.. code-block:: yaml

   # Optimize upload performance
   params:
     chunk_size: 10485760  # 10MB chunks
     timeout: 300          # 5 minute timeout
     retry_attempts: 3     # Retry failed uploads
     compression: true     # Compress before upload

Error Handling and Monitoring
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   # Robust error handling
   params:
     on_error: "continue"           # Don't fail pipeline on upload error
     backup_local: true             # Keep local copy as backup
     verify_upload: true            # Verify file integrity after upload
     notification_email: "user@domain.com"  # Email on upload completion

Authentication Management
~~~~~~~~~~~~~~~~~~~~~~~~~

Environment Configuration
""""""""""""""""""""""""""

.. code-block:: bash

   # OAuth2 configuration
   export GOOGLE_OAUTH2_CREDENTIALS_PATH="/secure/path/to/oauth2_credentials.json"
   export GOOGLE_OAUTH2_TOKEN_PATH="/secure/path/to/token.json"
   
   # Service Account configuration  
   export GOOGLE_SERVICE_ACCOUNT_PATH="/secure/path/to/service_account.json"
   export GOOGLE_DRIVE_FOLDER_ID="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"

Token Management
""""""""""""""""

.. code-block:: python

   # Check OAuth2 token status
   from utils.google_auth_helper import GoogleAuthHelper
   
   auth_helper = GoogleAuthHelper()
   
   if auth_helper.token_expired():
       print("Token expired, refreshing...")
       auth_helper.refresh_token()
   else:
       print("Token valid")

Troubleshooting
---------------

Common Issues and Solutions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 40 60
   :header-rows: 1

   * - Problem
     - Solution
   * - "Authentication failed" error
     - Re-run OAuth2 setup or check service account credentials
   * - "Insufficient permissions" error
     - Verify folder sharing with service account email
   * - Upload timeouts
     - Reduce chunk size or increase timeout values
   * - "Quota exceeded" error
     - Wait for quota reset (24 hours) or reduce upload frequency
   * - Files not appearing in Drive
     - Check folder permissions and refresh Drive view
   * - Upload seems slow
     - Verify network connection and try smaller chunk sizes

Debugging Tools
~~~~~~~~~~~~~~~

.. code-block:: bash

   # Test OAuth2 authentication
   poetry run python -c "
   from utils.google_auth_helper import GoogleAuthHelper
   auth = GoogleAuthHelper()
   print('OAuth2 status:', auth.check_oauth2_status())
   "
   
   # Test service account access
   poetry run python -c "
   from utils.google_auth_helper import GoogleAuthHelper  
   auth = GoogleAuthHelper()
   print('Service account status:', auth.check_service_account_status())
   "
   
   # List accessible Drive folders
   poetry run python scripts/list_drive_folders.py

Performance Considerations
--------------------------

Upload Speed Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~

Typical performance metrics:

.. list-table::
   :widths: 25 25 25 25
   :header-rows: 1

   * - File Size
     - Upload Time (OAuth2)
     - Upload Time (Service Account)
     - Recommended Chunk Size
   * - < 10MB
     - 2-5 seconds
     - 2-5 seconds  
     - Default (5MB)
   * - 10-100MB
     - 10-30 seconds
     - 10-30 seconds
     - 10MB
   * - 100MB-1GB
     - 1-5 minutes
     - 1-5 minutes
     - 25MB
   * - > 1GB
     - 5-20 minutes
     - 5-20 minutes
     - 50MB

Network and API Limits
~~~~~~~~~~~~~~~~~~~~~~

- **Google Drive API Quota**: 1,000 requests per 100 seconds per user
- **Upload Limits**: 5TB per day per user
- **File Size Limits**: 5TB per file maximum
- **Concurrent Uploads**: Recommend max 3-5 simultaneous uploads

Best Practices
--------------

Security and Privacy
~~~~~~~~~~~~~~~~~~~~

1. **Credential Protection**
   
   - Never commit OAuth2 or service account credentials to version control
   - Store credentials in secure, encrypted locations
   - Use environment variables for credential paths
   - Regularly rotate service account keys

2. **Access Control**
   
   - Use principle of least privilege for folder sharing
   - Regularly audit who has access to shared folders
   - Consider using organization-managed shared drives

3. **Data Sensitivity**
   
   - Be aware of data privacy regulations (GDPR, HIPAA, etc.)
   - Consider encryption for sensitive biological data
   - Document data handling and retention policies

Operational Guidelines
~~~~~~~~~~~~~~~~~~~~~~

1. **Monitoring**
   
   - Track upload success rates and performance
   - Monitor Google Drive API quota usage
   - Set up alerts for upload failures

2. **Maintenance**
   
   - Regularly clean up old result files
   - Archive completed analyses
   - Update credentials before expiration

3. **Documentation**
   
   - Document folder organization conventions
   - Maintain sharing permission records
   - Record credential renewal procedures

See Also
--------

- :doc:`../actions/sync_to_google_drive` - Google Drive action reference
- :doc:`../examples/advanced_pipelines` - Pipeline integration examples
- :doc:`../workflows/metabolomics_pipeline` - Complete workflow with uploads

---

## Verification Sources
*Last verified: August 22, 2025*

This documentation was verified against the following project resources:

- `/biomapper/src/actions/io/sync_to_google_drive_v3.py` (Google Drive sync action implementation with OAuth2 and Service Account support)
- `/biomapper/src/utils/google_auth_helper.py` (Authentication helper class supporting both OAuth2 and Service Account methods)
- `/biomapper/scripts/setup_oauth2_drive.py` (OAuth2 setup wizard script for interactive credential configuration)
- `/biomapper/scripts/verify_google_drive_setup.py` (Google Drive integration verification script)
- `/biomapper/pyproject.toml` (Project dependencies including google-auth, google-auth-oauthlib, and googleapiclient)
- `/biomapper/src/client/client_v2.py` (Main BiomapperClient for API interactions)
- `/biomapper/README.md` (Project architecture and usage patterns)