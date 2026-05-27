"""Upload CamemBERT artifacts to HuggingFace Hub (private repo)."""
from __future__ import annotations

import os
from pathlib import Path

from huggingface_hub import HfApi, create_repo

def load_env(path: str) -> dict:
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env

env = load_env("apps/api/.env")
token = env.get("HF_TOKEN", "")

if not token:
    print("ERROR: HF_TOKEN not found in apps/api/.env")
    exit(1)

api = HfApi(token=token)
user = api.whoami()
username = user["name"]
print(f"Logged in as: {username}")

REPO_ID = f"{username}/freeassist-camembert-intent"

# Create private repo
try:
    create_repo(REPO_ID, token=token, private=True, exist_ok=True)
    print(f"Repo ready: {REPO_ID}")
except Exception as e:
    print(f"Repo already exists or error: {e}")

# Upload best model
best_dir = Path("artifacts/best")
if not best_dir.exists():
    print(f"ERROR: {best_dir} not found")
    exit(1)

print(f"Uploading from {best_dir}...")
api.upload_folder(
    folder_path=str(best_dir),
    repo_id=REPO_ID,
    token=token,
    commit_message="Upload CamemBERT fine-tuned intent classifier + FAISS index",
)
print(f"Done! Model available at: https://huggingface.co/{REPO_ID}")
