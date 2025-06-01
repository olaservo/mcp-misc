# Example Resources MCP Server

This MCP server demonstrates the Model Context Protocol (MCP) resource capabilities. It provides various example resources to showcase different resource patterns, URI templates, and features like pagination and subscriptions.

## Overview

The example-resources server is designed to help developers understand how to implement and work with MCP resources. It provides no tools or prompts - only resources with different data types and access patterns.

## Features

### Resource Types

The server provides four different types of resources to demonstrate various MCP resource patterns:

#### 1. Static Resources
- **URI Pattern**: `test://static/resource/{id}` (where id is 1-100)
- **Description**: 100 numbered static resources
- **Content Types**:
  - Even numbered resources: Plain text format
  - Odd numbered resources: Base64 encoded binary data
- **Pagination**: Supports pagination with 10 items per page
- **Subscription**: Supports resource update subscriptions (updates every 10 seconds)

#### 2. Search Resources
- **URI Pattern**: `test://search{?q}`
- **Description**: Searchable resources with query parameter
- **Parameters**:
  - `q` (required): Search query string
- **Returns**: JSON with search results matching the query

#### 3. User List Resources
- **URI Pattern**: `test://users{?name,limit,offset}`
- **Description**: User listing with filtering and pagination
- **Parameters**:
  - `name` (optional): Filter users by name
  - `limit` (optional, default: 10): Number of users to return (1-100)
  - `offset` (optional, default: 0): Pagination offset
- **Returns**: JSON with filtered and paginated user data

#### 4. Post Resources
- **URI Pattern**: `test://api/v1/posts/{id}{?include,format}`
- **Description**: Blog post resources with optional includes and format options
- **Parameters**:
  - `id` (required): Post ID (numeric)
  - `include` (optional): Comma-separated list of additional data to include (`comments`, `author`, `stats`)
  - `format` (optional, default: json): Response format (`json`, `xml`, `yaml`)
- **Returns**: Post data in the specified format with optional additional data

### Resource Capabilities

- **Resource Templates**: Provides URI templates for all resource types
- **Pagination**: Demonstrates cursor-based pagination for static resources
- **Subscriptions**: Supports subscribing to resource updates
- **Parameter Validation**: Shows proper parameter validation and error handling
- **Multiple Formats**: Demonstrates serving resources in different formats (JSON, XML, YAML)

## Installation and Usage

This is a local development project that needs to be built from source.

### Building the Project

```shell
cd example-resources
npm install
npm run build
```

### Usage with Claude Desktop

After building, add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "example-resources": {
      "command": "node",
      "args": [
        "/path/to/your/project/example-resources/dist/index.js"
      ]
    }
  }
}
```

### Usage with VS Code

After building, add the following to your VS Code User Settings (JSON) or `.vscode/mcp.json`:

```json
{
  "mcp": {
    "servers": {
      "example-resources": {
        "command": "node",
        "args": ["/path/to/your/project/example-resources/dist/index.js"]
      }
    }
  }
}
```

**Note**: Replace `/path/to/your/project/` with the actual path to where you've cloned this repository.

## Development

### Running from Source

#### Default (STDIO) Transport
```shell
cd example-resources
npm install
npm run build
npm start
```

#### SSE Transport (deprecated)
```shell
npm run start:sse
```

#### Streamable HTTP Transport
```shell
npm run start:streamableHttp
```

### Building
```shell
npm run build
```

### Development Mode
```shell
npm run watch
```

## Example Resource URIs

Here are some example URIs you can use to test the different resource types:

### Static Resources
- `test://static/resource/1` - First static resource (binary)
- `test://static/resource/2` - Second static resource (text)
- `test://static/resource/50` - Fiftieth static resource (text)

### Search Resources
- `test://search?q=javascript` - Search for "javascript"
- `test://search?q=api` - Search for "api"

### User Resources
- `test://users` - List all users (default pagination)
- `test://users?name=john` - Filter users by name containing "john"
- `test://users?limit=5&offset=0` - Get first 5 users
- `test://users?name=jane&limit=2` - Filter by name and limit results

### Post Resources
- `test://api/v1/posts/1` - Get post 1 in JSON format
- `test://api/v1/posts/1?include=comments,author` - Get post 1 with comments and author details
- `test://api/v1/posts/1?format=xml` - Get post 1 in XML format
- `test://api/v1/posts/1?include=stats&format=yaml` - Get post 1 with stats in YAML format

## Transport Support

The server supports three MCP transport methods:

1. **STDIO** (default): Standard input/output transport
2. **SSE**: Server-Sent Events over HTTP (deprecated as of MCP 2025-03-26)
3. **Streamable HTTP**: Modern HTTP-based transport

Use the appropriate script or command line argument to select the transport method.
