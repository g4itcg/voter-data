#!/usr/bin/env python3
"""Push voter_data.json to GitHub after each fetch."""
import subprocess, os, sys

REPO_DIR = "/opt/data/voter-data-repo"
DATA_SRC = "/opt/data/voter_data.json"
TOKEN_FILE = os.path.expanduser("~/.github_token")

def run(cmd, cwd=REPO_DIR):
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=cwd)
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

# 5. Commit and push
run(["git", "add", "voter_data.json", "vbm_history.json"], REPO_DIR)
run(["git", "commit", "--author", "Jarvis <jarvis.green.net@gmail.com>",
     "-m", f"Auto-update {__import__('datetime').datetime.now().strftime('%b %d %H:%M')} ET"],
    REPO_DIR)
push_result = run(["git", "push", "origin", "main"], REPO_DIR)

if push_result.returncode == 0:
    print("✅ Pushed to GitHub successfully")
    sys.exit(0)
else:
    print("❌ Push failed")
    sys.exit(1)