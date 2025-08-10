#!/usr/bin/env python3
# checkout_issues.py
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

def parse_issue_url(url: str):
    """Parse a GitHub issue URL and return (owner, repo, issue_number)."""
    pattern = r'https://github\.com/([^/]+)/([^/]+)/issues/(\d+)'
    match = re.match(pattern, url.strip())
    if not match:
        raise ValueError(f"Invalid GitHub issue URL format: {url}")
    return match.group(1), match.group(2), int(match.group(3))

def fetch_issue_from_github(owner: str, repo: str, issue_num: int):
    """Fetch minimal issue details from GitHub using gh CLI."""
    # Use gh CLI to get just the basic info needed for the agent
    result = run([
        "gh", "issue", "view", str(issue_num),
        "--repo", f"{owner}/{repo}",
        "--json", "number,url"
    ])
    
    import json
    issue_data = json.loads(result)
    
    # Return minimal data - agent will fetch its own details
    formatted_issue = {
        "num": issue_data["number"],
        "html_url": issue_data["url"]
    }
    
    return formatted_issue

def load_issue_list(input_file: Path):
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

def create_issue_details_md(wt_dir: Path, issue: dict):
    """Create .claude/agents/issue-investigator.md file in the worktree with minimal issue info."""
    claude_dir = wt_dir / ".claude" / "agents"
    claude_dir.mkdir(parents=True, exist_ok=True)
    issue_details_path = claude_dir / "issue-investigator.md"
    
    # Get the repo info from the URL for gh CLI commands
    url = issue.get('html_url', '')
    repo_path = ""
    if url and 'github.com' in url:
        # Extract owner/repo from URL like https://github.com/owner/repo/issues/123
        parts = url.split('github.com/')[1].split('/')
        if len(parts) >= 2:
            repo_path = f"{parts[0]}/{parts[1]}"
    
    # Create minimal agent instructions that fetch details themselves
    content = f"""# Issue Investigator Agent

You are an issue investigation agent for **Issue #{issue['num']}**.

## Your Mission

1. **Fetch full issue details** - Get complete information about this issue
2. **Check for existing PRs** - See if someone is already working on this
3. **Check for duplicates** - Search for similar issues
4. **Investigate the problem** - Understand the root cause by examining code
5. **Propose a solution** - Come up with a concrete implementation plan
6. **Document findings** - Record your analysis in the Investigation Notes section

## Quick Reference
- **Issue Number:** #{issue['num']}
- **Repository:** {repo_path}
- **URL:** {issue.get('html_url', 'N/A')}

## Step 1: Fetch Complete Issue Details

Start by getting full details about this issue:

```bash
gh issue view {issue['num']} --repo {repo_path} --json number,title,body,author,createdAt,updatedAt,labels,assignees,state,url,milestone,reactionGroups,comments
```

This will give you:
- Full title and description
- All comments and discussion
- Labels, assignees, milestone
- Creation and update dates
- Reactions and engagement

## Step 2: Check for Existing PRs

Check if there are any open PRs that might address this issue:

```bash
gh pr list --search "#{issue['num']}" --state open --repo {repo_path}
gh pr list --state open --repo {repo_path} | head -20
```

## Step 3: Search for Duplicates

Search for similar issues (you'll refine search terms after reading the issue):

```bash
gh issue list --search "keywords from title" --state all --repo {repo_path}
gh issue list --state closed --repo {repo_path} | head -20
```

## Step 4: Code Investigation

After understanding the issue:
- Use file search tools to locate relevant code
- Examine the current implementation
- Identify the root cause
- Look for related functionality or previous fixes

## Step 5: Solution Design & Implementation Planning

- Plan your approach
- Consider backward compatibility
- Design tests
- Create implementation steps

## Investigation Notes

### Issue Details
<!-- Paste the full issue details from gh issue view here -->

### PR Check Results
<!-- Results from PR searches -->

### Duplicate Analysis
<!-- Results from duplicate searches -->

### Code Analysis
<!-- File locations, code snippets, current implementation understanding -->

### Root Cause Analysis
<!-- Your understanding of why this issue occurs -->

### Proposed Solution
<!-- Detailed implementation plan -->

### Implementation Steps
<!-- Step-by-step plan with specific file changes -->

### Testing Plan
<!-- How to verify the fix works -->

"""
    
    with open(issue_details_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Created issue-investigator.md in {claude_dir}")

def new_worktree_for_issue(repo_path: Path, issue_num: int, issue_data: dict = None):
    """Create a new worktree for working on an issue."""
    branch_name = f"issue-{issue_num}"
    wt_dir = repo_path / ".worktrees" / f"issue-{issue_num}"
    
    # Check if worktree already exists in git's worktree list
    worktree_list = run(["git", "worktree", "list", "--porcelain"], cwd=repo_path)
    existing_worktree = None
    for line in worktree_list.splitlines():
        if line.startswith("worktree ") and f"issue-{issue_num}" in line:
            existing_worktree = Path(line.split(" ", 1)[1])
            break
    
    if existing_worktree:
        print(f"Worktree for issue #{issue_num} already exists at {existing_worktree}")
        # Copy tasks.json to the existing worktree
        copy_vscode_tasks(repo_path, existing_worktree)
        # Create/update issue-investigator.md if issue data is provided
        if issue_data:
            create_issue_details_md(existing_worktree, issue_data)
        return existing_worktree
    
    # Create a new branch from main/master for the issue
    main_branch = "main"
    try:
        run(["git", "rev-parse", "--verify", "main"], cwd=repo_path)
    except RuntimeError:
        try:
            run(["git", "rev-parse", "--verify", "master"], cwd=repo_path)
            main_branch = "master"
        except RuntimeError:
            sys.exit("Could not find main or master branch")
    
    # Remove existing worktree if it exists (orphaned directory)
    if wt_dir.exists():
        try:
            run(["git", "worktree", "remove", str(wt_dir)], cwd=repo_path)
        except RuntimeError:
            # If removal fails, try to prune and remove manually
            run(["git", "worktree", "prune"], cwd=repo_path)
            if wt_dir.exists():
                shutil.rmtree(wt_dir)
    
    # Delete existing branch if it exists
    try:
        run(["git", "branch", "-D", branch_name], cwd=repo_path)
    except RuntimeError:
        pass  # Branch doesn't exist, that's fine
    
    # Create new worktree with a new branch
    run(["git", "worktree", "add", "-b", branch_name, str(wt_dir), main_branch], cwd=repo_path)
    
    # Copy tasks.json to the worktree
    copy_vscode_tasks(repo_path, wt_dir)
    
    # Create issue-investigator.md if issue data is provided
    if issue_data:
        create_issue_details_md(wt_dir, issue_data)
    
    return wt_dir

def open_in_vscode(path: Path, code_binary: str):
    run([code_binary, "-n", "--window-state", "maximized", str(path)], check=True, capture=False)

def prompt_choice(issue):
    n = issue["num"]
    url = issue.get("html_url", "N/A")
    print(f"  #{n} - {url}")
    while True:
        ans = input("Create worktree for this issue? [y]es / [n]o / [a]ll remaining / [q]uit: ").strip().lower()
        if ans in ("y", "n", "a", "q"):
            return ans
        print("Please enter y/n/a/q.")

def main():
    parser = argparse.ArgumentParser(
        description="Create worktrees for issues from a saved issue list file or a single GitHub issue URL."
    )
    script_dir = Path(__file__).parent
    default_input = script_dir / "output" / "issue_list.json"
    parser.add_argument(
        "input", nargs='?', default=str(default_input), 
        help=f"JSON file containing issue details or GitHub issue URL (default: {default_input})"
    )
    parser.add_argument(
        "--issue-url", help="GitHub issue URL to create worktree for (alternative to input file)"
    )
    parser.add_argument(
        "--max-checkout", type=int, default=4, help="Max number of issues to create worktrees for (default: 4)"
    )
    default_code = "code.cmd" if sys.platform == "win32" else "code"
    parser.add_argument(
        "--code-binary", default=default_code, help=f"VS Code binary name (default: {default_code})"
    )
    parser.add_argument(
        "--auto", action="store_true", help="Automatically create worktrees up to max-checkout issues without prompting"
    )
    default_repo_path = r"C:\Users\johnn\OneDrive\Documents\GitHub\olaservo\inspector"
    parser.add_argument(
        "--repo-path", 
        default=default_repo_path,
        help="Path to the git repository (default: inspector repo)"
    )
    args = parser.parse_args()

    for tool in ("git", "gh", args.code_binary):
        require_tool(tool)

    repo_path = Path(args.repo_path)
    
    # Determine if we're using an issue URL or input file
    issue_url = args.issue_url
    if not issue_url:
        # Check if the input argument looks like a URL
        if args.input.startswith("https://github.com/"):
            issue_url = args.input
        
    if issue_url:
        # Handle single issue URL
        try:
            owner, repo_name, issue_num = parse_issue_url(issue_url)
            
            # Fetch basic issue data from GitHub using gh CLI
            issue_data = fetch_issue_from_github(owner, repo_name, issue_num)
            issues = [issue_data]
            data = {"issues": issues, "fetched_at": f"GitHub via gh CLI at {datetime.now().isoformat()}"}
        except ValueError as e:
            sys.exit(f"Error parsing issue URL: {e}")
    else:
        # Handle input file
        input_file = Path(args.input)
        if not input_file.exists():
            sys.exit(f"Input file not found: {input_file}")
        
        data = load_issue_list(input_file)
        issues = data["issues"]

    if not repo_path.exists() or not (repo_path / ".git").exists():
        sys.exit(f"Repo path does not exist or is not a git repo: {repo_path}")

    assert_clean(repo_path)
    ensure_dirs(repo_path)

    if not issues:
        print("No issues found in input file.")
        return

    print(f"Found {len(issues)} issues from {data.get('fetched_at', 'unknown time')}:")
    apply_all = args.auto
    opened = []
    checked_out = 0

    for issue in issues:
        if checked_out >= args.max_checkout:
            print(f"Reached max checkout limit of {args.max_checkout}")
            break

        if not apply_all:
            choice = prompt_choice(issue)
            if choice == "q":
                break
            elif choice == "a":
                apply_all = True
            elif choice == "n":
                continue

        try:
            wt = new_worktree_for_issue(repo_path, issue["num"], issue)
            # Small delay to ensure tasks.json copy is complete before opening VS Code
            time.sleep(0.1)
            open_in_vscode(wt, args.code_binary)
            opened.append(issue["num"])
            checked_out += 1
            print(f"Opened {wt}")
        except Exception as ex:
            print(f"Warning: {ex}", file=sys.stderr)

    if opened:
        print("\nOpened issue worktrees:", ", ".join(f"#{n}" for n in opened))
        print("Cleanup later:")
        print("  git worktree remove .worktrees/issue-<num>")
        print("  git branch -D issue-<num>")
        print("  git worktree prune")

if __name__ == "__main__":
    main()