# Deploy runbook (devbox)

This is written to be executed by **Claude Code on the devbox**. Follow the
phases in order; each ends with a check. Stop and report if a check fails.

The deploy puts two loopback services behind the existing Cloudflare Tunnel:

| Service        | Bind             | Public hostname (via tunnel)      | Auth at the edge |
|----------------|------------------|-----------------------------------|------------------|
| Hestia API/UI  | `127.0.0.1:8000` | `hestia.robertonovara.me`         | Authentik / Access |
| Hestia MCP     | `127.0.0.1:8766` | `hestia-mcp.robertonovara.me`     | app-layer Bearer |

## Coexistence with devbox-bridge — read first

`devbox-bridge` already runs on this box (MCP on **8765**, `mcpdev.robertonovara.me`).
Hestia must not disturb it:

- **Different port:** Hestia MCP uses **8766**. Don't reuse 8765.
- **Different connector + token:** Hestia is registered as its **own** claude.ai
  connector with its **own** bearer token. Do not reuse devbox-bridge's token.
  This is deliberate: devbox-bridge is a privileged surface (`run_command`,
  `git_push`); Hestia is a low-privilege household app. Keep the trust zones
  separate.
- **Don't clobber cloudflared:** in Phase 4 you *add* two ingress rules to the
  existing tunnel config. Leave the `mcpdev` rule and the final `http_status:404`
  catch-all exactly where they are.

## Phase 0 — preconditions (verify, don't assume)

Run these and confirm before proceeding:

```bash
# OS + python
. /etc/os-release && echo "$PRETTY_NAME"      # expect Ubuntu Server
python3 --version                             # expect 3.12.x
command -v rsync curl                          # both must resolve

# cloudflared is installed and running, and find its config
systemctl is-active cloudflared
sudo find /etc/cloudflared /root/.cloudflared /home -maxdepth 3 -name 'config.y*ml' 2>/dev/null
cloudflared tunnel list                        # note the tunnel NAME/UUID serving this box
```

If `python3` is not 3.12, install it (`apt install python3.12 python3.12-venv`)
and pass `PYTHON=python3.12` to the installer in Phase 2.

## Phase 1 — get the code onto the devbox

Either clone the repo or copy this checkout to the box. End state: a working
directory containing `app/main.py` and `deploy/`.

```bash
# option A: from GitHub (once pushed)
git clone https://github.com/Pl1n10/hestia.git ~/hestia && cd ~/hestia
# option B: you already have the checkout here
cd <path-to-hestia-checkout>
test -f app/main.py && echo OK   # must print OK
```

## Phase 2 — run the installer

```bash
sudo bash deploy/install.sh
# if python3 isn't 3.12:  sudo PYTHON=python3.12 bash deploy/install.sh
```

What it does (idempotent — safe to re-run): creates the `hestia` system user,
syncs code to `/opt/hestia`, builds a venv, writes `/etc/hestia/hestia.env`
(generating a master agent token **once**), seeds the database in
`/var/lib/hestia`, installs + starts both systemd units, and prints the agent
token.

**Capture the printed token** — you need it in Phase 5. If you ever lose it,
read it back with `sudo grep AGENT_TOKEN /etc/hestia/hestia.env`.

Check: the installer's own smoke lines show `api … -> 200` and `mcp … -> 200`.

## Phase 3 — verify the services locally

```bash
systemctl status hestia-api hestia-mcp --no-pager   # both active (running)
curl -fsS http://127.0.0.1:8000/api/health ; echo
curl -fsS http://127.0.0.1:8000/api/dashboard ; echo   # cards for dogs+subscriptions
curl -fsS http://127.0.0.1:8766/healthz ; echo

# MCP is gated: no token -> 401, valid token -> reaches the MCP layer (not 401)
TOKEN=$(sudo grep -oP 'HESTIA_AGENT_TOKEN=\K.*' /etc/hestia/hestia.env)
curl -s -o /dev/null -w "no-token: %{http_code}\n" -X POST http://127.0.0.1:8766/mcp
curl -s -o /dev/null -w "token:    %{http_code}\n" -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' http://127.0.0.1:8766/mcp
```

