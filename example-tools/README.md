# Example Tools MCP Server

This is an example MCP (Model Context Protocol) server that demonstrates various tool implementations. It provides a comprehensive set of tools showcasing different capabilities and patterns for MCP tool development.

## Features

This server demonstrates:

- **Basic Tools**: Simple operations like echo, addition, and time retrieval
- **Text Processing**: String manipulation, word counting, and UUID generation
- **Data Tools**: Email validation, JSON parsing, and data formatting
- **Advanced Features**: Long-running tasks with progress updates, annotated responses, and image generation
- **System Tools**: System information retrieval and file listing (simulated)

## Tools Available

### Basic Tools
- `echo` - Echoes back the input message
- `add` - Adds two numbers together
- `getCurrentTime` - Gets the current date and time with optional timezone

### Text Processing Tools
- `reverseText` - Reverses the input text
- `countWords` - Counts words and analyzes text
- `generateUuid` - Generates a UUID

### Data Tools
- `validateEmail` - Validates an email address format
- `parseJson` - Parses and validates JSON strings
- `formatData` - Formats data in different output formats (JSON, YAML, table)

### Advanced Features
- `longRunningTask` - Demonstrates progress updates for long-running operations
- `annotatedResponse` - Shows how to use annotations with metadata
- `imageGenerator` - Returns sample images

### System Tools
- `getSystemInfo` - Gets system information (with optional environment variables)
- `listFiles` - Lists files in a directory (simulated for demonstration)

## Installation

```bash
npm install
```

## Usage

The server supports multiple transport methods:

### STDIO Transport (Default)
```bash
npm start
# or
node dist/index.js stdio
```

### SSE (Server-Sent Events) Transport
```bash
npm run start:sse
# or
node dist/index.js sse
```

### Streamable HTTP Transport
```bash
npm run start:streamableHttp
# or
node dist/index.js streamableHttp
```

## Development

### Building
```bash
npm run build
```

### Watching for changes
```bash
npm run watch
```

## Example Tool Usage

### Basic Echo
```json
{
  "method": "tools/call",
  "params": {
    "name": "echo",
    "arguments": {
      "message": "Hello, MCP!"
    }
  }
}
```

### Text Analysis
```json
{
  "method": "tools/call",
  "params": {
    "name": "countWords",
    "arguments": {
      "text": "The quick brown fox jumps over the lazy dog"
    }
  }
}
```

### Data Formatting
```json
{
  "method": "tools/call",
  "params": {
    "name": "formatData",
    "arguments": {
      "data": {"name": "John", "age": 30, "city": "New York"},
      "format": "yaml"
    }
  }
}
```

### Long Running Task with Progress
```json
{
  "method": "tools/call",
  "params": {
    "name": "longRunningTask",
    "arguments": {
      "duration": 10,
      "steps": 5,
      "taskName": "Data Processing"
    }
  }
}
```

## Transport Details

### STDIO
The default transport method using standard input/output. Best for command-line integration and simple client implementations.

### SSE (Server-Sent Events)
HTTP-based transport using Server-Sent Events for real-time communication. Runs on port 3001 by default.

- Connection endpoint: `GET /sse`
- Message endpoint: `POST /message`

### Streamable HTTP
Full HTTP-based transport with session management and resumability. Runs on port 3002 by default.

- Main endpoint: `/mcp` (supports GET, POST, DELETE)
- Supports session management with `mcp-session-id` header
- Includes resumability with event store

## Architecture

The server is built using:

- **@modelcontextprotocol/sdk**: Core MCP SDK for server implementation
- **Zod**: Schema validation for tool inputs
- **Express**: HTTP server for SSE and Streamable HTTP transports
- **TypeScript**: Type-safe development

## Error Handling

All tools include proper error handling and validation:

- Input validation using Zod schemas
- Descriptive error messages
- Proper HTTP status codes for transport errors
- Graceful handling of edge cases

## Annotations

The server demonstrates MCP's annotation system for providing metadata about tool responses:

- **Priority levels**: Different importance levels for content
- **Audience targeting**: Content intended for specific audiences (user, assistant)
- **Content categorization**: Metadata for organizing responses

This makes it easier for MCP clients to handle and display tool responses appropriately.
