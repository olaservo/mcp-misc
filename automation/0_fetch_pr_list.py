#!/usr/bin/env python3
# fetch_pr_list.py
# Python 3.9+, requires: git, gh in PATH

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime

DEFAULT_REPO_URL = "https://github.com/modelcontextprotocol/inspector"
DEFAULT_REPO_NAME = "inspector"

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

def clone_if_missing(base_path: Path):
    repo_path = base_path / DEFAULT_REPO_NAME
    if not repo_path.exists():
        print(f"Cloning {DEFAULT_REPO_URL} into {repo_path} ...")
        run(["git", "clone", DEFAULT_REPO_URL], cwd=base_path)
    return repo_path.resolve()

def get_oldest_open_prs(repo_path: Path, count: int):
    # grab up to 100 open PRs, then sort locally by createdAt ASC
    out = run([
        "gh","pr","list",
        "--state","open",
        "--limit","100",
        "--json","number,title,author,createdAt,url"
    ], cwd=repo_path)
    prs = json.loads(out)
    for pr in prs:
        pr["num"] = int(pr["number"])
        pr["author_login"] = pr["author"]["login"] if pr.get("author") else "unknown"
        pr["created_date"] = pr["createdAt"]
        pr["formatted_date"] = datetime.strptime(pr["created_date"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
    prs.sort(key=lambda p: p["created_date"])   # oldest first
    return prs[:count]

def prompt_pr_selection(pr):
    n = pr["num"]
    t = pr["title"]
    a = pr["author_login"]
    d = pr["formatted_date"]
    print(f"  #{n}  {t}  (@{a})  opened {d}")
    while True:
        ans = input("Include this PR? [y]es / [n]o / [a]ll remaining / [q]uit: ").strip().lower()
        if ans in ("y", "n", "a", "q"):
            return ans
        print("Please enter y/n/a/q.")

def save_pr_list(prs, output_file: Path, repo_path: Path):
    # Create output directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "repo_path": str(repo_path),
        "repo_url": DEFAULT_REPO_URL,
        "fetched_at": datetime.now().isoformat(),
        "prs": prs
    }
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser(
        description="Fetch oldest N PRs and save details to a JSON file."
    )
    parser.add_argument(
        "--repo-path",
        default=None,
        help="Path to repo root (default: clones/uses modelcontextprotocol/inspector)",
    )
    parser.add_argument(
        "--count", type=int, default=20, help="How many oldest open PRs to fetch (default: 20)"
    )
    script_dir = Path(__file__).parent
    default_output = script_dir / "output" / "pr_list.json"
    parser.add_argument(
        "--output", default=str(default_output), help=f"Output JSON file (default: {default_output})"
    )
    parser.add_argument(
        "--auto", action="store_true", help="Automatically include all fetched PRs without prompting"
    )
    args = parser.parse_args()

    for tool in ("git", "gh"):
        require_tool(tool)

    if args.repo_path:
        repo = Path(args.repo_path).resolve()
        if not (repo / ".git").exists():
            sys.exit(f"Not a git repo: {repo}")
    else:
        # Default: sibling folder in current directory
        repo = clone_if_missing(Path.cwd())

    try:
        run(["gh", "auth", "status"], cwd=repo)
    except RuntimeError:
        sys.exit("`gh auth status` failed. Run `gh auth login` and try again.")

    prs = get_oldest_open_prs(repo, args.count)
    if not prs:
        print("No open PRs found.")
        return

    print(f"Found {len(prs)} oldest open PRs:")
    
    # Interactive selection or auto-include
    selected_prs = []
    if args.auto:
        selected_prs = prs
        for pr in prs:
            print(f"  #{pr['num']}  {pr['title']}  (@{pr['author_login']})  opened {pr['formatted_date']}")
    else:
        apply_all = False
        for pr in prs:
            if not apply_all:
                choice = prompt_pr_selection(pr)
                if choice == "q":
                    break
                elif choice == "a":
                    apply_all = True
                    selected_prs.append(pr)
                elif choice == "y":
                    selected_prs.append(pr)
                elif choice == "n":
                    continue
            else:
                selected_prs.append(pr)

    if not selected_prs:
        print("No PRs selected.")
        return

    output_file = Path(args.output)
    save_pr_list(selected_prs, output_file, repo)
    
    print(f"\nSelected {len(selected_prs)} PRs and saved to {output_file}")

if __name__ == "__main__":
    main()