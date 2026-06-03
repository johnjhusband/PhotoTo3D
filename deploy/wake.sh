#!/usr/bin/env bash
# wake.sh — recreate the mesh3d server from the parked snapshot (see park.sh).
# Comes back fully configured in a few minutes; no reinstall needed.
#
# Reads HCLOUD_TOKEN from env or /home/john/repos/CTO/.env (HETZNER_API_TOKEN).
set -euo pipefail
SERVER_NAME="${SERVER_NAME:-mesh3d-cpu}"
SERVER_TYPE="${SERVER_TYPE:-ccx33}"          # 8 dedicated cores, 32GB
SNAP_DESC="${SNAP_DESC:-mesh3d-cpu-parked}"
SSH_KEY_NAME="${SSH_KEY_NAME:-cto-agent-deploy}"
LOCATION="${LOCATION:-hil}"

if [ -z "${HCLOUD_TOKEN:-}" ] && [ -f /home/john/repos/CTO/.env ]; then
  HCLOUD_TOKEN="$(grep -h '^HETZNER_API_TOKEN' /home/john/repos/CTO/.env | cut -d= -f2 | tr -d '\r\n\"')"
fi
export HCLOUD_TOKEN

# already running?
ip="$(hcloud server list -o noheader -o columns=name,ipv4 | awk -v n="$SERVER_NAME" '$1==n{print $2}')"
if [ -n "$ip" ]; then echo "[wake] $SERVER_NAME already running at $ip"; exit 0; fi

img="$(hcloud image list --type snapshot -o noheader -o columns=id,description | awk -v d="$SNAP_DESC" '$2==d{print $1}' | head -1)"
[ -n "$img" ] || { echo "[wake] no snapshot '$SNAP_DESC' found — nothing to restore"; exit 1; }

echo "[wake] recreating $SERVER_NAME from snapshot $img ..."
hcloud server create --name "$SERVER_NAME" --type "$SERVER_TYPE" \
  --image "$img" --location "$LOCATION" --ssh-key "$SSH_KEY_NAME"
hcloud server list -o columns=name,ipv4 | grep "$SERVER_NAME"
echo "[wake] up. Snapshot can be kept for next time or deleted to save a few cents."
