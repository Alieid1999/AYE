import shutil
import os
import sys

# Ensure UTF-8 output encoding for console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

root_dir = os.path.dirname(os.path.abspath(__file__))
public_dir = os.path.join(root_dir, 'public')

os.makedirs(public_dir, exist_ok=True)

files_to_sync = ['index.html', 'store_dashboard.html', 'icon.svg', 'manifest.json', 'sw.js']

print("Syncing project files to public directory...")
synced_count = 0

for filename in files_to_sync:
    src = os.path.join(root_dir, filename)
    dst = os.path.join(public_dir, filename)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        size = os.path.getsize(dst)
        print(f"Synced: {filename} -> public/{filename} ({size} bytes)")
        synced_count += 1
    else:
        print(f"Warning: Source file {filename} does not exist.")

print(f"\nSuccessfully synced {synced_count} files to public directory!")
