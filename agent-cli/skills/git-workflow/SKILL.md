---
name: git-workflow
description: Git branching, commit conventions, rebase, conflict resolution, and PR workflow. Use when asked to set up git, write commit messages, or manage branches.
---

# Git Workflow

## Branch Naming
```
feature/add-user-auth
fix/login-500-error
chore/update-dependencies
docs/api-reference
refactor/extract-auth-service
```

## Commit Message Convention (Conventional Commits)
```
<type>(<scope>): <short summary>

type:  feat | fix | chore | docs | refactor | test | perf | ci
scope: optional, e.g. auth, api, ui

Examples:
feat(auth): add JWT refresh token endpoint
fix(products): handle null price in serializer
chore: upgrade Django to 5.1
test(orders): add integration tests for checkout flow
```

## Daily Workflow
```bash
# Start work
git checkout main && git pull
git checkout -b feature/my-feature

# During work — small, atomic commits
git add -p                          # stage hunks interactively
git commit -m "feat(api): add product list endpoint"

# Keep branch up to date
git fetch origin
git rebase origin/main              # prefer rebase over merge for clean history

# Push
git push -u origin feature/my-feature
```

## Useful Commands
```bash
# Undo last commit (keep changes)
git reset HEAD~1

# Amend last commit message
git commit --amend -m "new message"

# Stash work in progress
git stash push -m "wip: half-done auth"
git stash pop

# Find which commit broke something
git bisect start
git bisect bad                      # current is broken
git bisect good v1.0.0              # this tag was good
# git auto-checks out midpoints; mark each: git bisect good/bad

# Clean untracked files
git clean -fd

# See what changed
git diff HEAD~1 HEAD -- path/to/file
git log --oneline --graph --all
```

## Conflict Resolution
```bash
# When rebase hits conflict:
# 1. Edit conflicted files (remove <<<<, ====, >>>> markers)
# 2. Stage resolved files
git add resolved_file.py
# 3. Continue
git rebase --continue
# OR abort and go back
git rebase --abort
```

## .gitignore (Python project)
```
__pycache__/
*.pyc
.env
.venv/
venv/
*.egg-info/
dist/
build/
.DS_Store
*.sqlite3
```

## Rules
- Never force-push to `main` or `develop`
- Rebase feature branches, merge PRs (keeps history clean)
- One logical change per commit — don't mix refactor + feature
- Always `git pull --rebase` not `git pull` (avoids merge commits)
