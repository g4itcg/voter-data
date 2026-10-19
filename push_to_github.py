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

print("Pushing voter data to GitHub...")

# 1. Read the token for git auth
with open(TOKEN_FILE) as f:
    token = f.read().strip()

# 2. Set a credential helper for this push
os.environ["GIT_ASKPASS"] = "/opt/data/home/.git-credential-helper.sh"

# 3. Check if data actually changed before pushing
import hashlib
old_hash = None
if os.path.exists(os.path.join(REPO_DIR, "voter_data.json")):
    with open(os.path.join(REPO_DIR, "voter_data.json"), "rb") as f:
        old_hash = hashlib.md5(f.read()).hexdigest()
new_hash = hashlib.md5(open(DATA_SRC, "rb").read()).hexdigest()

if old_hash == new_hash:
    print("Data unchanged — no push needed")
    sys.exit(0)

print(f"Data changed: {old_hash[:8]} → {new_hash[:8]}, pushing...")

# 4. Copy latest data into repo
import shutil
shutil.copy(DATA_SRC, os.path.join(REPO_DIR, "voter_data.json"))
shutil.copy(os.path.join(os.path.dirname(DATA_SRC), "vbm_history.json"),
            os.path.join(REPO_DIR, "vbm_history.json"))

# 5. Commit and push
run(["git", "add", "voter_data.json", "vbm_history.json"], REPO_DIR)
run(["git", "commit", "--author", "Jarvis <jarvis.green.net@gmail.com>", "-m", f"Auto-update voter data {__import__('datetime').datetime.now().strftime('%b %d %H:%M')}"], REPO_DIR)
push_result = run(["git", "push", "origin", "main"], REPO_DIR)

if push_result.returncode == 0:
    print("✅ Pushed to GitHub successfully")
    sys.exit(0)
else:
    print("❌ Push failed")
    sys.exit(1)