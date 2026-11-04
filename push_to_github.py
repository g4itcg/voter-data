#!/usr/bin/env python3
"""Push voter_data.json to GitHub after each fetch."""
import subprocess, os, sys

REPO_DIR = "/opt/data/voter-data-repo"
DATA_SRC = "/opt/data/voter_data.json"
TOKEN_FILE = os.path.expanduser("~/.github_token")

def run(cmd, cwd=REPO_DIR):
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=90, cwd=cwd)
    if result.returncode != 0:
        print(f"  ⚠️  {cmd[0]} exited {result.returncode}: {result.stderr.strip()}")
    return result

print("Pushing voter data to GitHub...\n")

# 1. Read the token for git auth
with open(TOKEN_FILE) as f:
    token = f.read().strip()

# 2. Set a credential helper for this push
os.environ["GIT_ASKPASS"] = "/opt/data/home/.git-credential-helper.sh"

# 3. Always push — even if only the timestamp changed, so the update time stays fresh
import json, hashlib
now_ts = "?"
if os.path.exists(DATA_SRC):
    with open(DATA_SRC) as f:
        try:
            d = json.load(f)
            now_ts = d.get("fetched_at", "?")[:19]
        except:
            pass

# 3. Check if data actually changed by comparing full content (including timestamp)
old_hash = None
repo_data = os.path.join(REPO_DIR, "voter_data.json")
if os.path.exists(repo_data):
    with open(repo_data) as f:
        old_hash = hashlib.md5(f.read().encode()).hexdigest()
with open(DATA_SRC) as f:
    new_hash = hashlib.md5(f.read().encode()).hexdigest()

if old_hash == new_hash:
    print(f"[{now_ts}] Data unchanged — no push needed")
    sys.exit(0)

print(f"[{now_ts}] Data changed, pushing to GitHub...")

# 4. Copy latest data into repo
import shutil
shutil.copy(DATA_SRC, repo_data)
shutil.copy(os.path.join(os.path.dirname(DATA_SRC), "vbm_history.json"),
            os.path.join(REPO_DIR, "vbm_history.json"))

# 5. Commit
run(["git", "add", "voter_data.json", "vbm_history.json"], REPO_DIR)
run(["git", "commit", "--author", "Jarvis <jarvis.green.net@gmail.com>",
     "-m", f"Auto-update {__import__('datetime').datetime.now().strftime('%b %d %H:%M')} ET"],
    REPO_DIR)

# 6. Push with retry: fetch before each attempt, rebase on race, exponential backoff.
#    Multiple cron jobs push to this repo in the same minute (voter data, FL
#    comparison, national comparison). "cannot lock ref" / "[rejected]" mean a
#    sibling push landed first — rebase ours on top and retry.
import time
RACE_PATTERNS = ("cannot lock ref", "fetch first", "[rejected]", "non-fast-forward")
MAX_ATTEMPTS = 5
backoff = [8, 11, 14, 17, 20]  # seconds, exponential-ish

push_result = None
for attempt in range(1, MAX_ATTEMPTS + 1):
    # Refresh the tracking ref so push (and the lease check) compares against live remote
    run(["git", "fetch", "origin", "main"], REPO_DIR)
    # If a sibling pushed since our commit, rebase ours on top of it.
    # rebase.autoStash keeps this working when the working tree has unstaged
    # edits (e.g. push_to_github.py itself changed) — a plain pull --rebase
    # aborts with "cannot pull with rebase: You have unstaged changes".
    run(["git", "-c", "rebase.autoStash=true", "pull", "--rebase", "origin", "main"], REPO_DIR)
    push_result = run(["git", "push", "origin", "main"], REPO_DIR)
    if push_result.returncode == 0:
        print("✅ Pushed to GitHub successfully")
        sys.exit(0)
    err = (push_result.stderr or "") + (push_result.stdout or "")
    if attempt < MAX_ATTEMPTS and any(p in err for p in RACE_PATTERNS):
        print(f"  ⚠️  Race detected (attempt {attempt}/{MAX_ATTEMPTS}), backing off {backoff[attempt - 1]}s and retrying...")
        time.sleep(backoff[attempt - 1])
    else:
        break

# Never force-push here. A sibling cron job (FL/national comparison refresh) shares
# this repo; after a fresh fetch the lease check passes against the sibling's new
# HEAD, so --force-with-lease would silently discard its commit. Leave our commits
# local — the next 10-min run rebases and retries.
print("❌ Push failed after all retries — commits kept locally, next run will retry")
sys.exit(1)