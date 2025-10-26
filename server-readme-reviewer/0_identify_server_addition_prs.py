#!/usr/bin/env python3
"""
Script to identify open PRs that are adding servers to the README and output them in batched CSV files.

This script:
- Fetches open PRs from the modelcontextprotocol/servers repository using proper pagination
- Identifies which PRs are adding server entries to the README (single or multiple)
- Automatically splits multi-server PRs into individual server entries with suffix numbering
- Categorizes servers using label-based logic with fallback:
  * If PR has 'add-official-server' label → categorized as 'official'
  * If PR has 'add-community-server' label → categorized as 'community'
  * Otherwise, uses fallback logic (icons or 'official' in title → official, else community)
- Checks PR approval status and pre-populates validation columns for approved PRs
- Automatically fixes missing alt text in img tags using the server name
- Outputs results to batched CSV files with full validation columns (sorted alphabetically by server name)
- Logs all decisions with detailed reasoning for both accepted and rejected PRs
- Creates a comprehensive log file and optional rejected PRs CSV for audit trail

Usage:
    # Default usage with batch size 10, approval checking, and auto-splitting enabled
    python 0_identify_server_addition_prs.py
    
    # Filter for official servers only
    python 0_identify_server_addition_prs.py --category official
    
    # Filter for community servers only
    python 0_identify_server_addition_prs.py --category community
    
    # Custom batch size
    python 0_identify_server_addition_prs.py --batch-size 5
    
    # Control pagination
    python 0_identify_server_addition_prs.py --max-pages 5 --per-page 30
    
    # Disable auto-splitting (original behavior)
    python 0_identify_server_addition_prs.py --no-split-multiple-servers
    
    # Set maximum servers per PR for splitting
    python 0_identify_server_addition_prs.py --max-servers-per-pr 5
    
    # Enable debug logging
    python 0_identify_server_addition_prs.py --log-level DEBUG
    
    # Skip rejected PRs CSV
    python 0_identify_server_addition_prs.py --no-rejected-csv

Output Files:
    - server_addition_prs_official_batch_N.csv: Batched official server PRs
    - server_addition_prs_community_batch_N.csv: Batched community server PRs
    - server_pr_analysis_YYYYMMDD_HHMMSS.log: Detailed analysis log
    - rejected_prs_YYYYMMDD_HHMMSS.csv: Rejected PRs with reasons (optional)
"""

