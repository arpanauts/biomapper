Sync to Google Drive
===================

.. automodule:: src.actions.io.sync_to_google_drive_v2
.. automodule:: src.actions.io.sync_to_google_drive_v3

Overview
--------

The Google Drive sync actions (``SYNC_TO_GOOGLE_DRIVE_V2`` and ``SYNC_TO_GOOGLE_DRIVE_V3``) enable uploading biomapper results directly to Google Drive for sharing and archival. Both actions support OAuth2 and Service Account authentication methods.

**V3 is recommended** for new implementations as it includes enhanced error handling, chunked upload support, and better progress tracking.

Key Features
------------

- **Multiple Authentication**: OAuth2 (personal) and Service Account (automated)
- **Chunked Upload**: Efficient handling of large files
- **Progress Tracking**: Real-time upload progress
- **Automatic Organization**: Creates organized folder structures
- **Error Recovery**: Robust handling of network issues and timeouts

Authentication Methods
----------------------

OAuth2 (Recommended for Personal Use)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Benefits**:
- Upload to your personal Drive storage
- No quota limitations (uses your personal storage)
- Full ownership and control of uploaded files
- Easy sharing using Drive's native sharing features

**Setup**: See :doc:`../integrations/google_drive` for complete OAuth2 setup guide.

Service Account (For Automation)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Benefits**:
- Programmatic access without user interaction
- Suitable for automated pipelines
- Can be shared across team members

**Limitations**:
- Cannot store files (no storage quota)
- Must upload to folders shared with the service account
- More complex permission management

Parameters
----------

SYNC_TO_GOOGLE_DRIVE_V3
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 25 15 10 50
   :header-rows: 1

   * - Parameter
     - Type
     - Required
     - Description
   * - ``input_key``
     - string
     - Yes
     - Key for the dataset to upload
   * - ``output_key``
     - string
     - Yes
     - Key for the output with upload metadata
   * - ``file_path``
     - string
     - Yes
     - Local file path to upload
   * - ``drive_folder_name``
     - string
     - Yes
     - Google Drive folder name for organization
   * - ``strategy_name``
     - string
     - No
     - Strategy name for folder organization
   * - ``auth_method``
     - string
     - No
     - 'oauth2' or 'service_account' (default: auto-detect)
   * - ``chunk_size``
     - integer
     - No
     - Upload chunk size in bytes (default: 10MB)

SYNC_TO_GOOGLE_DRIVE_V2
~~~~~~~~~~~~~~~~~~~~~~~

Legacy version with similar parameters but without chunked upload support.

Example Usage
-------------

YAML Strategy (V3)
~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: upload_results
       action:
         type: SYNC_TO_GOOGLE_DRIVE_V3
         params:
           input_key: final_results
           output_key: upload_status
           file_path: "/tmp/biomapper_results.csv"
           drive_folder_name: "Biomapper Results"
           strategy_name: "metabolomics_pipeline_v3"
           auth_method: "oauth2"
           chunk_size: 5242880  # 5MB chunks

Python Client
~~~~~~~~~~~~~

.. code-block:: python

   from src.client.client_v2 import BiomapperClient

   client = BiomapperClient(base_url="http://localhost:8000")
   
   result = await client.run_action(
       action_type="SYNC_TO_GOOGLE_DRIVE_V3",
       params={
           "input_key": "results_dataset",
           "output_key": "drive_upload",
           "file_path": "/results/metabolite_mapping.csv",
           "drive_folder_name": "Metabolomics Analysis",
           "strategy_name": "arivale_harmonization",
           "auth_method": "oauth2"
       },
       context=context
   )
   
   # Access upload metadata
   upload_info = result.context["datasets"]["drive_upload"]
   print(f"Uploaded to: {upload_info['drive_url']}")

Folder Organization
-------------------

The actions create organized folder structures on Google Drive:

::

   Biomapper Results/
   ├── metabolomics_pipeline_v3/
   │   ├── 2025-08-22_14-30-15/
   │   │   ├── mapping_results.csv
   │   │   ├── statistics.json
   │   │   └── visualizations.png
   │   └── latest/  # Symlink to most recent
   └── protein_harmonization/
       ├── 2025-08-22_15-45-30/
       └── latest/

Output Format
-------------

The action returns metadata about the upload:

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Field
     - Description
   * - ``file_id``
     - Google Drive file ID
   * - ``drive_url``
     - Direct link to view the file
   * - ``folder_id``
     - Parent folder ID
   * - ``upload_size``
     - File size in bytes
   * - ``upload_duration``
     - Time taken for upload
   * - ``chunks_uploaded``
     - Number of chunks (V3 only)

Performance Considerations
--------------------------

