#!/usr/bin/env python3
"""
Script to merge validated servers into the README and generate PR descriptions.

This script:
1. Reads validated server data from CSV files
2. Filters for servers by category (community or official)
3. Deduplicates servers by URL (case-insensitive)
4. Merges them into the appropriate section of the README
5. Maintains alphabetical order
6. Logs changes
7. Optionally generates PR descriptions with consistent deduplication

Usage:
    # Merge servers into README
    python merge_servers.py --server-type community [--readme-path path/to/README.md] [--dry-run]
    python merge_servers.py --server-type official [--readme-path path/to/README.md] [--dry-run]
    
    # Generate PR description and merge
    python merge_servers.py --server-type community --generate-pr-description [--readme-path path/to/README.md]
    
    # Generate PR description only (dry run)
    python merge_servers.py --server-type community --generate-pr-description --dry-run
"""

import csv
import os
import glob
import argparse
import re
from typing import List, Dict
from datetime import datetime

# Configuration for different server types
SERVER_CONFIGS = {
    'community': {
        'section_header': '### 🌎 Community Servers',
        'log_prefix': 'community_merge_log',
        'display_name': 'Community Servers'
    },
    'official': {
        'section_header': '### 🎖️ Official Integrations',
        'log_prefix': 'official_merge_log',
        'display_name': 'Official Servers'
    }
}

def collect_valid_servers(server_type: str) -> List[Dict]:
    """Parse all CSV files and collect servers marked as 'Valid' and categorized as specified type"""
    valid_servers = []
    
    # Get the script directory and create output directory path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'output')
    validation_results_dir = os.path.join(output_dir, 'validation_results')
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Look for CSV files in the validation_results directory only
    csv_files = []
    
    if os.path.exists(validation_results_dir):
        validation_pattern = os.path.join(validation_results_dir, "*.csv")
        csv_files = glob.glob(validation_pattern)
    
    print(f"Looking for CSV files in: {validation_results_dir}")
    print(f"Found {len(csv_files)} CSV files to process")
    
    for csv_file in sorted(csv_files):
        print(f"Processing {os.path.basename(csv_file)}...")
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Only process valid servers of the specified type
                    if (row.get('Validation_Status', '').strip() == 'Valid' and 
                        row.get('Category', '').strip() == server_type):
                        
                        complete_line = row.get('Complete_Line', '').strip()
                        server_name = row.get('Server_Name', '').strip()
                        # Skip community servers that have image links (likely mis-labeled official servers)
                        if server_type == 'community' and '<img' in complete_line:
                            print(f"  Skipping community server with image (likely mis-labeled): {server_name}")
                            continue
                        
                        valid_servers.append({
                            'pr_number': row.get('PR_Number', '').strip(),
                            'original_pr_number': row.get('Original_PR_Number', '').strip(),
                            'server_index': row.get('Server_Index', '1').strip(),
                            'total_servers_in_pr': row.get('Total_Servers_In_PR', '1').strip(),
                            'server_name': server_name,
                            'server_url': row.get('Server_URL', '').strip(),
                            'complete_line': complete_line,
                            'pr_author': row.get('PR_Author', '').strip(),
                            'category': row.get('Category', '').strip()
                        })
        except Exception as e:
            print(f"Error processing {os.path.basename(csv_file)}: {e}")
    
    print(f"Found {len(valid_servers)} valid {server_type} servers")
    return valid_servers

def extract_server_name_from_line(line: str) -> str:
    """Extract server name from a README line for sorting purposes."""
    # Pattern to match server entries: - **[Name](url)** - description
    # or: - <img...> **[Name](url)** - description
    pattern = r'^\s*-\s+(?:<img[^>]*>\s+)?\*\*\[([^\]]+)\]'
    match = re.match(pattern, line.strip())
    if match:
        return match.group(1)
    return line.strip()

def extract_url_from_line(line: str) -> str:
    """Extract URL from a README line for deduplication purposes."""
    # Pattern to match server entries: - **[Name](url)** - description
    # or: - <img...> **[Name](url)** - description
    pattern = r'^\s*-\s+(?:<img[^>]*>\s+)?\*\*\[[^\]]+\]\(([^)]+)\)'
    match = re.match(pattern, line.strip())
    if match:
        return match.group(1)
    return line.strip()