import subprocess
import json
import csv
import re
import sys
import argparse
import os
import logging
from datetime import datetime
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
    # Pattern for server entries with icons - now allows optional content before the dash
    icon_pattern = r'^\s*-\s+(<img[^>]*>)\s+\*\*\[([^\]]+)\]\(([^)]+)\)\*\*\s*(.*?)\s*-\s*(.+)$'
    
    # Pattern for server entries without icons - now allows optional content before the dash
    no_icon_pattern = r'^\s*-\s+\*\*\[([^\]]+)\]\(([^)]+)\)\*\*\s*(.*?)\s*-\s*(.+)$'
    
    # Try icon pattern first
    icon_match = re.match(icon_pattern, line.strip())
    if icon_match:
        img_tag = icon_match.group(1)
        server_name = icon_match.group(2)
        server_url = icon_match.group(3)
        attribution = icon_match.group(4).strip()
        description = icon_match.group(5)
        
        # Fix alt text in the img tag
        fixed_img_tag = fix_img_alt_text(img_tag, server_name)
        
        # Reconstruct the complete line with fixed img tag
        if attribution:
            fixed_line = f"- {fixed_img_tag} **[{server_name}]({server_url})** {attribution} - {description}"
        else:
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
        attribution = no_icon_match.group(3).strip()
        description = no_icon_match.group(4)
        
        # Reconstruct the complete line
        if attribution:
            fixed_line = f"- **[{server_name}]({server_url})** {attribution} - {description}"
        else:
            fixed_line = f"- **[{server_name}]({server_url})** - {description}"
        
        return {
            'server_name': server_name,
            'server_url': server_url,
            'description': description,
            'complete_line': fixed_line
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

# Global variables for logging
logger = None
rejected_prs = []

def setup_logging(output_dir: str, log_level: str = 'INFO') -> logging.Logger:
    """Set up logging configuration with both file and console handlers."""
    global logger
    
    # Create timestamp for log files
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create logger
    logger = logging.getLogger('server_pr_analyzer')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter('%(message)s')
    
    # File handler for detailed logging
    log_file = os.path.join(output_dir, f'server_pr_analysis_{timestamp}.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Console handler for user-friendly output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    logger.info(f"Logging initialized. Log file: {log_file}")
    return logger

def log_rejection(pr: Dict, reason: str, details: str = ""):
    """Log a rejected PR with reason and details."""
    global rejected_prs, logger
    
    rejection_entry = {
        'pr_number': pr['number'],
        'pr_title': pr['title'],
        'pr_author': pr['user'],
        'rejection_reason': reason,
        'analysis_details': details,
        'labels': ', '.join(pr.get('labels', [])),
        'timestamp': datetime.now().isoformat()
    }
    
    rejected_prs.append(rejection_entry)
    
    if logger:
        logger.debug(f"REJECTED PR #{pr['number']}: {reason} - {details}")

def write_rejected_prs_csv(output_dir: str):
    """Write rejected PRs to a CSV file."""
    global rejected_prs
    
    if not rejected_prs:
        return None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = os.path.join(output_dir, f'rejected_prs_{timestamp}.csv')
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'PR_Number', 'PR_Title', 'PR_Author', 'Rejection_Reason', 
            'Analysis_Details', 'Labels', 'Timestamp'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        
        for rejection in rejected_prs:
            writer.writerow({
                'PR_Number': rejection['pr_number'],
                'PR_Title': rejection['pr_title'],
                'PR_Author': rejection['pr_author'],
                'Rejection_Reason': rejection['rejection_reason'],
                'Analysis_Details': rejection['analysis_details'],
                'Labels': rejection['labels'],
                'Timestamp': rejection['timestamp']
            })
    
    return filename

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

def check_pr_approval_status(pr_number: int) -> Dict[str, any]:
    """
    Check if a PR has been approved by fetching its reviews.
    
    Returns:
        Dict with approval info: {
            'is_approved': bool,
            'approval_count': int,
            'approver': str (first approver username),
            'approval_date': str (ISO format),
            'error': str (if any error occurred)
        }
    """
    try:
        cmd = [
            'gh', 'api', f'repos/modelcontextprotocol/servers/pulls/{pr_number}/reviews',
            '--jq', '[.[] | select(.state == "APPROVED")] | map({user: .user.login, submitted_at: .submitted_at}) | sort_by(.submitted_at)'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
        
        if not result.stdout or not result.stdout.strip():
            return {
                'is_approved': False,
                'approval_count': 0,
                'approver': '',
                'approval_date': '',
                'error': None
            }
        
        approvals = json.loads(result.stdout)
        
        if not approvals:
            return {
                'is_approved': False,
                'approval_count': 0,
                'approver': '',
                'approval_date': '',
                'error': None
            }
        
        # Get the first (earliest) approval
        first_approval = approvals[0]
        
        return {
            'is_approved': True,
            'approval_count': len(approvals),
            'approver': first_approval['user'],
            'approval_date': first_approval['submitted_at'],
            'error': None
        }
        
    except subprocess.CalledProcessError as e:
        print(f"    Warning: Error checking approval status for PR #{pr_number}: {e}")
        return {
            'is_approved': False,
            'approval_count': 0,
            'approver': '',
            'approval_date': '',
            'error': str(e)
        }
    except json.JSONDecodeError as e:
        print(f"    Warning: Error parsing approval response for PR #{pr_number}: {e}")
        return {
            'is_approved': False,
            'approval_count': 0,
            'approver': '',
            'approval_date': '',
            'error': f"JSON decode error: {e}"
        }

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

def analyze_pr_for_server_addition(pr: Dict, split_multiple_servers: bool = True, max_servers_per_pr: int = 10) -> Optional[List[Dict[str, str]]]:
    """Analyze a PR to see if it's adding server(s) to the README."""
    global logger
    
    pr_number = pr['number']
    pr_title = pr['title']
    pr_author = pr['user']
    
    print(f"  Analyzing PR #{pr_number}: {pr_title}")
    if logger:
        logger.info(f"Analyzing PR #{pr_number}: {pr_title} by {pr_author}")
    
    # Skip PRs that are adding resources, not servers
    if 'add-community-resource' in pr.get('labels', []):
        reason = "PR is adding a resource, not a server"
        print(f"    Skipping - {reason}")
        log_rejection(pr, "Resource Addition", reason)
        return None
    
    # Fetch the diff
    diff = fetch_pr_diff(pr_number)
    if not diff:
        reason = "Could not fetch diff from GitHub API"
        print(f"    Could not fetch diff")
        log_rejection(pr, "Diff Fetch Failed", reason)
        return None
    
    # Look for README.md changes
    if 'README.md' not in diff:
        reason = "No changes to README.md file"
        print(f"    No README.md changes")
        log_rejection(pr, "No README Changes", reason)
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
    
    # Check if we found any server entries
    if len(added_lines) == 0:
        reason = "No valid server entries found in diff additions"
        print(f"    No server entries found in additions")
        log_rejection(pr, "No Server Entries", reason)
        return None
    
    # Check if we have too many servers for splitting
    if len(added_lines) > max_servers_per_pr:
        reason = f"Too many server lines ({len(added_lines)} > {max_servers_per_pr} max)"
        print(f"    Too many server lines ({len(added_lines)}), exceeds limit of {max_servers_per_pr}")
        log_rejection(pr, "Exceeds Server Limit", reason)
        return None
    
    # Handle multiple servers based on split_multiple_servers setting
    if len(added_lines) > 1 and not split_multiple_servers:
        reason = f"Adding multiple server lines ({len(added_lines)} lines) - splitting disabled"
        print(f"    Adding multiple lines ({len(added_lines)}), skipping (splitting disabled)")
        log_rejection(pr, "Multiple Server Lines", reason)
        return None
    
    # Check that there are no other significant additions (to avoid PRs that modify multiple lines)
    non_server_additions = 0
    for line in lines:
        if line.startswith('+') and not line.startswith('+++'):
            added_line = line[1:].strip()
            # Skip empty lines and lines that are just whitespace
            if added_line and not extract_server_info_from_line(line[1:]):
                non_server_additions += 1
    
    # Be more lenient with non-server additions for multi-server PRs
    max_non_server_additions = 2 + len(added_lines)  # Allow more for multi-server PRs
    if non_server_additions > max_non_server_additions:
        reason = f"Too many non-server additions ({non_server_additions} lines)"
        print(f"    Too many non-server additions ({non_server_additions}), skipping")
        log_rejection(pr, "Too Many Changes", reason)
        return None
    
    # Check approval status once for the entire PR
    print(f"    Checking approval status...")
    approval_info = check_pr_approval_status(pr_number)
    if approval_info['is_approved']:
        print(f"    [APPROVED] PR is approved by {approval_info['approver']} ({approval_info['approval_count']} approval(s))")
        if logger:
            logger.info(f"PR #{pr_number} is pre-approved by {approval_info['approver']}")
    else:
        print(f"    - PR not yet approved")
        if logger:
            logger.debug(f"PR #{pr_number} not yet approved")
    
    # Process each server entry
    server_entries = []
    
    # Ensure pr_number is consistently handled as string for concatenation
    pr_number_str = str(pr_number)
    
    for i, (original_line, server_info) in enumerate(added_lines):
        # Create suffix for multiple servers (1-indexed)
        server_index = i + 1
        suffix = f"-{server_index}" if len(added_lines) > 1 else ""
        display_pr_number = f"{pr_number_str}{suffix}"
        
        # Log the PR number assignment for debugging
        if logger:
            if len(added_lines) > 1:
                logger.debug(f"Split PR #{pr_number}: Server {server_index}/{len(added_lines)} -> PR #{display_pr_number}")
            else:
                logger.debug(f"Single server PR #{pr_number} -> PR #{display_pr_number}")
        
        # Use the fixed complete line from server_info (which has alt text fixed)
        complete_line = server_info['complete_line']
        category = categorize_server_by_labels(pr.get('labels', []), complete_line)
        
        # Prepare validation columns based on approval status
        if approval_info['is_approved']:
            validation_status = "Valid"
            confidence_level = "100%"
            validation_notes = f"Pre-approved PR - skipping manual validation (approved by {approval_info['approver']})"
        else:
            validation_status = ""
            confidence_level = ""
            validation_notes = ""
        
        # Validate PR number format before creating entry
        if not display_pr_number or not str(display_pr_number).strip():
            if logger:
                logger.error(f"Invalid display_pr_number generated: '{display_pr_number}' for PR #{pr_number}, server {server_index}")
            continue
        
        server_entry = {
            'pr_number': display_pr_number,
            'original_pr_number': pr_number,
            'server_index': server_index,
            'total_servers_in_pr': len(added_lines),
            'pr_title': pr_title,
            'complete_line': complete_line,
            'server_url': server_info['server_url'],
            'server_name': server_info['server_name'],
            'pr_author': pr_author,
            'category': category,
            # Approval metadata
            'is_approved': approval_info['is_approved'],
            'approval_count': approval_info['approval_count'],
            'approver': approval_info['approver'],
            'approval_date': approval_info['approval_date'],
            # Validation columns (pre-populated for approved PRs)
            'validation_status': validation_status,
            'confidence_level': confidence_level,
            'validation_notes': validation_notes
        }
        
        # Additional validation logging
        if logger:
            logger.debug(f"Created server entry: PR #{display_pr_number}, Server: '{server_info['server_name']}', Category: {category}")
        
        server_entries.append(server_entry)
    
    # Log the results
    if len(added_lines) == 1:
        print(f"    [OK] Found {server_entries[0]['category']} server addition: {server_entries[0]['server_name']}")
        if logger:
            logger.info(f"ACCEPTED PR #{pr_number}: {server_entries[0]['category']} server '{server_entries[0]['server_name']}' by {pr_author}")
    else:
        print(f"    [OK] Found {len(added_lines)} server additions (split into individual entries):")
        for entry in server_entries:
            print(f"      - {entry['category']}: {entry['server_name']} (PR #{entry['pr_number']})")
        if logger:
            logger.info(f"ACCEPTED PR #{pr_number}: Split into {len(added_lines)} server entries by {pr_author}")
            for entry in server_entries:
                logger.info(f"  - {entry['category']} server '{entry['server_name']}' (PR #{entry['pr_number']})")
    
    return server_entries

def write_csv_file(results: List[Dict], filename: str):
    """Write results to a single CSV file with full validation columns, sorted alphabetically by server name."""
    # Sort results by server_name (case-insensitive)
    sorted_results = sorted(results, key=lambda x: x['server_name'].lower())
    
    print(f"  Sorting {len(results)} entries alphabetically by server name...")
    if results:
        print(f"  First entry after sorting: {sorted_results[0]['server_name']}")
        print(f"  Last entry after sorting: {sorted_results[-1]['server_name']}")
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        # Include all validation columns plus new metadata columns for split PRs
        fieldnames = [
            'PR_Number', 'Original_PR_Number', 'Server_Index', 'Total_Servers_In_PR', 
            'PR_Title', 'Complete_Line', 'Server_URL', 'Server_Name', 'PR_Author', 'Category',
            'Validation_Status', 'Is_Valid_Confidence_Level', 'Validation_Notes',
            'Is_Approved', 'Approval_Count', 'Approver', 'Approval_Date'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        
        for result in sorted_results:
            writer.writerow({
                'PR_Number': result['pr_number'],
                'Original_PR_Number': result.get('original_pr_number', result['pr_number']),
                'Server_Index': result.get('server_index', 1),
                'Total_Servers_In_PR': result.get('total_servers_in_pr', 1),
                'PR_Title': result['pr_title'],
                'Complete_Line': result['complete_line'],
                'Server_URL': result['server_url'],
                'Server_Name': result['server_name'],
                'PR_Author': result['pr_author'],
                'Category': result['category'],
                'Validation_Status': result.get('validation_status', ''),
                'Is_Valid_Confidence_Level': result.get('confidence_level', ''),
                'Validation_Notes': result.get('validation_notes', ''),
                'Is_Approved': result.get('is_approved', False),
                'Approval_Count': result.get('approval_count', 0),
                'Approver': result.get('approver', ''),
                'Approval_Date': result.get('approval_date', '')
            })

def write_batched_results(results: List[Dict], output_prefix: str = 'server_addition_prs', batch_size: int = 10):
    """Write results to batched CSV files, split by category and batch size. Only creates files for categories with results."""
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
    
    # Process official servers (only if there are any)
    if official_servers:
        official_batches = [official_servers[i:i + batch_size] for i in range(0, len(official_servers), batch_size)]
        print(f"\nOfficial servers: {len(official_servers)} servers -> {len(official_batches)} batches")

        for batch_num, batch in enumerate(official_batches, 1):
            batch_filename = os.path.join(output_dir, f"{output_prefix}_official_batch_{batch_num}.csv")
            print(f"  - {os.path.basename(batch_filename)} ({len(batch)} servers)")
            write_csv_file(batch, batch_filename)
            created_files.append(batch_filename)
    else:
        print(f"\nOfficial servers: 0 servers -> No official batch files created")

    # Process community servers (only if there are any)
    if community_servers:
        community_batches = [community_servers[i:i + batch_size] for i in range(0, len(community_servers), batch_size)]
        print(f"\nCommunity servers: {len(community_servers)} servers -> {len(community_batches)} batches")

        for batch_num, batch in enumerate(community_batches, 1):
            batch_filename = os.path.join(output_dir, f"{output_prefix}_community_batch_{batch_num}.csv")
            print(f"  - {os.path.basename(batch_filename)} ({len(batch)} servers)")
            write_csv_file(batch, batch_filename)
            created_files.append(batch_filename)
    else:
        print(f"\nCommunity servers: 0 servers -> No community batch files created")
    
    print(f"\n=== Batching Complete ===")
    if created_files:
        print(f"Created {len(created_files)} batch files:")
        for filename in created_files:
            print(f"  - {os.path.basename(filename)}")
    else:
        print("No batch files created (no servers found)")
    
    return created_files

def main():
    """Main function to fetch PRs and write batched results."""
    global logger, rejected_prs
    
    parser = argparse.ArgumentParser(description='Identify open PRs that are adding servers to the README and output batched CSV files')
    
    parser.add_argument('--per-page', type=int, default=20, choices=range(1, 101),
                       help='PRs per page (1-100, default: 20)')
    parser.add_argument('--start-page', type=int, default=1,
                       help='Starting page number (default: 1)')
    parser.add_argument('--max-pages', type=int, default=20,
                       help='Maximum number of pages to process (default: 20)')
    parser.add_argument('--output-prefix', default='server_addition_prs',
                       help='Output CSV filename prefix (default: server_addition_prs)')
    parser.add_argument('--batch-size', type=int, default=10,
                       help='Number of servers per batch (default: 10)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')
    parser.add_argument('--no-rejected-csv', action='store_true',
                       help='Skip creating rejected PRs CSV file')
    parser.add_argument('--no-split-multiple-servers', action='store_true',
                       help='Disable auto-splitting of multi-server PRs (original behavior)')
    parser.add_argument('--max-servers-per-pr', type=int, default=10,
                       help='Maximum servers per PR for splitting (default: 10)')
    parser.add_argument('--category', choices=['official', 'community', 'all'], default='all',
                       help='Filter servers by category: official, community, or all (default: all)')
    
    args = parser.parse_args()
    
    # Set up output directory and logging
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize logging
    logger = setup_logging(output_dir, args.log_level)
    
    print("=== MCP Server Addition PR Identifier ===")
    print(f"Fetching open PRs to identify server additions to README")
    logger.info("=== MCP Server Addition PR Identifier Started ===")
    logger.info(f"Configuration: per_page={args.per_page}, start_page={args.start_page}, max_pages={args.max_pages}")
    logger.info(f"Output: prefix={args.output_prefix}, batch_size={args.batch_size}")
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
        logger.warning("No PRs found!")
        return
    
    logger.info(f"Fetched {len(all_prs)} PRs for analysis")
    print(f"\n=== Analyzing {len(all_prs)} PRs for server additions ===")
    
    # Process each PR
    results = []
    accepted_count = 0
    rejected_count = 0
    
    # Configure splitting behavior
    split_multiple_servers = not args.no_split_multiple_servers
    
    for i, pr in enumerate(all_prs, 1):
        print(f"\n[{i}/{len(all_prs)}] Processing PR #{pr['number']}")
        
        # Analyze PR for server addition
        server_entries = analyze_pr_for_server_addition(
            pr, 
            split_multiple_servers=split_multiple_servers,
            max_servers_per_pr=args.max_servers_per_pr
        )
        
        if server_entries:
            # server_entries is now a list of server entries
            results.extend(server_entries)
            accepted_count += 1
            print(f"  [OK] Added to results")
        else:
            rejected_count += 1
            print(f"  - Not a server addition PR")
        
        # Show running totals every 10 PRs
        if i % 10 == 0:
            print(f"    Progress: Analyzed {i}/{len(all_prs)} PRs | Accepted: {accepted_count} | Rejected: {rejected_count}")
        
        # Small delay to be nice to the API
        time.sleep(0.2)
    
    # Filter results based on category selection
    if args.category != 'all':
        original_count = len(results)
        results = [r for r in results if r['category'] == args.category]
        filtered_count = original_count - len(results)
        print(f"\n=== Category Filter Applied ===")
        print(f"Category filter '{args.category}': Kept {len(results)} servers, filtered out {filtered_count}")
        logger.info(f"Category filter '{args.category}': Processed {len(results)} servers, filtered {filtered_count}")
    
    # Write results
    print(f"\n=== Final Summary ===")
    print(f"Total PRs analyzed: {len(all_prs)}")
    print(f"PRs adding servers to README: {len(results)}")
    print(f"PRs rejected: {len(rejected_prs)}")
    
    logger.info(f"Analysis complete: {len(all_prs)} PRs analyzed, {len(results)} accepted, {len(rejected_prs)} rejected")
    
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
        print(f"Official servers: {official_count}")
        logger.info(f"Official servers: {official_count}")
        if official_count > 0:
            official_servers = [r for r in results if r['category'] == 'official']
            for result in official_servers[:5]:  # Show first 5
                print(f"  PR #{result['pr_number']}: {result['server_name']} by {result['pr_author']}")
            if official_count > 5:
                print(f"  ... and {official_count - 5} more")
        
        print(f"\nCommunity servers: {community_count}")
        logger.info(f"Community servers: {community_count}")
        if community_count > 0:
            community_servers = [r for r in results if r['category'] == 'community']
            for result in community_servers[:5]:  # Show first 5
                print(f"  PR #{result['pr_number']}: {result['server_name']} by {result['pr_author']}")
            if community_count > 5:
                print(f"  ... and {community_count - 5} more")
    
    # Write rejected PRs CSV if requested and there are rejections
    if not args.no_rejected_csv and rejected_prs:
        rejected_csv_file = write_rejected_prs_csv(output_dir)
        if rejected_csv_file:
            print(f"\n=== Rejected PRs Log ===")
            print(f"Rejected PRs saved to: {os.path.basename(rejected_csv_file)}")
            logger.info(f"Rejected PRs CSV written: {rejected_csv_file}")
            
            # Show rejection reason breakdown
            rejection_reasons = {}
            for rejection in rejected_prs:
                reason = rejection['rejection_reason']
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
            
            print(f"Rejection reasons breakdown:")
            for reason, count in sorted(rejection_reasons.items(), key=lambda x: x[1], reverse=True):
                print(f"  {reason}: {count} PRs")
                logger.info(f"Rejection reason '{reason}': {count} PRs")
    
    print(f"\nComplete! Results saved to CSV files.")
    logger.info("=== MCP Server Addition PR Identifier Completed ===")

if __name__ == "__main__":
    main()