Expect `no-token: 401` and `token:` a non-401 code (400 is fine here — it just
means the MCP session handshake is needed; auth passed). The audit log should
now show the auth events:

```bash
sudo tail -n 5 /var/lib/hestia/mcp-audit.log
```

## Phase 4 — cloudflared ingress + DNS

Edit the **existing** tunnel config (path from Phase 0). Merge the two rules from
`deploy/cloudflared/ingress.hestia.yaml` into the `ingress:` list, keeping the
`mcpdev` rule and ending with the `http_status:404` catch-all.

```bash
sudo nano /etc/cloudflared/config.yml      # or wherever it lives
cloudflared tunnel ingress validate         # must pass
```

Create the DNS routes once (use the tunnel name/UUID from Phase 0):

```bash
cloudflared tunnel route dns <TUNNEL> hestia.robertonovara.me
cloudflared tunnel route dns <TUNNEL> hestia-mcp.robertonovara.me
sudo systemctl restart cloudflared
```

Check from anywhere:

```bash
curl -fsS https://hestia-mcp.robertonovara.me/healthz ; echo   # 200, public
curl -s -o /dev/null -w "%{http_code}\n" https://hestia-mcp.robertonovara.me/mcp -X POST  # 401
```

## Phase 5 — register the MCP connector on claude.ai (Hermes)

This is a UI step (and/or Hermes config). Add a **custom connector**:

- URL: `https://hestia-mcp.robertonovara.me/mcp`
- Auth header: `Authorization: Bearer <the token from Phase 2>`

Then from Hermes, list tools — you should see `dogs_*` and `subscriptions_*`.
Try one write and confirm it lands:

```bash
# after Hermes calls e.g. dogs_log_activity:
sudo tail -n 5 /var/lib/hestia/mcp-audit.log         # an mcp_tool_call line, principal=hermes
curl -fsS http://127.0.0.1:8000/api/dashboard ; echo  # the dogs card reflects it
```

## Phase 6 — put the dashboard behind Authentik / Access

`hestia.robertonovara.me` serves the human UI and runs with
`HESTIA_AUTH_MODE=proxy`, so it trusts the `X-Authentik-Username` /
`-Email` headers your proxy injects. Front it the same way you front your other
internal apps (Cloudflare Access app or Authentik forward-auth). Confirm an
authenticated request reaches `/api/me` and shows your user.

## Operations

> **Any manual Hestia command must run with the env loaded** (absolute
> `HESTIA_DATABASE_URL`). Run from `/opt/hestia` with
> `env $(sudo grep -v '^#' /etc/hestia/hestia.env | xargs)` — as the seed command
> below does. Without it the default DB path is *relative*, so a stray empty
> `hestia.db` gets created in the CWD and your command touches a different file
> than the services. (FAILURES F-009.)

```bash
# logs
journalctl -u hestia-api -f
journalctl -u hestia-mcp -f
sudo tail -f /var/lib/hestia/mcp-audit.log

# restart / stop
sudo systemctl restart hestia-api hestia-mcp

# update to latest code: pull/sync, then re-run the installer (idempotent)
cd <checkout> && git pull && sudo bash deploy/install.sh

# issue an extra revocable agent token (hashed in the DB, shown once)
sudo -u hestia env $(sudo grep -v '^#' /etc/hestia/hestia.env | xargs) \
  /opt/hestia/.venv/bin/python -m scripts.seed --token

# rollback
sudo bash deploy/uninstall.sh           # keep data
sudo bash deploy/uninstall.sh --purge   # remove data/config/user too
```

## Security posture (why it's shaped this way)

- Both services bind loopback only; the tunnel is the sole ingress.
- The MCP requires a bearer token at the app layer (`mcp_require_auth=true`) and
  records every call to an audit log — independent of Cloudflare Access.
- Services run as the unprivileged `hestia` user under systemd hardening
  (`ProtectSystem=strict`, `NoNewPrivileges`, write access limited to
  `/var/lib/hestia`). A bug in a Hestia tool can't reach the rest of the box.
- Hestia's token and connector are separate from devbox-bridge's, so the
  household surface never grants the devbox's privileged operations.
