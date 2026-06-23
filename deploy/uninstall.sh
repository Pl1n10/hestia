#!/usr/bin/env bash
#
# Hestia uninstaller. Stops + removes the services and code. By default it KEEPS
# your data (database + audit log). Pass --purge to also delete /var/lib/hestia
# and /etc/hestia.
#
#     sudo bash deploy/uninstall.sh           # keep data
#     sudo bash deploy/uninstall.sh --purge   # remove everything

set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "run as root"; exit 1; }

PURGE="${1:-}"

for svc in hestia-mcp hestia-api; do
  systemctl disable --now "${svc}.service" 2>/dev/null || true
  rm -f "/etc/systemd/system/${svc}.service"
done
systemctl daemon-reload

rm -rf /opt/hestia

if [[ "$PURGE" == "--purge" ]]; then
  rm -rf /var/lib/hestia /etc/hestia
  userdel hestia 2>/dev/null || true
  echo "purged data, config, and user."
else
  echo "removed services and code. Data kept in /var/lib/hestia and /etc/hestia."
fi