def find_servers_section(readme_lines: List[str], section_header: str) -> tuple:
    """Find the start and end of the specified servers section."""
    start_idx = None
    end_idx = None
    
    for i, line in enumerate(readme_lines):
        # Look for the specified section header
        if section_header in line:
            start_idx = i
            continue
        
        # If we found the start, look for the next section or end of file
        if start_idx is not None:
            # Look for next section header (### or ##) or end of file
            if line.strip().startswith('### ') or line.strip().startswith('## '):
                end_idx = i
                break
    
    # If no end found, use end of file
    if start_idx is not None and end_idx is None:
        end_idx = len(readme_lines)
    
    return start_idx, end_idx

def merge_servers_into_readme(readme_path: str, servers: List[Dict], server_type: str, dry_run: bool = False) -> bool:
    """Merge servers into the README file."""
    if not os.path.exists(readme_path):
        print(f"Error: README file not found at {readme_path}")
        return False
    
    config = SERVER_CONFIGS[server_type]
    section_header = config['section_header']
    display_name = config['display_name']
    
    # Read the current README
    with open(readme_path, 'r', encoding='utf-8') as f:
        readme_lines = f.readlines()
    
    # Find the servers section
    start_idx, end_idx = find_servers_section(readme_lines, section_header)
    
    if start_idx is None:
        print(f"Error: Could not find '{section_header}' section in README")
        return False
    
    print(f"Found {display_name} section at lines {start_idx + 1} to {end_idx}")
    
    # Extract existing servers from the section
    existing_servers = []
    section_lines = readme_lines[start_idx:end_idx]
    
    for line in section_lines:
        line_stripped = line.strip()
        # Skip headers, empty lines, and notes
        if (line_stripped.startswith('### ') or 
            line_stripped.startswith('> ') or 
            not line_stripped or
            not line_stripped.startswith('- ')):
            continue
        
        existing_servers.append(line.rstrip('\n'))
    
    print(f"Found {len(existing_servers)} existing {server_type} servers in README")
    
    # Create new server lines from validated servers
    new_server_lines = []
    for server in servers:
        new_server_lines.append(server['complete_line'])
    
    print(f"Adding {len(new_server_lines)} new {server_type} servers")
    
    # Combine existing and new servers
    all_server_lines = existing_servers + new_server_lines
    
    # Remove duplicates (by URL)
    seen_urls = set()
    unique_servers = []
    
    for line in all_server_lines:
        url = extract_url_from_line(line)
        if url.lower() not in seen_urls:
            seen_urls.add(url.lower())
            unique_servers.append(line)
        else:
            server_name = extract_server_name_from_line(line)
            print(f"  Skipping duplicate URL: {server_name} ({url})")
    
    # Sort servers alphabetically by name (case-insensitive)
    unique_servers.sort(key=lambda x: extract_server_name_from_line(x).lower())
    
    print(f"Final count: {len(unique_servers)} unique {server_type} servers (after deduplication)")
    
    # Find the first bullet point (start of server list)
    insert_idx = start_idx + 1
    while insert_idx < end_idx:
        line = readme_lines[insert_idx].strip()
        if line.startswith('- '):
            break
        insert_idx += 1
    
    # Build the new README content
    new_readme_lines = []
    
    # Add everything before the servers list
    new_readme_lines.extend(readme_lines[:insert_idx])
    
    # Add the sorted server list
    for server_line in unique_servers:
        new_readme_lines.append(server_line + '\n')
    
    # Add everything after the servers section
    new_readme_lines.extend(readme_lines[end_idx:])
    
    if dry_run:
        print("\n=== DRY RUN - Changes that would be made ===")
        print(f"Would update {len(unique_servers)} {server_type} servers in README")
        print("First 5 servers that would be in the list:")
        for i, line in enumerate(unique_servers[:5]):
            server_name = extract_server_name_from_line(line)
            print(f"  {i+1}. {server_name}")
        if len(unique_servers) > 5:
            print(f"  ... and {len(unique_servers) - 5} more")
        return True
    
    # Write the updated README
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.writelines(new_readme_lines)
    
    print(f"Successfully updated README with {len(unique_servers)} {server_type} servers")
    
    # Log the changes
    log_changes(servers, readme_path, server_type)
    
    return True

def deduplicate_servers_by_url(servers: List[Dict]) -> List[Dict]:
    """Remove duplicate servers based on URL, using the same logic as merge_servers_into_readme."""
    seen_urls = set()
    unique_servers = []
    
    for server in servers:
        url = server['server_url'].lower()
        if url not in seen_urls:
            seen_urls.add(url)
            unique_servers.append(server)
        else:
            print(f"  Skipping duplicate URL: {server['server_name']} ({server['server_url']})")
    
    return unique_servers

