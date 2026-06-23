"""Scaffold a new module by cloning the _template blueprint.

    python -m scripts.new_module vehicles
    python -m scripts.new_module utilities --name Bollette --icon ⚡

What it does:
  * copies app/modules/_template -> app/modules/<key>
  * replaces the token `example`/`Example` with your key throughout
  * rewrites the manifest (key/name/icon)
  * adds <key> to AVAILABLE in app/modules/__init__.py

After it runs, enable the module with HESTIA_ENABLED_MODULES=...,<key> and
start editing models.py / service.py. The new module is a real vertical: REST
router + MCP tools + a dashboard summary, all wired the same way as dogs.
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = ROOT / "app" / "modules"
TEMPLATE = MODULES / "_template"
REGISTRY = MODULES / "__init__.py"

KEY_RE = re.compile(r"^[a-z][a-z0-9_]{1,30}$")
RESERVED = {"example", "_template", "base"}


def _validate(key: str) -> None:
    if not KEY_RE.match(key):
        raise SystemExit(f"invalid key '{key}': use lowercase letters, digits, underscore")
    if key in RESERVED:
        raise SystemExit(f"'{key}' is reserved")
    if (MODULES / key).exists():
        raise SystemExit(f"module '{key}' already exists at {MODULES / key}")


def _capitalize(key: str) -> str:
    # vehicles -> Vehicles ; car_parts -> CarParts
    return "".join(part.capitalize() for part in key.split("_"))


def _copy_and_rewrite(key: str, name: str, icon: str) -> Path:
    dest = MODULES / key
    shutil.copytree(TEMPLATE, dest)

    cap = _capitalize(key)
    for path in dest.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        # CapWord first, then lowercase (both case-sensitive; no overlap).
        text = text.replace("Example", cap).replace("example", key)
        path.write_text(text, encoding="utf-8")

    # Rewrite the manifest fields the user actually chose.
    init = dest / "__init__.py"
    text = init.read_text(encoding="utf-8")
    text = re.sub(r'name="[^"]*"', f'name="{name}"', text, count=1)
    text = re.sub(r'icon="[^"]*"', f'icon="{icon}"', text, count=1)
    text = text.replace(
        '"""TEMPLATE module package. Copy, then register in app/modules/__init__.py\n'
        '(AVAILABLE) or enable via HESTIA_ENABLED_MODULES."""',
        f'"""{name} module."""',
    )
    init.write_text(text, encoding="utf-8")
    return dest


def _register(key: str) -> bool:
    text = REGISTRY.read_text(encoding="utf-8")
    m = re.search(r"AVAILABLE:\s*tuple\[str, \.\.\.\]\s*=\s*\(([^)]*)\)", text)
    if not m:
        return False
    current = [c.strip().strip('"').strip("'") for c in m.group(1).split(",") if c.strip()]
    if key in current:
        return True
    current.append(key)
    rebuilt = "AVAILABLE: tuple[str, ...] = (" + ", ".join(f'"{c}"' for c in current) + ")"
    text = text[: m.start()] + rebuilt + text[m.end():]
    REGISTRY.write_text(text, encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold a new Hestia module.")
    parser.add_argument("key", help="module key, e.g. vehicles (lowercase)")
    parser.add_argument("--name", help="display name (default: capitalized key)")
    parser.add_argument("--icon", default="📦", help="emoji icon (default: 📦)")
    args = parser.parse_args()

    key = args.key.strip().lower()
    _validate(key)
    name = args.name or _capitalize(key)

    dest = _copy_and_rewrite(key, name, args.icon)
    registered = _register(key)

    print(f"created module '{key}' at {dest.relative_to(ROOT)}")
    print(f"  manifest: name={name!r} icon={args.icon}")
    print("  AVAILABLE updated" if registered else "  ! could not patch AVAILABLE — add it by hand")
    print()
    print("next:")
    print(f"  1. model your data in app/modules/{key}/models.py")
    print(f"  2. write the service functions + summary in service.py")
    print(f"  3. enable it:  HESTIA_ENABLED_MODULES=...,{key}")


if __name__ == "__main__":
    main()
