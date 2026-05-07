#!/bin/bash
# Sync selected docs from the fleming-keith/wai-hackathon-2026 enterprise repo
# into R-CT's local mirror folder. Idempotent — safe to run repeatedly.
#
# Direction: read-only, enterprise -> R-CT. Edits to mirrored files belong
# upstream (in the enterprise repo); re-running this script overwrites local
# changes by design.
#
# See repo-bridge.md for the full rationale and what does/doesn't cross.

set -euo pipefail

ENTERPRISE_REPO="${ENTERPRISE_REPO:-$HOME/wai-hackathon-2026}"
RCT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MIRROR="$RCT_ROOT/data/scratch/hackathon-smithsonian/upstream"
SCHEMAS="$RCT_ROOT/code/governance/schemas"

# (source-relative-path -> destination-absolute-path) pairs.
# Add a line to expand the bridge; remove a line to retire one.
MANIFEST=(
  "schemas/rag-record.schema.json|$SCHEMAS/rag-record.schema.json"
  "outputs/case-bundles-summary.md|$MIRROR/case-bundles-summary.md"
  "outputs/curation-workflow.md|$MIRROR/curation-workflow.md"
  "outputs/INDEX.md|$MIRROR/outputs-index.md"
  "outputs/README.md|$MIRROR/outputs-readme.md"
  "outputs/quick-reference.md|$MIRROR/quick-reference.md"
  "docs/project/participant-packet.md|$MIRROR/participant-packet.md"
  "docs/project/team-plan.md|$MIRROR/team-plan.md"
)

if [ ! -d "$ENTERPRISE_REPO" ]; then
  echo "ERROR: enterprise repo not found at $ENTERPRISE_REPO" >&2
  echo "Clone it first:" >&2
  echo "  git clone https://github.com/fleming-keith/wai-hackathon-2026.git $ENTERPRISE_REPO" >&2
  exit 1
fi

echo "==> updating enterprise checkout: $ENTERPRISE_REPO"
git -C "$ENTERPRISE_REPO" pull --ff-only

mkdir -p "$MIRROR" "$SCHEMAS"

# Stamp the mirror with the upstream commit so divergence is traceable.
UPSTREAM_SHA=$(git -C "$ENTERPRISE_REPO" rev-parse HEAD)
UPSTREAM_DATE=$(git -C "$ENTERPRISE_REPO" log -1 --format=%cI HEAD)
cat > "$MIRROR/.sync-stamp" <<EOF
upstream_repo: fleming-keith/wai-hackathon-2026
upstream_sha: $UPSTREAM_SHA
upstream_commit_date: $UPSTREAM_DATE
synced_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)
synced_by_script: code/scripts/sync-from-enterprise.sh
EOF

changed=0
missing=0
for entry in "${MANIFEST[@]}"; do
  src_rel="${entry%%|*}"
  dst="${entry#*|}"
  src="$ENTERPRISE_REPO/$src_rel"

  if [ ! -f "$src" ]; then
    echo "  [missing] $src_rel  (not present in upstream — skipping)"
    missing=$((missing + 1))
    continue
  fi

  mkdir -p "$(dirname "$dst")"
  if ! cmp -s "$src" "$dst" 2>/dev/null; then
    cp "$src" "$dst"
    echo "  [updated] $src_rel -> ${dst#$RCT_ROOT/}"
    changed=$((changed + 1))
  fi
done

echo
echo "Sync complete. $changed file(s) updated, $missing missing."
echo "Mirror stamped at $MIRROR/.sync-stamp (upstream sha $UPSTREAM_SHA)."
echo "Edits to mirrored files belong upstream — never edit them in $MIRROR/."
