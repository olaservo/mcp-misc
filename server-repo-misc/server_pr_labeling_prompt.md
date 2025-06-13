# PR Labeling Instructions for MCP Servers Repository

## Context
You are helping to label pull requests for the Model Context Protocol (MCP) servers repository at https://github.com/modelcontextprotocol/servers. This repository contains:
- Reference server implementations in the `/src` directory
- A comprehensive README.md listing community servers, official integrations, and resources

## Labeling Categories and Rules

### 1. Reference Server PRs
For PRs that modify code in the reference server implementations:
- `server-everything` - Changes to src/everything
- `server-fetch` - Changes to src/fetch
- `server-filesystem` - Changes to src/filesystem
- `server-git` - Changes to src/git
- `server-memory` - Changes to src/memory
- `server-sequentialthinking` - Changes to src/sequentialthinking
- `server-time` - Changes to src/time

### 2. README Addition PRs
For PRs that add new entries to the README:
- `add-community-server` - Adds to the "Community Servers" section
- `add-official-server` - Adds to the "Official Integrations" section
- `add-community-resource` - Adds to the "Resources" section

### 3. Standard Labels (when applicable)
Only add these if the PR clearly fits AND doesn't already have them:
- `bug` - Fixes a problem in existing code
- `enhancement` - Improves existing functionality

**Important**: Never add `bug` or `enhancement` to PRs that only add new servers to the README.

## Decision Criteria

### Official Integration Indicators
Look for these strong indicators of Official Integrations:
- **Image/logo references**: Lines starting with `- <img` (official servers always have company logos)
- **"Official" in the entry**: Phrases like "official MCP server", "officially maintained", "official integration"
- **Company-maintained language**: "maintained by [Company]", "[Company]'s MCP server"
- **Professional formatting**: Structured entries with company branding
- **GitHub organization match**: When the GitHub org matches a known company name

### General Decision Rules
- Only label PRs when >90% certain based on the title and description
- Look for explicit mentions of:
  - File paths (e.g., "src/filesystem/", "README.md")
  - Server names (e.g., "filesystem server", "git MCP")
  - Section names (e.g., "community servers", "official integrations")
  - Keywords indicating bugs (e.g., "fix", "broken", "error") or enhancements (e.g., "improve", "add feature", "optimize")

## Workflow Commands

1. Fetch PRs (20 at a time):

```shell
gh api repos/modelcontextprotocol/servers/pulls -X GET -f per_page=20 -f state=open -f page=<page_number> --jq '[.[] | {number: .number, title: .title, labels: [.labels[].name], description: .body}]'
```

2. Add labels to a PR:

```shell
gh pr edit <pr_number> --repo modelcontextprotocol/servers --add-label "<label1>,<label2>"
```

## Examples

### Official Integration Examples
- PR titled "Add Stripe official MCP server" → `add-official-server`
- PR with description containing `- <img height="12" width="12" src="..."> **[CompanyName]**` → `add-official-server`
- PR titled "Add AWS MCP server by AWS Labs" → `add-official-server`
- PR body mentions "official integration maintained by [Company]" → `add-official-server`

### Other Examples
- PR titled "Fix filesystem server permission error" → `server-filesystem`, `bug`
- PR titled "Add OpenAI MCP server to community list" → `add-community-server`
- PR titled "Update git server to support sparse checkout" → `server-git`, `enhancement`
- PR with vague title like "Update server" → Skip labeling (not >90% certain)

Remember: When in doubt, don't label. It's better to skip uncertain PRs than to mislabel them.
