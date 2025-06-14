import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import {
  ListPromptsRequestSchema,
  GetPromptRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

export const createServer = () => {
  const server = new Server(
    {
      name: "example-servers/example-prompts",
      version: "1.0.0",
    },
    {
      capabilities: {
        prompts: { listChanged: true },
      },
    }
  );

  // MCP specification content for embedding in prompts
  const MCP_SPEC_CONTENT = `The Model Context Protocol (MCP) provides a standardized way for servers to expose prompt templates to clients. Prompts allow servers to provide structured messages and instructions for interacting with language models.

Key features:
- User-controlled prompt selection
- Argument templating and validation
- Multi-modal content support (text, images, audio)
- Embedded resource references
- Dynamic prompt generation`;

  // Sample tiny image for multi-modal demonstrations
  const SAMPLE_IMAGE = "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";

  // Helper function to generate code review content
  function generateCodeReview(code: string, language?: string, style?: string): string {
    const detectedLang = language || detectLanguage(code);
    const reviewStyle = style || "comprehensive";
    
    return `# Code Review for ${detectedLang.charAt(0).toUpperCase() + detectedLang.slice(1)} Code

## Code Analysis
\`\`\`${detectedLang}
${code}
\`\`\`

## Review Summary (${reviewStyle} style)
This code appears to be a ${detectedLang} implementation. Here are my observations:

### Strengths:
- Clear and readable structure
- Follows basic ${detectedLang} conventions

### Suggestions for Improvement:
- Consider adding error handling
- Add documentation/comments for better maintainability
- Review variable naming for clarity
- Consider performance optimizations if applicable

### Security Considerations:
- Validate all inputs
- Check for potential vulnerabilities
- Follow ${detectedLang} security best practices`;
  }

  // Helper function to detect programming language
  function detectLanguage(code: string): string {
    if (code.includes("def ") || code.includes("import ")) return "python";
    if (code.includes("function ") || code.includes("const ") || code.includes("=>")) return "javascript";
    if (code.includes("interface ") || code.includes(": string")) return "typescript";
    if (code.includes("public class ") || code.includes("System.out")) return "java";
    if (code.includes("#include") || code.includes("int main")) return "c++";
    return "unknown";
  }

  // Helper function to generate documentation
  function generateDocumentation(topic: string, language?: string, style?: string, detail?: string): string {
    const docStyle = style || "tutorial";
    const detailLevel = detail || "intermediate";
    const targetLang = language || "general";

    return `# ${topic} Documentation

## Overview
This ${docStyle}-style documentation covers ${topic} for ${targetLang} development.

**Detail Level:** ${detailLevel}

## Introduction
${topic} is an important concept in software development that helps developers build better applications.

## Key Concepts
- Fundamental principles
- Best practices
- Common patterns
- Implementation strategies

## Examples
\`\`\`${targetLang === "general" ? "" : targetLang}
// Example implementation will be provided here
// based on the specified language and style
\`\`\`

## Best Practices
1. Follow established conventions
2. Write clear, maintainable code
3. Include proper error handling
4. Document your implementation

## Resources
- Official documentation
- Community guides
- Example projects
- Testing frameworks`;
  }

  // Helper function to generate test cases
  function generateTestCases(component: string, framework?: string, coverage?: string): string {
    const testFramework = framework || "jest";
    const coverageType = coverage || "unit";

    return `# Test Cases for ${component}

## Test Framework: ${testFramework}
## Coverage Type: ${coverageType}

### Test Suite Structure
\`\`\`javascript
describe('${component}', () => {
  // Setup and teardown
  beforeEach(() => {
    // Initialize test environment
  });

  afterEach(() => {
    // Clean up after tests
  });

  // Test cases will be generated here
});
\`\`\`

### Core Test Cases

#### Happy Path Tests
- Valid input scenarios
- Expected behavior verification
- Success state validation

#### Edge Case Tests
- Boundary value testing
- Empty/null input handling
- Maximum/minimum limits

#### Error Handling Tests
- Invalid input scenarios
- Exception handling
- Error message validation

### ${coverageType.charAt(0).toUpperCase() + coverageType.slice(1)} Test Coverage
- Function/method coverage
- Branch coverage
- Statement coverage
- Integration points`;
  }

  server.setRequestHandler(ListPromptsRequestSchema, async (request) => {
    const cursor = request.params?.cursor;
    let startIndex = 0;
    const PAGE_SIZE = 10;

    if (cursor) {
      const decodedCursor = parseInt(atob(cursor), 10);
      if (!isNaN(decodedCursor)) {
        startIndex = decodedCursor;
      }
    }

    const allPrompts = [
      {
        name: "code_review",
        description: "Analyze code quality and suggest improvements",
        arguments: [
          {
            name: "code",
            description: "The code to review",
            required: true
          },
          {
            name: "language",
            description: "Programming language (auto-detected if not specified)",
            required: false
          },
          {
            name: "style",
            description: "Documentation style: tutorial, reference, api",
            required: false
          },
          {
            name: "detail",
            description: "Detail level: basic, intermediate, comprehensive",
            required: false
          }
        ]
      },
      {
        name: "explain_concept",
        description: "Explain technical concepts clearly with examples",
        arguments: [
          {
            name: "concept",
            description: "The technical concept to explain",
            required: true
          },
          {
            name: "audience",
            description: "Target audience: beginner, intermediate, advanced",
            required: false
          }
        ]
      },
      {
        name: "generate_documentation",
        description: "Create comprehensive documentation for code or APIs",
        arguments: [
          {
            name: "topic",
            description: "What to document",
            required: true
          },
          {
            name: "language",
            description: "Programming language or technology",
            required: false
          },
          {
            name: "style",
            description: "Documentation style: tutorial, reference, api",
            required: false
          },
          {
            name: "detail",
            description: "Detail level: basic, intermediate, comprehensive",
            required: false
          }
        ]
      },
      {
        name: "create_test_cases",
        description: "Generate comprehensive test cases for components",
        arguments: [
          {
            name: "component",
            description: "Component or function to test",
            required: true
          },
          {
            name: "framework",
            description: "Testing framework: jest, mocha, pytest, junit",
            required: false
          },
          {
            name: "coverage",
            description: "Coverage type: unit, integration, e2e",
            required: false
          }
        ]
      },
      {
        name: "debug_assistance",
        description: "Help debug code issues and errors",
        arguments: [
          {
            name: "error",
            description: "Error message or description",
            required: true
          },
          {
            name: "code",
            description: "Relevant code snippet",
            required: false
          },
          {
            name: "language",
            description: "Programming language",
            required: false
          }
        ]
      },
      {
        name: "project_analysis",
        description: "Comprehensive project analysis with MCP specification context",
        arguments: [
          {
            name: "project_type",
            description: "Type of project to analyze",
            required: true
          },
          {
            name: "focus_area",
            description: "Specific area to focus on: architecture, performance, security",
            required: false
          }
        ]
      },
      {
        name: "multi_modal_demo",
        description: "Demonstrate multi-modal content with text and images",
        arguments: [
          {
            name: "topic",
            description: "Topic for the demonstration",
            required: true
          },
          {
            name: "include_image",
            description: "Whether to include sample image",
            required: false
          }
        ]
      }
    ];

    const endIndex = Math.min(startIndex + PAGE_SIZE, allPrompts.length);
    const prompts = allPrompts.slice(startIndex, endIndex);

    let nextCursor: string | undefined;
    if (endIndex < allPrompts.length) {
      nextCursor = btoa(endIndex.toString());
    }

    return {
      prompts,
      nextCursor,
    };
  });

  server.setRequestHandler(GetPromptRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    switch (name) {
      case "code_review":
        const code = args?.code;
        if (!code) {
          throw new Error("Code parameter is required for code review");
        }
        
        const language = args?.language;
        const style = args?.style;
        
        return {
          description: "Code review analysis with suggestions for improvement",
          messages: [
            {
              role: "user",
              content: {
                type: "text",
                text: generateCodeReview(code, language, style)
              }
            }
          ]
        };

      case "explain_concept":
        const concept = args?.concept;
        if (!concept) {
          throw new Error("Concept parameter is required");
        }
        
        const audience = args?.audience || "intermediate";
        
        return {
          description: `Explanation of ${concept} for ${audience} level`,
          messages: [
            {
              role: "user",
              content: {
                type: "text",
                text: `Please explain the concept of "${concept}" in a clear and comprehensive way suitable for a ${audience} audience. Include:

1. **Definition**: What is ${concept}?
2. **Key Components**: What are the main parts or aspects?
3. **How it Works**: Explain the underlying mechanisms
4. **Use Cases**: When and why would you use this?
5. **Examples**: Provide practical examples
6. **Best Practices**: What should developers keep in mind?
7. **Common Pitfalls**: What mistakes should be avoided?

Make the explanation engaging and include code examples where appropriate.`
              }
            }
          ]
        };

      case "generate_documentation":
        const topic = args?.topic;
        if (!topic) {
          throw new Error("Topic parameter is required for documentation generation");
        }
        
        const docLanguage = args?.language;
        const docStyle = args?.style;
        const detail = args?.detail;
        
        return {
          description: `Documentation generation for ${topic}`,
          messages: [
            {
              role: "user",
              content: {
                type: "text",
                text: generateDocumentation(topic, docLanguage, docStyle, detail)
              }
            }
          ]
        };

      case "create_test_cases":
        const component = args?.component;
        if (!component) {
          throw new Error("Component parameter is required for test case generation");
        }
        
        const framework = args?.framework;
        const coverage = args?.coverage;
        
        return {
          description: `Test case generation for ${component}`,
          messages: [
            {
              role: "user",
              content: {
                type: "text",
                text: generateTestCases(component, framework, coverage)
              }
            }
          ]
        };

      case "debug_assistance":
        const error = args?.error;
        if (!error) {
          throw new Error("Error parameter is required for debug assistance");
        }
        
        const debugCode = args?.code;
        const debugLanguage = args?.language;
        
        let debugPrompt = `# Debug Assistance Request

## Error Description
${error}

## Analysis Approach
Please help debug this issue by:

1. **Error Analysis**: Analyze the error message and identify potential causes
2. **Root Cause Investigation**: Suggest what might be causing this issue
3. **Solution Strategies**: Provide step-by-step debugging approaches
4. **Code Fixes**: Suggest specific code changes if applicable
5. **Prevention**: How to avoid this issue in the future

`;

        if (debugCode) {
          debugPrompt += `## Relevant Code
\`\`\`${debugLanguage || ''}
${debugCode}
\`\`\`

`;
        }

        if (debugLanguage) {
          debugPrompt += `## Language Context
This is a ${debugLanguage} related issue.

`;
        }

        debugPrompt += `Please provide a comprehensive debugging guide.`;
        
        return {
          description: "Debug assistance with error analysis and solutions",
          messages: [
            {
              role: "user",
              content: {
                type: "text",
                text: debugPrompt
              }
            }
          ]
        };

      case "project_analysis":
        const projectType = args?.project_type;
        if (!projectType) {
          throw new Error("Project type parameter is required");
        }
        
        const focusArea = args?.focus_area || "architecture";
        
        return {
          description: `Project analysis for ${projectType} with focus on ${focusArea}`,
          messages: [
            {
              role: "user",
              content: {
                type: "text",
                text: `# Project Analysis: ${projectType}

## Focus Area: ${focusArea}

Please analyze this ${projectType} project with emphasis on ${focusArea}. Consider the following aspects:

### Architecture Analysis
- Overall system design
- Component relationships
- Data flow patterns
- Scalability considerations

### MCP Integration Opportunities
${MCP_SPEC_CONTENT}

### Recommendations
Based on the analysis, provide specific recommendations for:
- Improvements to current architecture
- Best practices implementation
- Potential MCP server integration points
- Performance optimizations
- Security enhancements

### Implementation Roadmap
Suggest a phased approach for implementing the recommended changes.`
              }
            },
            {
              role: "user",
              content: {
                type: "resource",
                resource: {
                  uri: "mcp://specification/architecture",
                  text: "MCP Architecture Specification - provides detailed information about how MCP servers and clients interact, including protocol design, message flow, and integration patterns."
                }
              }
            }
          ]
        };

      case "multi_modal_demo":
        const demoTopic = args?.topic;
        if (!demoTopic) {
          throw new Error("Topic parameter is required for multi-modal demo");
        }
        
        const includeImage = args?.include_image !== "false";
        
        const messages: any[] = [
          {
            role: "user",
            content: {
              type: "text",
              text: `# Multi-Modal Content Demonstration: ${demoTopic}

This prompt demonstrates MCP's multi-modal capabilities by combining text and visual content.

## Topic Overview
${demoTopic} is an important subject that benefits from both textual explanation and visual representation.

## Key Points
- Multi-modal content enhances understanding
- Images can illustrate complex concepts
- MCP supports various content types
- Embedded resources provide additional context

## Implementation Notes
This example shows how MCP servers can provide rich, multi-modal prompt content that includes:
- Structured text with markdown formatting
- Base64-encoded images
- Embedded resource references
- Mixed content types in a single prompt`
            }
          }
        ];

        if (includeImage) {
          messages.push({
            role: "user",
            content: {
              type: "image",
              data: SAMPLE_IMAGE,
              mimeType: "image/png"
            }
          });
        }

        messages.push({
          role: "user",
          content: {
            type: "resource",
            resource: {
              uri: "mcp://demo/multi-modal-guide",
              text: "Multi-modal content guide demonstrating how to effectively combine text, images, and other media types in MCP prompts for enhanced user experience."
            }
          }
        });

        return {
          description: `Multi-modal demonstration for ${demoTopic}`,
          messages
        };

      default:
        throw new Error(`Unknown prompt: ${name}`);
    }
  });

  return { server, cleanup: async () => {} };
};