def filter_new_servers_against_readme(servers: List[Dict], readme_path: str, server_type: str) -> List[Dict]:
    """Filter servers to only include those that are not already in the README."""
    if not os.path.exists(readme_path):
        print(f"Warning: README file not found at {readme_path}, including all servers")
        return servers
    
    config = SERVER_CONFIGS[server_type]
    section_header = config['section_header']
    
    # Read the current README
    with open(readme_path, 'r', encoding='utf-8') as f:
        readme_lines = f.readlines()
    
    # Find the servers section
    start_idx, end_idx = find_servers_section(readme_lines, section_header)
    
    if start_idx is None:
        print(f"Warning: Could not find '{section_header}' section in README, including all servers")
        return servers
    
    # Extract existing server URLs from the section
    existing_urls = set()
    section_lines = readme_lines[start_idx:end_idx]
    
    for line in section_lines:
        line_stripped = line.strip()
        # Skip headers, empty lines, and notes
        if (line_stripped.startswith('### ') or 
            line_stripped.startswith('> ') or 
            not line_stripped or
            not line_stripped.startswith('- ')):
            continue
        
        url = extract_url_from_line(line.rstrip('\n'))
        if url:
            existing_urls.add(url.lower())
    
    # Filter out servers that already exist
    new_servers = []
    for server in servers:
        if server['server_url'].lower() not in existing_urls:
            new_servers.append(server)
        else:
            print(f"  Excluding duplicate from PR description: {server['server_name']} ({server['server_url']})")
    
    return new_servers

def generate_pr_description(servers: List[Dict], server_type: str, readme_path: str = None) -> str:
    """Generate a PR description for the servers that will be merged."""
    if not servers:
        return "No servers to add."
    
    # Filter out servers that already exist in README if path is provided
    if readme_path:
        servers = filter_new_servers_against_readme(servers, readme_path, server_type)
    
    # Apply deduplication within the new servers list
    unique_servers = deduplicate_servers_by_url(servers)
    
    if not unique_servers:
        return "No new servers to add (all servers already exist in README)."
    
    # Sort by server name (primary) and PR number (secondary)
    def get_original_pr_number(pr_number_str):
        """Extract original PR number from potentially split PR number."""
        if '-' in pr_number_str:
            return int(pr_number_str.split('-')[0])
        else:
            return int(pr_number_str)
    
    unique_servers.sort(key=lambda x: (get_original_pr_number(x['pr_number']), x['server_name'].lower()))
    
    # Generate title and description based on server type
    config = SERVER_CONFIGS[server_type]
    display_name = config['display_name']
    
    if server_type == 'community':
        title = f"Add {len(unique_servers)} Community MCP Server{'s' if len(unique_servers) != 1 else ''}"
        description_text = f"This PR adds {len(unique_servers)} new MCP server{'s' if len(unique_servers) != 1 else ''} to the README, sourced from community pull requests."
    else:  # official
        title = f"Add {len(unique_servers)} Official MCP Integration{'s' if len(unique_servers) != 1 else ''}"
        description_text = f"This PR adds {len(unique_servers)} new MCP integration{'s' if len(unique_servers) != 1 else ''} to the README, sourced from official integrations."
    
    # Start building the description
    description = f"# {title}\n\n"
    description += f"{description_text}\n\n"
    description += "## Added Servers\n\n"
    
    # List all servers with server names linking to their repository URLs
    for server in unique_servers:
        # Extract the base PR number for GitHub links
        pr_number = server['pr_number']
        
        # If PR number has format like "1729-2", extract "1729" for both display and URL
        if '-' in pr_number:
            original_pr = pr_number.split('-')[0]
        else:
            original_pr = pr_number
        
        # Use the original PR number for both display and URL (no more dashes)
        display_pr = original_pr
        
        # Add split context if this is from a multi-server PR
        split_context = ""
        if server.get('total_servers_in_pr', '1') != '1':
            split_context = f" (server {server.get('server_index', '1')} of {server.get('total_servers_in_pr', '1')})"
        
        description += f"- **[{server['server_name']}]({server['server_url']})** ([PR #{display_pr}](https://github.com/modelcontextprotocol/servers/pull/{original_pr})){split_context} by @{server['pr_author']}\n"
    
    return description

