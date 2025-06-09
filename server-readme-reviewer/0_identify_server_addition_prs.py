#!/usr/bin/env python3
"""
Script to identify open PRs that are adding servers to the README and output them in batched CSV files.

This script:
- Fetches open PRs from the modelcontextprotocol/servers repository using proper pagination
- Identifies which PRs are adding a single server entry to the README
- Categorizes servers using label-based logic with fallback:
  * If PR has 'add-official-server' label → categorized as 'official'
  * If PR has 'add-community-server' label → categorized as 'community'
  * Otherwise, uses fallback logic (icons or 'official' in title → official, else community)
- Automatically fixes missing alt text in img tags using the server name
- Outputs results to batched CSV files (sorted alphabetically by server name)

Usage:
    # Default usage with batch size 10
    python 0_identify_server_addition_prs.py
    
    # Custom batch size
    python 0_identify_server_addition_prs.py --batch-size 5
    
    # Control pagination
    python 0_identify_server_addition_prs.py --max-pages 5 --per-page 30
"""

import subprocess
import json
import csv
import re
import sys
import argparse
import os
from typing import List, Dict, Optional
import time

def parse_img_tag(img_tag_str: str) -> Dict[str, str]:
    """Parse an img tag string and return its attributes as a dictionary."""
    attributes = {}
    
    # Remove the opening and closing tags
    content = img_tag_str.strip()
    if content.startswith('<img'):
        content = content[4:]  # Remove '<img'
    if content.endswith('>'):
        content = content[:-1]  # Remove '>'
    
    # Parse attributes using regex
    attr_pattern = r'(\w+)=(["\'])([^"\']*)\2'
    matches = re.findall(attr_pattern, content)
    
    for attr_name, quote_char, attr_value in matches:
        attributes[attr_name.lower()] = attr_value
    
    return attributes

def reconstruct_img_tag(attributes: Dict[str, str]) -> str:
    """Reconstruct an img tag from attributes dictionary."""
    attr_strings = []
    
    # Maintain a consistent order for attributes
    ordered_attrs = ['src', 'alt', 'width', 'height', 'class', 'style']
    
    # Add ordered attributes first
    for attr in ordered_attrs:
        if attr in attributes:
            attr_strings.append(f'{attr}="{attributes[attr]}"')
    
    # Add any remaining attributes
    for attr, value in attributes.items():
        if attr not in ordered_attrs:
            attr_strings.append(f'{attr}="{value}"')
    
    return f'<img {" ".join(attr_strings)}>'

def fix_img_alt_text(line: str, server_name: str) -> str:
    """Fix missing or inadequate alt text in img tags using the server name."""
    # Find img tags in the line
    img_pattern = r'<img[^>]*>'
    img_matches = re.finditer(img_pattern, line)
    
    fixed_line = line
    offset = 0  # Track position changes due to replacements
    
    for match in img_matches:
        original_img = match.group(0)
        start_pos = match.start() + offset
        end_pos = match.end() + offset
        
        # Parse the img tag attributes
        attributes = parse_img_tag(original_img)
        
        # Check if alt attribute is missing or empty
        alt_text = attributes.get('alt', '').strip()
        
        if not alt_text:
            # Add alt text using the server name
            attributes['alt'] = server_name
            
            # Reconstruct the img tag
            new_img = reconstruct_img_tag(attributes)
            
            # Replace in the line
            fixed_line = fixed_line[:start_pos] + new_img + fixed_line[end_pos:]
            
            # Update offset for next replacements
            offset += len(new_img) - len(original_img)
    
    return fixed_line

def extract_server_info_from_line(line: str) -> Optional[Dict[str, str]]:
    """Extract server information from a README line and fix alt text if needed."""
    # Pattern for server entries with icons
    icon_pattern = r'^\s*-\s+(<img[^>]*>)\s+\*\*\[([^\]]+)\]\(([^)]+)\)\*\*\s*-\s*(.+)$'
    
    # Pattern for server entries without icons
    no_icon_pattern = r'^\s*-\s+\*\*\[([^\]]+)\]\(([^)]+)\)\*\*\s*-\s*(.+)$'
    
    # Try icon pattern first
    icon_match = re.match(icon_pattern, line.strip())
    if icon_match:
        img_tag = icon_match.group(1)
        server_name = icon_match.group(2)
        server_url = icon_match.group(3)
        description = icon_match.group(4)
        
        # Fix alt text in the img tag
        fixed_img_tag = fix_img_alt_text(img_tag, server_name)
        
        # Reconstruct the complete line with fixed img tag
        fixed_line = f"- {fixed_img_tag} **[{server_name}]({server_url})** - {description}"
        
        return {
            'server_name': server_name,
            'server_url': server_url,
            'description': description,
            'complete_line': fixed_line
        }
    
    # Try no icon pattern
    no_icon_match = re.match(no_icon_pattern, line.strip())
    if no_icon_match:
        server_name = no_icon_match.group(1)
        server_url = no_icon_match.group(2)
        description = no_icon_match.group(3)
        
        return {
            'server_name': server_name,
            'server_url': server_url,
            'description': description,
            'complete_line': line.strip()
        }
    
    return None

