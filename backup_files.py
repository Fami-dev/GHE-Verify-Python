#!/usr/bin/env python3
"""Backup api_server.py and bot.py before refactoring"""

import shutil
from datetime import datetime

def backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    files_to_backup = [
        "api_server.py",
        "bot.py"
    ]
    
    for filename in files_to_backup:
        src = filename
        dst = f"{filename}.backup_{timestamp}"
        
        try:
            shutil.copy2(src, dst)
            print(f"✅ Backed up: {filename} → {dst}")
        except Exception as e:
            print(f"❌ Failed to backup {filename}: {e}")
    
    print("\n✅ Backup completed!")
    print(f"Timestamp: {timestamp}")

if __name__ == "__main__":
    backup()