def save_pr_description(servers: List[Dict], server_type: str, readme_path: str = None) -> str:
    """Generate and save PR description to a file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate PR description
    pr_description = generate_pr_description(servers, server_type, readme_path)
    
    # Create output filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f"pr_description_{server_type}_{timestamp}.md")
    
    # Write PR description
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(pr_description)
    
    print(f"PR description generated: {output_file}")
    print(f"Description length: {len(pr_description)} characters")
    
    # Show preview
    print(f"\n=== PR Description Preview ===")
    lines = pr_description.split('\n')
    for i, line in enumerate(lines[:15]):  # Show first 15 lines
        print(line)
    
    if len(lines) > 15:
        print(f"... and {len(lines) - 15} more lines")
    
    return output_file

def log_changes(servers: List[Dict], readme_path: str, server_type: str):
    """Log the changes made to a file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'output')
    
    config = SERVER_CONFIGS[server_type]
    log_prefix = config['log_prefix']
    display_name = config['display_name']
    
    log_file = os.path.join(output_dir, f"{log_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"{display_name} Merge Log\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        f.write(f"README Path: {readme_path}\n")
        f.write(f"Servers Added: {len(servers)}\n\n")
        
        f.write("Added Servers:\n")
        f.write("=" * 50 + "\n")
        
        for server in servers:
            # Add split PR context if applicable
            split_info = ""
            if server.get('total_servers_in_pr', '1') != '1':
                split_info = f" (server {server.get('server_index', '1')} of {server.get('total_servers_in_pr', '1')} from original PR #{server.get('original_pr_number', server['pr_number'])})"
            
            f.write(f"PR #{server['pr_number']}: {server['server_name']}{split_info}\n")
            f.write(f"  Author: {server['pr_author']}\n")
            f.write(f"  URL: {server['server_url']}\n")
            f.write(f"  Category: {server['category']}\n")
            if server.get('original_pr_number') and server['original_pr_number'] != server['pr_number']:
                f.write(f"  Original PR: #{server['original_pr_number']}\n")
            f.write(f"  Line: {server['complete_line']}\n")
            f.write("\n")
    
    print(f"Changes logged to: {log_file}")

def main():
    """Main function to orchestrate the merge process."""
    parser = argparse.ArgumentParser(description='Merge validated servers into README and optionally generate PR description')
    parser.add_argument('--server-type', 
                       choices=['community', 'official'],
                       required=True,
                       help='Type of servers to process (community or official)')
    parser.add_argument('--readme-path', 
                       default='path/to/README.md',
                       help='Path to the README.md file to update')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be changed without making changes')
    parser.add_argument('--generate-pr-description', action='store_true',
                       help='Generate a PR description for the servers being processed')
    
    args = parser.parse_args()
    
    config = SERVER_CONFIGS[args.server_type]
    display_name = config['display_name']
    
    print(f"=== {display_name} README Merger ===")
    print(f"Server type: {args.server_type}")
    print(f"README path: {args.readme_path}")
    print(f"Dry run: {args.dry_run}")
    print(f"Generate PR description: {args.generate_pr_description}")
    print()
    
    # Collect valid servers of the specified type
    servers = collect_valid_servers(args.server_type)
    
    if not servers:
        print(f"No valid {args.server_type} servers found to process.")
        return
    
    print(f"\nServers to process:")
    for server in servers:
        print(f"  - {server['server_name']} (PR #{server['pr_number']}) by {server['pr_author']}")
    
    # Generate PR description if requested
    pr_description_file = None
    if args.generate_pr_description:
        print(f"\n=== Generating PR Description ===")
        pr_description_file = save_pr_description(servers, args.server_type, args.readme_path)
    
    # Merge into README (unless it's a dry run with only PR description generation)
    if not args.dry_run or not args.generate_pr_description:
        print(f"\n=== Merging into README ===")
        success = merge_servers_into_readme(args.readme_path, servers, args.server_type, args.dry_run)
        
        if not success:
            print("\nMerge failed!")
            exit(1)
    
    # Final summary
    print(f"\n=== Summary ===")
    if args.generate_pr_description:
        print(f"✓ PR description generated: {pr_description_file}")
    
    if args.dry_run:
        if args.generate_pr_description:
            print("✓ PR description shows what would be included")
        print("✓ Dry run completed - no README changes made")
    else:
        print(f"✓ {display_name} merge completed successfully")
    
    print(f"✓ Processed {len(servers)} {args.server_type} servers")

if __name__ == "__main__":
    main()
