# Getting the Correct Shared Drive Folder ID

## The Issue
The ID `0AKkGZ5ECUf0JUk9PVA` looks like a Shared Drive root ID, not a folder ID.

## How to Get the Correct ID

### Option 1: Use the Shared Drive Root
1. Go to your Shared Drive
2. If you're at the root level, the URL might be:
   - `https://drive.google.com/drive/u/0/folders/0AKkGZ5ECUf0JUk9PVA`
   - Or `https://drive.google.com/drive/shared-drives/0AKkGZ5ECUf0JUk9PVA`

### Option 2: Create a Subfolder (Recommended)
1. Inside your Shared Drive, create a new folder called "biomapper-output" or similar
2. Click into that folder
3. The URL will change to something like:
   `https://drive.google.com/drive/folders/1ABC_longerID_xyz`
4. Copy that longer ID (usually starts with 1)

### Option 3: Navigate Differently
1. Go to https://drive.google.com
2. Click "Shared drives" 
3. Click into your Shared Drive
4. Click "New" → "Folder" to create a subfolder
5. Name it "biomapper-output"
6. Click into it
7. Copy the ID from the URL

## What the ID Should Look Like
- Personal/Shared folder IDs usually look like: `1tGkQps5DwaYn761J5DD-BNbETuGkLTeZ` (longer)
- Shared Drive root IDs look like: `0AKkGZ5ECUf0JUk9PVA` (shorter, starts with 0)

## Test Command
Once you have the right ID:
```bash
# Update .env with the new ID
# Then test:
poetry run python test_google_drive_sync.py
```

## Quick Debug
Try creating a subfolder in the Shared Drive and use that folder's ID instead of the root drive ID.