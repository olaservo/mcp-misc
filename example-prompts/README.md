# Example Prompts MCP Server

This MCP server demonstrates the Model Context Protocol (MCP) prompt capabilities. It provides various example prompts to showcase different prompt patterns, argument handling, and features like multi-modal content and embedded resources.

## Overview

The example-prompts server is designed to help developers understand how to implement and work with MCP prompts. It provides comprehensive prompt templates that demonstrate argument validation, multi-modal content, and integration with MCP resources.

## Features

### Prompt Types

The server provides seven different types of prompts to demonstrate various MCP prompt patterns:

#### 1. Code Review
- **Name**: `code_review`
- **Description**: Analyze code quality and suggest improvements
- **Arguments**:
  - `code` (required): The code to review
  - `language` (optional): Programming language (auto-detected if not specified)
  - `style` (optional): Review style - quick, comprehensive, security-focused
- **Features**: Automatic language detection, customizable review styles

#### 2. Explain Concept
- **Name**: `explain_concept`
- **Description**: Explain technical concepts clearly with examples
- **Arguments**:
  - `concept` (required): The technical concept to explain
  - `audience` (optional): Target audience - beginner, intermediate, advanced
- **Features**: Structured explanations with examples and best practices

#### 3. Generate Documentation
- **Name**: `generate_documentation`
- **Description**: Create comprehensive documentation for code or APIs
- **Arguments**:
  - `topic` (required): What to document
  - `language` (optional): Programming language or technology
  - `style` (optional): Documentation style - tutorial, reference, api
  - `detail` (optional): Detail level - basic, intermediate, comprehensive
- **Features**: Customizable documentation templates

#### 4. Create Test Cases
- **Name**: `create_test_cases`
- **Description**: Generate comprehensive test cases for components
- **Arguments**:
  - `component` (required): Component or function to test
  - `framework` (optional): Testing framework - jest, mocha, pytest, junit
  - `coverage` (optional): Coverage type - unit, integration, e2e
- **Features**: Framework-specific test generation

#### 5. Debug Assistance
- **Name**: `debug_assistance`
- **Description**: Help debug code issues and errors
- **Arguments**:
  - `error` (required): Error message or description
  - `code` (optional): Relevant code snippet
  - `language` (optional): Programming language
- **Features**: Structured debugging approach with solutions

#### 6. Project Analysis
- **Name**: `project_analysis`
- **Description**: Comprehensive project analysis with MCP specification context
- **Arguments**:
  - `project_type` (required): Type of project to analyze
  - `focus_area` (optional): Specific area to focus on - architecture, performance, security
- **Features**: Embedded MCP specification resources, architectural recommendations

#### 7. Multi-Modal Demo
- **Name**: `multi_modal_demo`
- **Description**: Demonstrate multi-modal content with text and images
- **Arguments**:
  - `topic` (required): Topic for the demonstration
  - `include_image` (optional): Whether to include sample image
- **Features**: Text, image, and embedded resource content

### Prompt Capabilities

- **Argument Validation**: Demonstrates proper parameter validation and error handling
- **Multi-Modal Content**: Shows how to include text, images, and embedded resources
- **Dynamic Content**: Generates contextual content based on arguments
- **Embedded Resources**: Includes MCP specification content as embedded resources
- **List Change Notifications**: Supports dynamic prompt list updates

## Installation and Usage

This is a local development project that needs to be built from source.

### Building the Project

```shell
cd example-prompts
npm install
npm run build
```

### Usage with Claude Desktop

After building, add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "example-prompts": {
      "command": "node",
      "args": [
        "/path/to/your/project/example-prompts/dist/index.js"
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
      "example-prompts": {
        "command": "node",
        "args": ["/path/to/your/project/example-prompts/dist/index.js"]
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
cd example-prompts
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

## Example Prompt Usage

Here are some example prompts you can use to test the different prompt types:

### Code Review
```json
{
  "name": "code_review",
  "arguments": {
    "code": "function add(a, b) { return a + b; }",
    "language": "javascript",
    "style": "comprehensive"
  }
}
```

### Explain Concept
```json
{
  "name": "explain_concept",
  "arguments": {
    "concept": "async/await",
    "audience": "intermediate"
  }
}
```

### Generate Documentation
```json
{
  "name": "generate_documentation",
  "arguments": {
    "topic": "REST API",
    "language": "javascript",
    "style": "api",
    "detail": "comprehensive"
  }
}
```

### Create Test Cases
```json
{
  "name": "create_test_cases",
  "arguments": {
    "component": "UserService",
    "framework": "jest",
    "coverage": "unit"
  }
}
```

### Debug Assistance
```json
{
  "name": "debug_assistance",
  "arguments": {
    "error": "TypeError: Cannot read property 'length' of undefined",
    "code": "const len = arr.length;",
    "language": "javascript"
  }
}
```

### Project Analysis
```json
{
  "name": "project_analysis",
  "arguments": {
    "project_type": "React web application",
    "focus_area": "architecture"
  }
}
```

### Multi-Modal Demo
```json
{
  "name": "multi_modal_demo",
  "arguments": {
    "topic": "MCP Protocol Overview",
    "include_image": "true"
  }
}
```

## MCP Integration Features

This server demonstrates several advanced MCP features:

- **Embedded Resources**: The `project_analysis` prompt includes embedded MCP specification content
- **Multi-Modal Content**: The `multi_modal_demo` prompt combines text, images, and resources
- **Dynamic Content Generation**: All prompts generate contextual content based on provided arguments
- **Argument Validation**: Proper validation with helpful error messages
- **List Change Notifications**: Support for dynamic prompt list updates

## Transport Support

The server supports three MCP transport methods:

1. **STDIO** (default): Standard input/output transport
2. **SSE**: Server-Sent Events over HTTP (deprecated as of MCP 2025-03-26)
3. **Streamable HTTP**: Modern HTTP-based transport

Use the appropriate script or command line argument to select the transport method.
