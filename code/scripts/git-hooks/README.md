# git-hooks/

Client-side git hooks for R-CT. Symlinked into `.git/hooks/` by `install.sh`.

## Install

```bash
bash code/scripts/git-hooks/install.sh
```

Idempotent. Survives `git pull` (symlinks point at tracked sources).

## Hooks

### `pre-commit` — enforces changelog.md update on every commit

Project rule (per `changelog.md` preamble): every commit on `main` drives
a version roll. The hook fails the commit if `changelog.md` is not in the
staged set, with a clear message pointing at the rule.

**Override** in genuine emergencies with `git commit --no-verify`. Doing
so creates drift between the changelog and the code; treat as a bug to
clean up, not normal operation.

## Why client-side and not server-side

We don't run our own GitHub Actions for this repo (the parent NVIDIA
Workbench-example template doesn't have a CI surface for it). A
server-side check would belong in `.github/workflows/` once we add one;
until then the client-side hook keeps contributors honest without
needing CI infrastructure.

If you're adding a contributor and want to enforce server-side too, add
a workflow under `.github/workflows/check-changelog.yml` that runs the
same diff check on every push and PR. Tracked as a future RCT item.
