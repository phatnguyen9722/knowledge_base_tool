# Sync Mechanism, Backup, and Docker Setup Script
**Date:** 08/07/2026

## Overview
This session focused on building a robust bidirectional sync mechanism for the Knowledge Base, allowing users to synchronize their local data (Notes, Posts, Tasks, Vault) with external directories like iCloud or Google Drive. We also built an automatic backup system and a streamlined Docker setup experience.

## Features Implemented

### 1. Two-Way File Sync Engine (`app/sync.py`)
- Built a bidirectional sync algorithm that compares local files against a remote directory.
- Implemented conflict resolution using `st_mtime` (last modified timestamp), ensuring the newest version of a file always wins.
- Supported categories: Notes, Posts, Tasks, and Vault.
- Added a safe "Preview" mode that generates a diff (what will be pushed and what will be pulled) before executing file operations.

### 2. Standalone Backup System
- Added functionality to instantly zip the entire Knowledge Base data directory into a single archive (e.g., `kb_backup_YYYYMMDD_HHMMSS.zip`).
- Enabled saving these backups directly into a dedicated external backup directory.

### 3. Sync & Backup UI (Settings Modal)
- Added a new **Sync** tab in the Settings UI.
- Removed the need for manual path inputs; paths are now elegantly hardcoded to Docker's internal `/sync` and `/backup` volume mounts.
- Added buttons for:
  - **Scan Sync**: Previews the diff (Push/Fetch).
  - **Force Push All (Initial Setup)**: Unconditionally overwrites the remote sync folder with local files, ideal for initial bootstrapping.
  - **Backup Now**: Instantly generates a zipped backup.

### 4. Interactive Docker Setup Script (`setup.sh`)
- Created an interactive bash script to bridge the gap between the host OS (Mac/Windows/Linux) and the Docker container.
- The script interactively asks the user for their desired Sync and Backup paths on the host.
- **Smart iCloud Detection**: Added a macOS-specific prompt that detects the OS and offers a one-click shortcut to map the Sync folder directly to the official iCloud Drive directory.
- Automatically generates a `.env` file directly inside the `dockerise/` directory.

### 5. Docker Configuration Updates
- Modified `dockerise/docker-compose.yml` to utilize environment variables (`${SYNC_DIR}` and `${BACKUP_DIR}`).
- Implemented safe fallbacks (`:-../kb_sync`) to ensure Docker Compose doesn't crash if the setup script is bypassed.

### 6. Git Hygiene
- Added all generated and temporary configuration files (`.env`, `dockerise/.env`, `kb_sync/`, `kb_backup/`) to `.gitignore` to prevent accidental commits.

## Next Steps
- The Sync feature is now fully operational. Future enhancements could include background auto-syncing via scheduled tasks or websockets.
