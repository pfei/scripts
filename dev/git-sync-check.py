#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path

def is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()

def check_repo(repo_path: Path):
    print(f"--> checking {repo_path}...")
    # Fetch updates silently
    subprocess.run(["git", "-C", str(repo_path), "fetch"], 
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Check if local is behind remote
    try:
        local = subprocess.check_output(["git", "-C", str(repo_path), "rev-parse", "@"], 
                                        text=True).strip()
        remote = subprocess.check_output(["git", "-C", str(repo_path), "rev-parse", "@{u}"], 
                                         text=True).strip()
        
        if local != remote:
            print(f"🔹 {repo_path.name: <20} : Needs pull")
    except subprocess.CalledProcessError:
        # Ignore repos without an upstream branch
        pass

def main():
    # Use provided path or default to current directory
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    
    if not target_dir.is_dir():
        print(f"Error: {target_dir} is not a valid directory.")
        sys.exit(1)
        
    print(f"🚀 Scanning {target_dir} for outdated repositories...\n")
    
    for entry in target_dir.iterdir():
        if entry.is_dir() and is_git_repo(entry):
            check_repo(entry)
            
    print("\n✅ Scan complete.")

if __name__ == "__main__":
    main()
