#!/bin/bash
# Install R-CT git hooks into the local clone's .git/hooks/. Idempotent.
# Run once after cloning; symlinks survive `git pull`.

set -e

REPO_ROOT=$(git rev-parse --show-toplevel)
GIT_DIR=$(git rev-parse --git-dir)
HOOK_SRC="$REPO_ROOT/code/scripts/git-hooks"

mkdir -p "$GIT_DIR/hooks"

for hook in pre-commit; do
    src="$HOOK_SRC/$hook"
    dst="$GIT_DIR/hooks/$hook"
    if [ ! -f "$src" ]; then
        echo "skip: $src not found"
        continue
    fi
    ln -sf "$src" "$dst"
    chmod +x "$src"
    echo "installed: $src -> $dst"
done
