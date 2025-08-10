#!/usr/bin/env python3
# checkout_prs.py
# Python 3.9+, requires: git, code (VS Code stable) in PATH

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

def run(cmd, cwd=None, check=True, capture=True):
    result = subprocess.run(
        cmd,
        cwd=cwd,
        shell=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result.stdout if capture else ""

def require_tool(name):
    if shutil.which(name) is None:
        sys.exit(f"Error: '{name}' not found in PATH. Please install or add to PATH.")

def assert_clean(repo_path: Path):
    out = run(["git", "status", "--porcelain"], cwd=repo_path)
    if out.strip():
        # Filter out the .worktrees/ directory that this script creates
        lines = [line for line in out.strip().split('\n') if line and not line.endswith('.worktrees/')]
        if lines:
            sys.exit("Your working tree has uncommitted changes. Commit or stash before running.")

def ensure_dirs(repo_path: Path):
    (repo_path / ".worktrees").mkdir(parents=True, exist_ok=True)

def parse_pr_url(url: str):
    """Parse a GitHub PR URL and return (owner, repo, pr_number)."""
    pattern = r'https://github\.com/([^/]+)/([^/]+)/pull/(\d+)'
    match = re.match(pattern, url.strip())
    if not match:
        raise ValueError(f"Invalid GitHub PR URL format: {url}")
    return match.group(1), match.group(2), int(match.group(3))

def load_pr_list(input_file: Path):
    with open(input_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def copy_vscode_tasks(repo_path: Path, wt_dir: Path):
    """Copy tasks.json from main repo .vscode to worktree if it exists."""
    tasks_src = repo_path / ".vscode" / "tasks.json"
    vscode_dest_dir = wt_dir / ".vscode"
    tasks_dest = vscode_dest_dir / "tasks.json"
    
    if tasks_src.exists():
        vscode_dest_dir.mkdir(exist_ok=True)
        shutil.copy2(tasks_src, tasks_dest)

def new_worktree_for_pr(repo_path: Path, pr_num: int, shallow: bool):
    wt_dir = repo_path / ".worktrees" / f"pr-{pr_num}"
    
    # Check if worktree already exists in git's worktree list
    worktree_list = run(["git", "worktree", "list", "--porcelain"], cwd=repo_path)
    existing_worktree = None
    for line in worktree_list.splitlines():
        if line.startswith("worktree ") and f"pr-{pr_num}" in line:
            existing_worktree = Path(line.split(" ", 1)[1])
            break
    
    if existing_worktree:
        print(f"Worktree for PR #{pr_num} already exists at {existing_worktree}")
        
        # Fetch latest changes for the PR
        refspec = f"pull/{pr_num}/head:pr-{pr_num}"
        fetch_cmd = ["git", "fetch"]
        if shallow:
            fetch_cmd += ["--depth=2"]
        fetch_cmd += ["upstream", refspec, "--update-head-ok"]
        run(fetch_cmd, cwd=repo_path)
        
        # Update the existing worktree to latest PR changes
        print(f"Updating worktree to latest PR #{pr_num} changes...")
        run(["git", "reset", "--hard", f"pr-{pr_num}"], cwd=existing_worktree)
        
        # Copy tasks.json to the existing worktree
        copy_vscode_tasks(repo_path, existing_worktree)
        return existing_worktree
    
    # Fetch the PR if worktree doesn't exist
    refspec = f"pull/{pr_num}/head:pr-{pr_num}"
    fetch_cmd = ["git", "fetch"]
    if shallow:
        fetch_cmd += ["--depth=2"]
    fetch_cmd += ["upstream", refspec, "--update-head-ok"]
    run(fetch_cmd, cwd=repo_path)

    # Clean up any orphaned worktree directories
    if wt_dir.exists():
        run(["git", "worktree", "prune"], cwd=repo_path)
    
    # Create new worktree
    run(["git", "worktree", "add", str(wt_dir), f"pr-{pr_num}"], cwd=repo_path)
    
    # Copy tasks.json to the worktree
    copy_vscode_tasks(repo_path, wt_dir)
    
    return wt_dir

def open_in_vscode(path: Path, code_binary: str):
    run([code_binary, "-n", "--window-state", "maximized", str(path)], check=True, capture=False)

def prompt_choice(pr):
    n = pr["num"]
    t = pr["title"]
    a = pr["author_login"]
    d = pr["formatted_date"]
    print(f"  #{n}  {t}  (@{a})  opened {d}")
    while True:
        ans = input("Open this PR? [y]es / [n]o / [a]ll remaining / [q]uit: ").strip().lower()
        if ans in ("y", "n", "a", "q"):
            return ans
        print("Please enter y/n/a/q.")

def main():
    parser = argparse.ArgumentParser(
        description="Check out PRs from a saved PR list file or a single GitHub PR URL."
    )
    script_dir = Path(__file__).parent
    default_input = script_dir / "output" / "pr_list.json"
    parser.add_argument(
        "input", nargs='?', default=str(default_input), 
        help=f"JSON file containing PR details or GitHub PR URL (default: {default_input})"
    )
    parser.add_argument(
        "--pr-url", help="GitHub PR URL to checkout (alternative to input file)"
    )
    parser.add_argument(
        "--max-checkout", type=int, default=4, help="Max number of PRs to check out locally (default: 4)"
    )
    parser.add_argument(
        "--shallow", action="store_true", help="Use shallow fetch for speed"
    )
    default_code = "code.cmd" if sys.platform == "win32" else "code"
    parser.add_argument(
        "--code-binary", default=default_code, help=f"VS Code binary name (default: {default_code})"
    )
    parser.add_argument(
        "--auto", action="store_true", help="Automatically checkout up to max-checkout PRs without prompting"
    )
    parser.add_argument(
        "--repo-path", 
        default=r"C:\Users\johnn\OneDrive\Documents\GitHub\olaservo\inspector",
        help="Path to the git repository (default: inspector repo)"
    )
    args = parser.parse_args()

    for tool in ("git", args.code_binary):
        require_tool(tool)

    repo_path = Path(args.repo_path)
    
    # Determine if we're using a PR URL or input file
    pr_url = args.pr_url
    if not pr_url:
        # Check if the input argument looks like a URL
        if args.input.startswith("https://github.com/"):
            pr_url = args.input
        
    if pr_url:
        # Handle single PR URL
        try:
            owner, repo_name, pr_num = parse_pr_url(pr_url)
            # Create a single PR data structure
            prs = [{
                "num": pr_num,
                "title": f"PR #{pr_num}",
                "author_login": "unknown",
                "formatted_date": "unknown"
            }]
            data = {"prs": prs, "fetched_at": "single PR URL"}
            
            # Update repo path based on parsed URL if not explicitly set
            if args.repo_path == r"C:\Users\johnn\OneDrive\Documents\GitHub\olaservo\inspector":
                # Use default path structure for the parsed repo
                repo_path = Path(f"C:\\Users\\johnn\\OneDrive\\Documents\\GitHub\\{owner}\\{repo_name}")
        except ValueError as e:
            sys.exit(f"Error parsing PR URL: {e}")
    else:
        # Handle input file
        input_file = Path(args.input)
        if not input_file.exists():
            sys.exit(f"Input file not found: {input_file}")
        
        data = load_pr_list(input_file)
        prs = data["prs"]

    if not repo_path.exists() or not (repo_path / ".git").exists():
        sys.exit(f"Repo path does not exist or is not a git repo: {repo_path}")

    assert_clean(repo_path)
    ensure_dirs(repo_path)

    if not prs:
        print("No PRs found in input file.")
        return

    print(f"Found {len(prs)} PRs from {data.get('fetched_at', 'unknown time')}:")
    apply_all = args.auto
    opened = []
    checked_out = 0

    for pr in prs:
        if checked_out >= args.max_checkout:
            print(f"Reached max checkout limit of {args.max_checkout}")
            break

        if not apply_all:
            choice = prompt_choice(pr)
            if choice == "q":
                break
            elif choice == "a":
                apply_all = True
            elif choice == "n":
                continue

        try:
            wt = new_worktree_for_pr(repo_path, pr["num"], args.shallow)
            # Small delay to ensure tasks.json copy is complete before opening VS Code
            time.sleep(0.1)
            open_in_vscode(wt, args.code_binary)
            opened.append(pr["num"])
            checked_out += 1
            print(f"Opened {wt}")
        except Exception as ex:
            print(f"Warning: {ex}", file=sys.stderr)

    if opened:
        print("\nOpened PR windows:", ", ".join(f"#{n}" for n in opened))
        print("Cleanup later:")
        print("  git worktree remove .worktrees/pr-<num>")
        print("  git branch -D pr-<num>")
        print("  git worktree prune")

if __name__ == "__main__":
    main()