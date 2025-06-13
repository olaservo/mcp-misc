#!/usr/bin/env python3
"""
Script to comment on and close original PRs that were merged into a combined PR.

This script:
1. Parses a combined PR description to extract original PR numbers
2. For each original PR:
   - Adds a comment thanking the contributor and linking to the combined PR
   - Closes the PR without merging it
3. Includes dry-run mode for testing
4. Logs all actions taken

Usage:
    # Dry run (recommended first step)
    python 3_close_original_prs.py --combined-pr-url https://github.com/modelcontextprotocol/servers/pull/2007 --dry-run
    
    # Execute for real (will prompt for confirmation per batch)
    python 3_close_original_prs.py --combined-pr-url https://github.com/modelcontextprotocol/servers/pull/2007
    
    # Skip confirmation prompts (for automation)
    python 3_close_original_prs.py --combined-pr-url https://github.com/modelcontextprotocol/servers/pull/2007 --auto-confirm
"""

import subprocess
import json
import re
import sys
import argparse
import os
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime

def extract_pr_number_from_url(url: str) -> Optional[int]:
    """Extract PR number from GitHub PR URL."""
    match = re.search(r'/pull/(\d+)', url)
    if match:
        return int(match.group(1))
    return None

def fetch_pr_description(pr_url: str) -> Optional[str]:
    """Fetch PR description from GitHub API."""
    pr_number = extract_pr_number_from_url(pr_url)
    if not pr_number:
        print(f"Error: Could not extract PR number from URL: {pr_url}")
        return None
    
    try:
        print(f"Fetching PR description for #{pr_number}...")
        
        cmd = [
            'gh', 'api', f'repos/modelcontextprotocol/servers/pulls/{pr_number}',
            '--jq', '.body'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
        
        if not result.stdout or not result.stdout.strip():
            print(f"Warning: Empty PR description for #{pr_number}")
            return None
            
        return result.stdout.strip()
        
    except subprocess.CalledProcessError as e:
        print(f"Error fetching PR description: {e}")
        print(f"stderr: {e.stderr}")
        return None

def parse_pr_description(description: str) -> List[Dict[str, str]]:
    """Parse PR description to extract original PR information."""
    # Pattern to match: - **[Server Name](url)** ([PR #1234](pr_url))
    pattern = r'- \*\*\[([^\]]+)\]\([^)]+\)\*\* \(\[PR #(\d+)\]\([^)]+\)\)'
    
    matches = re.findall(pattern, description)
    
    prs = []
    for match in matches:
        server_name, pr_number = match
        prs.append({
            'server_name': server_name.strip(),
            'pr_number': int(pr_number)
        })
    
    return prs


def check_pr_status(pr_number: int) -> Optional[Dict]:
    """Check the current status of a PR."""
    try:
        cmd = [
            'gh', 'api', f'repos/modelcontextprotocol/servers/pulls/{pr_number}',
            '--jq', '{state: .state, merged: .merged, title: .title}'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
        
        if not result.stdout or not result.stdout.strip():
            return None
            
        return json.loads(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"Error checking PR #{pr_number} status: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing PR status response: {e}")
        return None

def add_comment_to_pr(pr_number: int, combined_pr_url: str, dry_run: bool = False) -> bool:
    """Add a comment to the original PR."""
    comment_body = f"""Thanks for your contribution to the servers list. This has been merged in this combined PR: {combined_pr_url}

This is a new process we're trying out, so if you see any issues feel free to re-open the PR and tag me."""
    
    if dry_run:
        print(f"    [DRY RUN] Would add comment to PR #{pr_number}:")
        print(f"    Comment: {comment_body}")
        return True
    
    try:
        cmd = [
            'gh', 'api', f'repos/modelcontextprotocol/servers/issues/{pr_number}/comments',
            '-X', 'POST',
            '-f', f'body={comment_body}'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
        print(f"    ✓ Comment added to PR #{pr_number}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"    ✗ Error adding comment to PR #{pr_number}: {e}")
        if e.stderr:
            print(f"    stderr: {e.stderr}")
        return False

def close_pr(pr_number: int, dry_run: bool = False) -> bool:
    """Close the PR without merging."""
    if dry_run:
        print(f"    [DRY RUN] Would close PR #{pr_number}")
        return True
    
    try:
        cmd = [
            'gh', 'api', f'repos/modelcontextprotocol/servers/pulls/{pr_number}',
            '-X', 'PATCH',
            '-f', 'state=closed'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
        print(f"    ✓ PR #{pr_number} closed")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"    ✗ Error closing PR #{pr_number}: {e}")
        if e.stderr:
            print(f"    stderr: {e.stderr}")
        return False

def process_pr(pr_info: Dict, combined_pr_url: str, dry_run: bool = False) -> Dict:
    """Process a single PR (comment and close)."""
    pr_number = pr_info['pr_number']
    server_name = pr_info['server_name']
    
    print(f"  Processing PR #{pr_number}: {server_name}")
    
    # Check PR status first
    status = check_pr_status(pr_number)
    if not status:
        return {
            'pr_number': pr_number,
            'success': False,
            'error': 'Could not fetch PR status',
            'skipped': False
        }
    
    if status['state'] == 'closed':
        print(f"    ⚠ PR #{pr_number} is already closed, skipping")
        return {
            'pr_number': pr_number,
            'success': True,
            'error': None,
            'skipped': True,
            'reason': 'Already closed'
        }
    
    if status.get('merged', False):
        print(f"    ⚠ PR #{pr_number} is already merged, skipping")
        return {
            'pr_number': pr_number,
            'success': True,
            'error': None,
            'skipped': True,
            'reason': 'Already merged'
        }
    
    # Add comment
    comment_success = add_comment_to_pr(pr_number, combined_pr_url, dry_run)
    if not comment_success and not dry_run:
        return {
            'pr_number': pr_number,
            'success': False,
            'error': 'Failed to add comment',
            'skipped': False
        }
    
    # Small delay between comment and close
    if not dry_run:
        time.sleep(1)
    
    # Close PR
    close_success = close_pr(pr_number, dry_run)
    if not close_success and not dry_run:
        return {
            'pr_number': pr_number,
            'success': False,
            'error': 'Failed to close PR (comment may have been added)',
            'skipped': False
        }
    
    return {
        'pr_number': pr_number,
        'success': True,
        'error': None,
        'skipped': False
    }

def process_pr_batch(prs: List[Dict], combined_pr_url: str, batch_num: int, total_batches: int, 
                    dry_run: bool = False, auto_confirm: bool = False) -> List[Dict]:
    """Process a batch of PRs with confirmation."""
    print(f"\n=== Batch {batch_num}/{total_batches} ({len(prs)} PRs) ===")
    
    # Show preview
    print("PRs in this batch:")
    for pr in prs:
        print(f"  - PR #{pr['pr_number']}: {pr['server_name']}")
    
    # Ask for confirmation (unless auto-confirm or dry-run)
    if not auto_confirm and not dry_run:
        response = input(f"\nProcess this batch of {len(prs)} PRs? (y/n): ").strip().lower()
        if response != 'y':
            print("Batch skipped by user")
            return []
    elif dry_run:
        print("\n[DRY RUN] Processing batch...")
    else:
        print(f"\n[AUTO-CONFIRM] Processing batch...")
    
    # Process each PR in the batch
    results = []
    for i, pr in enumerate(prs, 1):
        print(f"\n[{i}/{len(prs)}] ", end="")
        result = process_pr(pr, combined_pr_url, dry_run)
        results.append(result)
        
        # Rate limiting between PRs
        if not dry_run and i < len(prs):
            time.sleep(2)
    
    return results

def create_batches(prs: List[Dict], batch_size: int = 10) -> List[List[Dict]]:
    """Split PRs into batches."""
    batches = []
    for i in range(0, len(prs), batch_size):
        batches.append(prs[i:i + batch_size])
    return batches

def log_results(results: List[Dict], combined_pr_url: str, dry_run: bool):
    """Log the results to a file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(output_dir, f"close_prs_log_{timestamp}.txt")
    
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"Close Original PRs Log\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        f.write(f"Combined PR URL: {combined_pr_url}\n")
        f.write(f"Dry Run: {dry_run}\n")
        f.write(f"Total PRs Processed: {len(results)}\n\n")
        
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        skipped = [r for r in results if r.get('skipped', False)]
        
        f.write(f"Summary:\n")
        f.write(f"  Successful: {len(successful)}\n")
        f.write(f"  Failed: {len(failed)}\n")
        f.write(f"  Skipped: {len(skipped)}\n\n")
        
        f.write("Detailed Results:\n")
        f.write("=" * 50 + "\n")
        
        for result in results:
            f.write(f"PR #{result['pr_number']}: ")
            if result['success']:
                if result.get('skipped'):
                    f.write(f"SKIPPED ({result.get('reason', 'Unknown reason')})\n")
                else:
                    f.write("SUCCESS\n")
            else:
                f.write(f"FAILED - {result.get('error', 'Unknown error')}\n")
        
        f.write("\n")
    
    print(f"\nResults logged to: {log_file}")

def main():
    """Main function to orchestrate the PR closing process."""
    parser = argparse.ArgumentParser(description='Comment on and close original PRs that were merged into a combined PR')
    
    # Required combined PR URL
    parser.add_argument('--combined-pr-url', required=True,
                       help='URL of the combined PR to fetch description from')
    
    # Options
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    parser.add_argument('--auto-confirm', action='store_true',
                       help='Skip confirmation prompts (use with caution)')
    parser.add_argument('--batch-size', type=int, default=10,
                       help='Number of PRs to process per batch (default: 10)')
    
    args = parser.parse_args()
    
    print("=== Close Original PRs Script ===")
    print(f"Combined PR link: {args.combined_pr_url}")
    print(f"Batch size: {args.batch_size}")
    print(f"Dry run: {args.dry_run}")
    print(f"Auto confirm: {args.auto_confirm}")
    print()
    
    # Get PR description from GitHub
    print("Fetching PR description from GitHub...")
    description = fetch_pr_description(args.combined_pr_url)
    
    if not description:
        print("Error: Could not load PR description")
        sys.exit(1)
    
    # Parse PR information
    print("Parsing PR description...")
    prs = parse_pr_description(description)
    
    if not prs:
        print("No PRs found in description")
        sys.exit(1)
    
    print(f"Found {len(prs)} PRs to process")
    
    # Show preview of first few PRs
    print("\nFirst 5 PRs found:")
    for pr in prs[:5]:
        print(f"  - PR #{pr['pr_number']}: {pr['server_name']}")
    if len(prs) > 5:
        print(f"  ... and {len(prs) - 5} more")
    
    # Create batches
    batches = create_batches(prs, args.batch_size)
    print(f"\nSplit into {len(batches)} batches of up to {args.batch_size} PRs each")
    
    # Final confirmation for non-dry-run
    if not args.dry_run and not args.auto_confirm:
        print(f"\n⚠ WARNING: This will comment on and close {len(prs)} PRs!")
        response = input("Are you sure you want to continue? (y/n): ").strip().lower()
        if response != 'y':
            print("Operation cancelled by user")
            sys.exit(0)
    
    # Process batches
    all_results = []
    
    for batch_num, batch in enumerate(batches, 1):
        batch_results = process_pr_batch(
            batch, args.combined_pr_url, batch_num, len(batches), 
            args.dry_run, args.auto_confirm
        )
        all_results.extend(batch_results)
        
        # Delay between batches (except for last batch)
        if batch_num < len(batches) and not args.dry_run:
            print(f"\nWaiting 5 seconds before next batch...")
            time.sleep(5)
    
    # Final summary
    successful = [r for r in all_results if r['success']]
    failed = [r for r in all_results if not r['success']]
    skipped = [r for r in all_results if r.get('skipped', False)]
    
    print(f"\n=== Final Summary ===")
    print(f"Total PRs: {len(prs)}")
    print(f"Processed: {len(all_results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"Skipped: {len(skipped)}")
    
    if failed:
        print(f"\nFailed PRs:")
        for result in failed:
            print(f"  - PR #{result['pr_number']}: {result.get('error', 'Unknown error')}")
    
    if skipped:
        print(f"\nSkipped PRs:")
        for result in skipped:
            print(f"  - PR #{result['pr_number']}: {result.get('reason', 'Unknown reason')}")
    
    # Log results
    if all_results:
        log_results(all_results, args.combined_pr_url, args.dry_run)
    
    if args.dry_run:
        print(f"\n✓ Dry run completed - no actual changes made")
    else:
        print(f"\n✓ Operation completed")

if __name__ == "__main__":
    main()
