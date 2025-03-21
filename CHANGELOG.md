# Changelog

All notable changes to Biomapper will be documented in this file.

## [0.5.1] - 2025-03-21

### Enhanced
- Added support for handling comment lines in CSV/TSV files:
  - Created centralized `load_tabular_file` utility function in utils/io_utils.py
  - Automatically skips lines starting with '#' during data loading
  - Intelligently detects file type (CSV/TSV) and selects appropriate separator
  - Maintains memory-aware file size limits (50% of available memory)
  - Works consistently across both frontend and backend components

## [0.5.0] - 2025-03-21

### Added
- Comprehensive UI documentation with separate technical and user sections
- Integration of Mermaid diagram support for visual workflows in documentation
- Proper Poetry-based documentation build configuration for ReadTheDocs

### Enhanced
- Significantly improved handling of large CSV files:
  - Removed arbitrary 5MB file size limit in favor of a dynamic approach
  - Added intelligent file size detection that sets maximum file size to 50% of available device memory
  - Implemented real-time upload progress tracking with visual progress bar
  - Enhanced file upload with XMLHttpRequest for accurate progress reporting
  - Added file size display in MB next to selected file name
- Modified backend API server configuration to support large CSV files:
  - Increased MAX_UPLOAD_SIZE setting from 10MB to 1GB
  - Implemented dynamic calculation based on system memory using psutil.virtual_memory().available / 2
  - Added 1GB fallback if memory information can't be determined
  - Ensured consistent file size limit calculation between frontend and backend

### Fixed
- Resolved "413 Payload Too Large" errors when uploading larger datasets

## [0.4.0] - Initial Release

- Initial public release of Biomapper
