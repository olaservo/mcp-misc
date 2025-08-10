#!/usr/bin/env python3
# fetch_issue_list.py
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

def get_oldest_open_issues(repo_path: Path, count: int):
    # grab up to 100 open issues, then sort locally by createdAt ASC
    out = run([
        "gh","issue","list",
        "--state","open",
        "--limit","100",
        "--json","number,title,author,createdAt,url,labels"
    ], cwd=repo_path)
    issues = json.loads(out)
    for issue in issues:
        issue["num"] = int(issue["number"])
        issue["author_login"] = issue["author"]["login"] if issue.get("author") else "unknown"
        issue["created_date"] = issue["createdAt"]
        issue["formatted_date"] = datetime.strptime(issue["created_date"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
        issue["label_names"] = [label["name"] for label in issue.get("labels", [])]
    issues.sort(key=lambda i: i["created_date"])   # oldest first
    return issues[:count]

def prompt_issue_selection(issue):
    n = issue["num"]
    t = issue["title"]
    a = issue["author_login"]
    d = issue["formatted_date"]
    labels = ", ".join(issue["label_names"]) if issue["label_names"] else "no labels"
    print(f"  #{n}  {t}  (@{a})  opened {d}  [{labels}]")
    while True:
        ans = input("Include this issue? [y]es / [n]o / [a]ll remaining / [q]uit: ").strip().lower()
        if ans in ("y", "n", "a", "q"):
            return ans
        print("Please enter y/n/a/q.")

def save_issue_list(issues, output_file: Path, repo_path: Path):
    # Create output directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "repo_path": str(repo_path),
        "repo_url": DEFAULT_REPO_URL,
        "fetched_at": datetime.now().isoformat(),
        "issues": issues
    }
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser(
        description="Fetch oldest N issues and save details to a JSON file."
    )
    parser.add_argument(
        "--repo-path",
        default=None,
        help="Path to repo root (default: clones/uses modelcontextprotocol/inspector)",
    )
    parser.add_argument(
        "--count", type=int, default=20, help="How many oldest open issues to fetch (default: 20)"
    )
    script_dir = Path(__file__).parent
    default_output = script_dir / "output" / "issue_list.json"
    parser.add_argument(
        "--output", default=str(default_output), help=f"Output JSON file (default: {default_output})"
    )
    parser.add_argument(
        "--auto", action="store_true", help="Automatically include all fetched issues without prompting"
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

    issues = get_oldest_open_issues(repo, args.count)
    if not issues:
        print("No open issues found.")
        return

    print(f"Found {len(issues)} oldest open issues:")
    
    # Interactive selection or auto-include
    selected_issues = []
    if args.auto:
        selected_issues = issues
        for issue in issues:
            labels = ", ".join(issue["label_names"]) if issue["label_names"] else "no labels"
            print(f"  #{issue['num']}  {issue['title']}  (@{issue['author_login']})  opened {issue['formatted_date']}  [{labels}]")
    else:
        apply_all = False
        for issue in issues:
            if not apply_all:
                choice = prompt_issue_selection(issue)
                if choice == "q":
                    break
                elif choice == "a":
                    apply_all = True
                    selected_issues.append(issue)
                elif choice == "y":
                    selected_issues.append(issue)
                elif choice == "n":
                    continue
            else:
                selected_issues.append(issue)

    if not selected_issues:
        print("No issues selected.")
        return

    output_file = Path(args.output)
    save_issue_list(selected_issues, output_file, repo)
    
    print(f"\nSelected {len(selected_issues)} issues and saved to {output_file}")

if __name__ == "__main__":
    main()