Upload Speed
~~~~~~~~~~~~

Typical performance metrics:
- **Small files** (<10MB): 2-5 seconds
- **Medium files** (10-100MB): 10-30 seconds  
- **Large files** (>100MB): 1-3 minutes

Factors affecting speed:
- Network bandwidth
- File size and type
- Chunk size configuration
- Google Drive API limits

Optimization Tips
~~~~~~~~~~~~~~~~~

1. **Adjust chunk size**: Larger chunks for faster networks
2. **Use compression**: Pre-compress large CSV files
3. **Batch uploads**: Group related files together
4. **Monitor quotas**: Be aware of daily API limits

Authentication Setup
--------------------

OAuth2 Setup
~~~~~~~~~~~~~

1. **Create OAuth2 credentials** in Google Cloud Console
2. **Download client configuration** JSON file
3. **Run setup script**:

   .. code-block:: bash

      poetry run python scripts/setup_oauth2_drive.py

4. **Follow browser authorization** flow
5. **Test upload**:

   .. code-block:: bash

      python scripts/verify_google_drive_setup.py

Service Account Setup
~~~~~~~~~~~~~~~~~~~~~

1. **Create service account** in Google Cloud Console
2. **Download credentials** JSON file
3. **Set environment variable**:

   .. code-block:: bash

      export GOOGLE_SERVICE_ACCOUNT_PATH="/path/to/credentials.json"

4. **Create shared folder** and share with service account email

Error Handling
--------------

Common Issues
~~~~~~~~~~~~~

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Error
     - Solution
   * - ``Authentication failed``
     - Re-run OAuth2 setup or check service account credentials
   * - ``Quota exceeded``
     - Wait for quota reset or reduce upload frequency
   * - ``Folder not found``
     - Ensure folder exists and is shared with service account
   * - ``Network timeout``
     - Retry upload or reduce chunk size
   * - ``Permission denied``
     - Verify folder sharing permissions

Retry Logic
~~~~~~~~~~~

V3 includes automatic retry logic:
- **Exponential backoff** for rate limiting
- **Automatic retry** on network errors
- **Chunked resume** for interrupted uploads
- **Progress preservation** across retries

Best Practices
--------------

1. **File Naming**: Use timestamp and strategy name for uniqueness
2. **Folder Organization**: Create logical folder hierarchies
3. **Authentication**: Prefer OAuth2 for personal use, Service Account for automation
4. **Error Handling**: Always check upload status in workflows
5. **Cleanup**: Regularly clean up old result files

Security Considerations
-----------------------

- **Credentials Protection**: Never commit OAuth2 tokens or service account keys
- **Access Control**: Limit folder sharing to necessary users only
- **Data Sensitivity**: Be aware of data privacy when uploading to cloud storage
- **Audit Trail**: Monitor upload logs for security compliance

Integration Examples
--------------------

Complete Pipeline with Upload
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   name: "metabolomics_with_drive_sync"
   description: "Complete metabolomics pipeline with Google Drive upload"
   
   steps:
     - name: load_data
       action:
         type: LOAD_DATASET_IDENTIFIERS
         # ... data loading parameters
         
     - name: progressive_matching
       action:
         type: PROGRESSIVE_SEMANTIC_MATCH
         # ... matching parameters
         
     - name: export_results
       action:
         type: EXPORT_DATASET
         params:
           input_key: final_results
           file_path: "/tmp/metabolomics_results.csv"
           
     - name: sync_to_drive
       action:
         type: SYNC_TO_GOOGLE_DRIVE_V3
         params:
           input_key: final_results
           output_key: drive_metadata
           file_path: "/tmp/metabolomics_results.csv"
           drive_folder_name: "Metabolomics Analysis"
           strategy_name: "progressive_pipeline_v3"

See Also
--------

- :doc:`../integrations/google_drive` - Complete Google Drive setup guide
- :doc:`export_dataset` - Exporting data for upload
- :doc:`../examples/advanced_pipelines` - Complete pipeline examples

---

## Verification Sources
*Last verified: 2025-08-22*

This documentation was verified against the following project resources:

- `/biomapper/src/actions/io/sync_to_google_drive_v2.py` (actual implementation of SYNC_TO_GOOGLE_DRIVE_V2)
- `/biomapper/src/actions/io/sync_to_google_drive_v3.py` (enhanced V3 implementation with improved error handling)
- `/biomapper/src/actions/typed_base.py` (TypedStrategyAction base class)
- `/biomapper/src/actions/registry.py` (self-registration via @register_action decorator)
- `/biomapper/CLAUDE.md` (2025 standardizations and integration patterns)
- `/biomapper/pyproject.toml` (Google API client dependencies)