def categorize_server(complete_line: str) -> str:
    """Categorize server as 'official' or 'community' based on presence of image tags or 'official' in title."""
    has_icon = '<img' in complete_line
    has_official_in_title = 'official' in complete_line.lower()
    return 'official' if (has_icon or has_official_in_title) else 'community'

def categorize_server_by_labels(pr_labels: List[str], complete_line: str) -> str:
    """
    Categorize server using labels first, then fallback logic.
    
    Args:
        pr_labels: List of label names from the PR
        complete_line: The complete server line for fallback categorization
        
    Returns:
        'official' or 'community'
    """
    # Check for explicit labels first
    if 'add-official-server' in pr_labels:
        return 'official'
    elif 'add-community-server' in pr_labels:
        return 'community'
    
    # Fallback to existing logic
    return categorize_server(complete_line)

def fetch_prs_page(page: int, per_page: int = 20, state: str = 'open') -> List[Dict]:
    """Fetch a single page of PRs using GitHub API."""
    try:
        print(f"  Fetching page {page} ({per_page} PRs per page)...")
        
        cmd = [
            'gh', 'api', 'repos/modelcontextprotocol/servers/pulls',
            '-X', 'GET',
            '-f', 'direction=asc',
            '-f', f'per_page={per_page}',
            '-f', f'state={state}',
            '-f', f'page={page}',
            '--jq', '[.[] | {number: .number, title: .title, user: .user.login, labels: [.labels[].name], body: .body}]'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
        
        if not result.stdout or not result.stdout.strip():
            return []
            
        prs = json.loads(result.stdout)
        print(f"    Retrieved {len(prs)} PRs from page {page}")
        return prs
        
    except subprocess.CalledProcessError as e:
        print(f"Error calling GitHub API: {e}")
        print(f"stderr: {e.stderr}")
        if "rate limit" in e.stderr.lower():
            print("Rate limit hit. Waiting 60 seconds...")
            time.sleep(60)
            return fetch_prs_page(page, per_page, state)  # Retry
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Raw output: {result.stdout}")
        return []

def fetch_pr_diff(pr_number: int) -> Optional[str]:
    """Fetch the diff for a specific PR."""
    try:
        cmd = [
            'gh', 'api', f'repos/modelcontextprotocol/servers/pulls/{pr_number}',
            '-H', 'Accept: application/vnd.github.v3.diff'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
        return result.stdout
        
    except subprocess.CalledProcessError as e:
        print(f"Error fetching diff for PR #{pr_number}: {e}")
        return None

def fetch_all_prs(state: str = 'open', per_page: int = 20, start_page: int = 1, max_pages: int = None) -> List[Dict]:
    """Fetch all PRs using pagination."""
    all_prs = []
    processed_pr_numbers = set()
    page = start_page
    
    print(f"Starting to fetch all {state} PRs from page {start_page}...")
    print(f"Using {per_page} PRs per page")
    if max_pages:
        print(f"Limited to {max_pages} pages maximum")
    print()
    
    while True:
        if max_pages and (page - start_page + 1) > max_pages:
            print(f"Reached maximum page limit ({max_pages})")
            break
            
        prs = fetch_prs_page(page, per_page, state)
        
        if not prs:
            print(f"No more PRs found on page {page}. Pagination complete.")
            break
        
        # De-duplicate PRs by number
        new_prs = []
        duplicates = 0
        
        for pr in prs:
            pr_number = pr['number']
            if pr_number not in processed_pr_numbers:
                processed_pr_numbers.add(pr_number)
                new_prs.append(pr)
            else:
                duplicates += 1
        
        if duplicates > 0:
            print(f"    Skipped {duplicates} duplicate PRs on page {page}")
        
        all_prs.extend(new_prs)
        print(f"    Added {len(new_prs)} new PRs (Total so far: {len(all_prs)})")
        
        # Small delay to be nice to the API
        time.sleep(0.5)
        page += 1
    
    print(f"\nPagination complete! Fetched {len(all_prs)} unique PRs across {page - start_page} pages")
    return all_prs

def analyze_pr_for_server_addition(pr: Dict) -> Optional[Dict[str, str]]:
    """Analyze a PR to see if it's adding a single server to the README."""
    pr_number = pr['number']
    pr_title = pr['title']
    pr_author = pr['user']
    
    print(f"  Analyzing PR #{pr_number}: {pr_title}")
    
    # Fetch the diff
    diff = fetch_pr_diff(pr_number)
    if not diff:
        print(f"    Could not fetch diff")
        return None
    
    # Look for README.md changes
    if 'README.md' not in diff:
        print(f"    No README.md changes")
        return None
    
    # Split diff into lines and look for additions
    lines = diff.split('\n')
    added_lines = []
    
    for line in lines:
        if line.startswith('+') and not line.startswith('+++'):
            # This is an added line
            added_line = line[1:]  # Remove the '+' prefix
            
            # Check if this looks like a server entry
            server_info = extract_server_info_from_line(added_line)
            if server_info:
                added_lines.append((added_line, server_info))
    
    # We only want PRs that add exactly one server line
    if len(added_lines) != 1:
        if len(added_lines) > 1:
            print(f"    Adding multiple lines ({len(added_lines)}), skipping")
        else:
            print(f"    No server entries found in additions")
        return None
    
    # Check that there are no other significant additions (to avoid PRs that modify multiple lines)
    non_server_additions = 0
    for line in lines:
        if line.startswith('+') and not line.startswith('+++'):
            added_line = line[1:].strip()
            # Skip empty lines and lines that are just whitespace
            if added_line and not extract_server_info_from_line(line[1:]):
                non_server_additions += 1
    
    if non_server_additions > 2:  # Allow for some minor additions like whitespace
        print(f"    Too many non-server additions ({non_server_additions}), skipping")
        return None
    
    original_line, server_info = added_lines[0]
    
    # Use the fixed complete line from server_info (which has alt text fixed)
    complete_line = server_info['complete_line']
    category = categorize_server_by_labels(pr.get('labels', []), complete_line)
    
    print(f"    ✓ Found {category} server addition: {server_info['server_name']}")
    
    return {
        'pr_number': pr_number,
        'pr_title': pr_title,
        'complete_line': complete_line,
        'server_url': server_info['server_url'],
        'server_name': server_info['server_name'],
        'pr_author': pr_author,
        'category': category
    }

def write_csv_file(results: List[Dict], filename: str):
    """Write results to a single CSV file, sorted alphabetically by server name."""
    # Sort results by server_name (case-insensitive)
    sorted_results = sorted(results, key=lambda x: x['server_name'].lower())
    
    print(f"  Sorting {len(results)} entries alphabetically by server name...")
    if results:
        print(f"  First entry after sorting: {sorted_results[0]['server_name']}")
        print(f"  Last entry after sorting: {sorted_results[-1]['server_name']}")
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['PR_Number', 'PR_Title', 'Complete_Line', 'Server_URL', 'Server_Name', 'PR_Author', 'Category']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        
        for result in sorted_results:
            writer.writerow({
                'PR_Number': result['pr_number'],
                'PR_Title': result['pr_title'],
                'Complete_Line': result['complete_line'],
                'Server_URL': result['server_url'],
                'Server_Name': result['server_name'],
                'PR_Author': result['pr_author'],
                'Category': result['category']
            })

def write_batched_results(results: List[Dict], output_prefix: str = 'server_addition_prs', batch_size: int = 10):
    """Write results to batched CSV files, split by category and batch size."""
    if not results:
        print("No server addition PRs found.")
        return
    
    # Get the script directory and create output directory path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'output')
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    print(f"Writing output files to: {output_dir}")
    
    # Separate results by category and sort alphabetically
    official_servers = sorted([r for r in results if r['category'] == 'official'], 
                             key=lambda x: x['server_name'].lower())
    community_servers = sorted([r for r in results if r['category'] == 'community'], 
                              key=lambda x: x['server_name'].lower())
    
    print(f"\n=== Batching Results ===")
    print(f"Official servers: {len(official_servers)} servers")
    print(f"Community servers: {len(community_servers)} servers")
    print(f"Batch size: {batch_size} servers per batch")
    print(f"Total: {len(results)} servers")
    
    created_files = []
    
    # Process official servers
    if official_servers:
        official_batches = [official_servers[i:i + batch_size] for i in range(0, len(official_servers), batch_size)]
        print(f"\nOfficial servers: {len(official_servers)} servers → {len(official_batches)} batches")
        
        for batch_num, batch in enumerate(official_batches, 1):
            batch_filename = os.path.join(output_dir, f"{output_prefix}_official_batch_{batch_num}.csv")
            print(f"  - {os.path.basename(batch_filename)} ({len(batch)} servers)")
            write_csv_file(batch, batch_filename)
            created_files.append(batch_filename)
    
    # Process community servers
    if community_servers:
        community_batches = [community_servers[i:i + batch_size] for i in range(0, len(community_servers), batch_size)]
        print(f"\nCommunity servers: {len(community_servers)} servers → {len(community_batches)} batches")
        
        for batch_num, batch in enumerate(community_batches, 1):
            batch_filename = os.path.join(output_dir, f"{output_prefix}_community_batch_{batch_num}.csv")
            print(f"  - {os.path.basename(batch_filename)} ({len(batch)} servers)")
            write_csv_file(batch, batch_filename)
            created_files.append(batch_filename)
    
    print(f"\n=== Batching Complete ===")
    print(f"Created {len(created_files)} batch files:")
    for filename in created_files:
        print(f"  - {os.path.basename(filename)}")
    
    return created_files

def main():
    """Main function to fetch PRs and write batched results."""
    parser = argparse.ArgumentParser(description='Identify open PRs that are adding servers to the README and output batched CSV files')
    
    parser.add_argument('--per-page', type=int, default=20, choices=range(1, 101),
                       help='PRs per page (1-100, default: 20)')
    parser.add_argument('--start-page', type=int, default=1,
                       help='Starting page number (default: 1)')
    parser.add_argument('--max-pages', type=int, default=10,
                       help='Maximum number of pages to process (default: 10)')
    parser.add_argument('--output-prefix', default='server_addition_prs',
                       help='Output CSV filename prefix (default: server_addition_prs)')
    parser.add_argument('--batch-size', type=int, default=10,
                       help='Number of servers per batch (default: 10)')
    
    args = parser.parse_args()
    
    print("=== MCP Server Addition PR Identifier ===")
    print(f"Fetching open PRs to identify server additions to README")
    print()
    
    # Fetch all PRs using pagination
    all_prs = fetch_all_prs(
        state='open', 
        per_page=args.per_page, 
        start_page=args.start_page,
        max_pages=args.max_pages
    )
    
    if not all_prs:
        print("No PRs found!")
        return
    
    print(f"\n=== Analyzing {len(all_prs)} PRs for server additions ===")
    
    # Process each PR
    results = []
    
    for i, pr in enumerate(all_prs, 1):
        print(f"\n[{i}/{len(all_prs)}] Processing PR #{pr['number']}")
        
        # Analyze PR for server addition
        server_addition = analyze_pr_for_server_addition(pr)
        
        if server_addition:
            results.append(server_addition)
            print(f"  ✓ Added to results")
        else:
            print(f"  - Not a server addition PR")
        
        # Small delay to be nice to the API
        time.sleep(0.2)
    
    # Write results
    print(f"\n=== Final Summary ===")
    print(f"Total PRs analyzed: {len(all_prs)}")
    print(f"PRs adding servers to README: {len(results)}")
    
    if results:
        write_batched_results(
            results, 
            output_prefix=args.output_prefix,
            batch_size=args.batch_size
        )
        
        # Show breakdown by category
        official_count = len([r for r in results if r['category'] == 'official'])
        community_count = len([r for r in results if r['category'] == 'community'])
        
        print(f"\n=== Server Addition PRs by Category ===")
        print(f"Official servers (with icons): {official_count}")
        if official_count > 0:
            official_servers = [r for r in results if r['category'] == 'official']
            for result in official_servers[:5]:  # Show first 5
                print(f"  PR #{result['pr_number']}: {result['server_name']} by {result['pr_author']}")
            if official_count > 5:
                print(f"  ... and {official_count - 5} more")
        
        print(f"\nCommunity servers (no icons): {community_count}")
        if community_count > 0:
            community_servers = [r for r in results if r['category'] == 'community']
            for result in community_servers[:5]:  # Show first 5
                print(f"  PR #{result['pr_number']}: {result['server_name']} by {result['pr_author']}")
            if community_count > 5:
                print(f"  ... and {community_count - 5} more")
    
    print(f"\nComplete! Results saved to CSV files.")

if __name__ == "__main__":
    main()
