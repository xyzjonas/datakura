#!/usr/bin/env bash
# Bump the project version with uv and propagate it to all places that carry it.
# Usage: scripts/release.sh [dev|patch|minor|major]   (default: dev)
set -euo pipefail

BUMP="${1:-dev}"
case "$BUMP" in
  dev | patch | minor | major) ;;
  *) echo "usage: $0 [dev|patch|minor|major]" >&2; exit 1 ;;
esac

cd "$(dirname "$0")/.."

if [[ -n "$(git status --porcelain)" ]]; then
  echo "working tree is dirty - commit or stash first" >&2
  exit 1
fi

OLD="$(uv version --short)"

# last commit that touched the version line in pyproject.toml = previous release
BASE="$(git log -1 --format=%H -G'^version = ' -- pyproject.toml)"
# skip non-user-facing semantic commits (chore:, docs:, ci:, optionally scoped)
COMMITS="$(git log --no-merges --format=%s "$BASE..HEAD" | grep -Ev '^(chore|docs|ci)(\([^)]*\))?!?:' || true)"

if [[ -z "$COMMITS" ]]; then
  echo "no commits since last release ($BASE) - nothing to release" >&2
  exit 1
fi

uv version --bump "$BUMP" --no-sync >/dev/null
NEW="$(uv version --short)"
RELEASE_DATE="$(date +%F)"

OLD="$OLD" NEW="$NEW" RELEASE_DATE="$RELEASE_DATE" COMMITS="$COMMITS" python3 -I - <<'PY'
import os
import re
from pathlib import Path

old, new = os.environ["OLD"], os.environ["NEW"]
date = os.environ["RELEASE_DATE"]
rows = [r for r in os.environ["COMMITS"].splitlines() if r.strip()]


def edit(path: str, fn) -> None:
    p = Path(path)
    p.write_text(fn(p.read_text()))


# pyproject.toml
edit("pyproject.toml", lambda s: re.sub(r'(?m)^version = ".*"$', f'version = "{new}"', s, count=1))

# API docs version
edit("apps/warehouse/api/app.py", lambda s: re.sub(r'version="[^"]*"', f'version="{new}"', s, count=1))

# frontend package.json
edit("frontend/package.json", lambda s: re.sub(r'(?m)^(  "version": ").*(",)$', rf"\g<1>{new}\2", s, count=1))


def esc(row: str) -> str:
    return row.replace("\\", "\\\\").replace("'", "\\'")


def version_ts(s: str) -> str:
    s = re.sub(r"(export const APP_VERSION = ).*", rf"\1'{new}'", s, count=1)
    entry = (
        "  {\n"
        f"    version: '{new}',\n"
        f"    releaseDate: '{date}',\n"
        "    rows: [\n"
        + "".join(f"      '{esc(r)}',\n" for r in rows)
        + "    ],\n"
        "  },\n"
    )
    marker = "export const CHANGELOG_ENTRIES: ChangelogEntry[] = [\n"
    s = s.replace(marker, marker + entry, 1)
    return s.replace("    {\n    version:", "  {\n    version:", 1)


edit("frontend/src/utils/version.ts", version_ts)
PY

echo "released $OLD -> $NEW ($RELEASE_DATE)"
echo "changelog rows:"
sed 's/^/  - /' <<<"$COMMITS"
echo "review with 'git diff', then commit (e.g. '$NEW: <summary>')"
