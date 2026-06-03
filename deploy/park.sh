#!/usr/bin/env bash
# park.sh — stop paying for the mesh3d server while keeping its full state.
#
# Hetzner bills a server until it is DELETED (power-off does NOT stop billing).
# So to "pause" cheaply: snapshot the disk, then delete the server. The snapshot
# costs only a few cents/month (compressed GB). wake.sh recreates from it.
#
# Reads HCLOUD_TOKEN from env or /home/john/repos/CTO/.env (HETZNER_API_TOKEN).
set -euo pipefail
SERVER_NAME="${SERVER_NAME:-mesh3d-cpu}"
SNAP_DESC="${SNAP_DESC:-mesh3d-cpu-parked}"

if [ -z "${HCLOUD_TOKEN:-}" ] && [ -f /home/john/repos/CTO/.env ]; then
  HCLOUD_TOKEN="$(grep -h '^HETZNER_API_TOKEN' /home/john/repos/CTO/.env | cut -d= -f2 | tr -d '\r\n\"')"
fi
export HCLOUD_TOKEN

id="$(hcloud server list -o noheader -o columns=name,id | awk -v n="$SERVER_NAME" '$1==n{print $2}')"
[ -n "$id" ] || { echo "Server $SERVER_NAME not found (already parked?)."; exit 0; }

echo "[park] creating snapshot of $SERVER_NAME (id $id)..."
hcloud server create-image --type snapshot --description "$SNAP_DESC" "$id"
echo "[park] deleting server $SERVER_NAME to stop billing..."
hcloud server delete "$id"
echo "[park] done. Server deleted, snapshot '$SNAP_DESC' retained. Run wake.sh to restore."
hcloud image list --type snapshot -o columns=id,description,image_size,created | grep "$SNAP_DESC" || true
