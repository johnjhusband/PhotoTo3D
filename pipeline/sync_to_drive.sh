#!/usr/bin/env bash
# sync_to_drive.sh — push the latest AI images to John's Google Drive folder.
# One-time setup (John authorizes his own Drive; I can't log in for him):
#   1. John runs:  rclone authorize "drive"   (opens browser, approve, copy the printed token JSON)
#   2. I create the remote with that token + the target folder id:
#        rclone config create gdrive drive scope=drive \
#          root_folder_id=1INrnKYrmYm9DwYDbhvaKUZ_AK9nSjhIu token='<PASTED JSON>'
# After that, this script keeps the Drive folder current with the local images.
set -uo pipefail
SRC="${1:-/home/john/repos/PhotoTo3D/AI_out}"
REMOTE="${RCLONE_REMOTE:-gdrive:}"
# images first (what John wants to SEE); GLBs too so the 3D models are backed up.
rclone copy "$SRC" "$REMOTE" \
  --include "*.png" --include "*.glb" \
  --transfers 4 --checkers 8 -v 2>&1 | tail -20
echo "[drive-sync] done -> $REMOTE  ($(ls "$SRC"/*.png 2>/dev/null | wc -l) images)"
