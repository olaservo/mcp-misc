import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
  ToolSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";
import { zodToJsonSchema } from "zod-to-json-schema";

const ToolInputSchema = ToolSchema.shape.inputSchema;
type ToolInput = z.infer<typeof ToolInputSchema>;

/* Input schemas for tools implemented in this server */

// Basic Tools
const EchoSchema = z.object({
  message: z.string().describe("Message to echo back"),
});

const AddSchema = z.object({
  a: z.number().describe("First number"),
  b: z.number().describe("Second number"),
});

const GetCurrentTimeSchema = z.object({
  timezone: z.string().optional().describe("Timezone (e.g., 'UTC', 'America/New_York'). Defaults to local timezone."),
});

// Text Processing Tools
const ReverseTextSchema = z.object({
  text: z.string().describe("Text to reverse"),
});

const CountWordsSchema = z.object({
  text: z.string().describe("Text to count words in"),
  includeSpaces: z.boolean().default(false).describe("Whether to include spaces in the count"),
});

const GenerateUuidSchema = z.object({
  version: z.enum(["v4"]).default("v4").describe("UUID version to generate"),
});

// Data Tools
const ValidateEmailSchema = z.object({
  email: z.string().describe("Email address to validate"),
});

const ParseJsonSchema = z.object({
  jsonString: z.string().describe("JSON string to parse"),
  strict: z.boolean().default(true).describe("Whether to use strict JSON parsing"),
});

const FormatDataSchema = z.object({
  data: z.any().describe("Data to format"),
  format: z.enum(["json", "yaml", "table"]).default("json").describe("Output format"),
});

// Advanced Features
const LongRunningTaskSchema = z.object({
  duration: z.number().default(5).describe("Duration of the task in seconds"),
  steps: z.number().default(3).describe("Number of steps in the task"),
  taskName: z.string().default("Processing").describe("Name of the task"),
});

const AnnotatedResponseSchema = z.object({
  messageType: z.enum(["info", "warning", "error", "success"]).describe("Type of message"),
  includeMetadata: z.boolean().default(true).describe("Whether to include metadata"),
});

const ImageGeneratorSchema = z.object({
  type: z.enum(["sample", "placeholder"]).default("sample").describe("Type of image to generate"),
});

// System Tools
const GetSystemInfoSchema = z.object({
  includeEnv: z.boolean().default(false).describe("Whether to include environment variables"),
});

const ListFilesSchema = z.object({
  directory: z.string().default(".").describe("Directory to list (simulated)"),
  includeHidden: z.boolean().default(false).describe("Whether to include hidden files"),
});

enum ToolName {
  // Basic Tools
  ECHO = "echo",
  ADD = "add", 
  GET_CURRENT_TIME = "getCurrentTime",
  
  // Text Processing Tools
  REVERSE_TEXT = "reverseText",
  COUNT_WORDS = "countWords",
  GENERATE_UUID = "generateUuid",
  
  // Data Tools
  VALIDATE_EMAIL = "validateEmail",
  PARSE_JSON = "parseJson",
  FORMAT_DATA = "formatData",
  
  // Advanced Features
  LONG_RUNNING_TASK = "longRunningTask",
  ANNOTATED_RESPONSE = "annotatedResponse",
  IMAGE_GENERATOR = "imageGenerator",
  
  // System Tools
  GET_SYSTEM_INFO = "getSystemInfo",
  LIST_FILES = "listFiles",
}

// Helper functions
function generateUuid(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

function validateEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

function formatAsTable(data: any): string {
  if (Array.isArray(data)) {
    if (data.length === 0) return "Empty array";
    
    const headers = Object.keys(data[0]);
    let table = headers.join(" | ") + "\n";
    table += headers.map(() => "---").join(" | ") + "\n";
    
    for (const row of data) {
      table += headers.map(h => String(row[h] || "")).join(" | ") + "\n";
    }
    
    return table;
  } else if (typeof data === 'object' && data !== null) {
    let table = "Key | Value\n--- | ---\n";
    for (const [key, value] of Object.entries(data)) {
      table += `${key} | ${String(value)}\n`;
    }
    return table;
  }
  
  return String(data);
}

function formatAsYaml(data: any): string {
  // Simple YAML-like formatting
  function yamlify(obj: any, indent = 0): string {
    const spaces = "  ".repeat(indent);
    
    if (Array.isArray(obj)) {
      return obj.map(item => `${spaces}- ${yamlify(item, 0)}`).join("\n");
    } else if (typeof obj === 'object' && obj !== null) {
      return Object.entries(obj)
        .map(([key, value]) => {
          if (typeof value === 'object' && value !== null) {
            return `${spaces}${key}:\n${yamlify(value, indent + 1)}`;
          } else {
            return `${spaces}${key}: ${String(value)}`;
          }
        })
        .join("\n");
    } else {
      return String(obj);
    }
  }
  
  return yamlify(data);
}

// Sample tiny image (1x1 pixel PNG)
const SAMPLE_IMAGE = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==";

export const createServer = () => {
  const server = new Server(
    {
      name: "example-servers/example-tools",
      version: "1.0.0",
    },
    {
      capabilities: {
        tools: {},
      },
    }
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => {
    const tools: Tool[] = [
      // Basic Tools
      {
        name: ToolName.ECHO,
        description: "Echoes back the input message",
        inputSchema: zodToJsonSchema(EchoSchema) as ToolInput,
      },
      {
        name: ToolName.ADD,
        description: "Adds two numbers together",
        inputSchema: zodToJsonSchema(AddSchema) as ToolInput,
      },
      {
        name: ToolName.GET_CURRENT_TIME,
        description: "Gets the current date and time",
        inputSchema: zodToJsonSchema(GetCurrentTimeSchema) as ToolInput,
      },
      
      // Text Processing Tools
      {
        name: ToolName.REVERSE_TEXT,
        description: "Reverses the input text",
        inputSchema: zodToJsonSchema(ReverseTextSchema) as ToolInput,
      },
      {
        name: ToolName.COUNT_WORDS,
        description: "Counts words in the input text",
        inputSchema: zodToJsonSchema(CountWordsSchema) as ToolInput,
      },
      {
        name: ToolName.GENERATE_UUID,
        description: "Generates a UUID",
        inputSchema: zodToJsonSchema(GenerateUuidSchema) as ToolInput,
      },
      
      // Data Tools
      {
        name: ToolName.VALIDATE_EMAIL,
        description: "Validates an email address format",
        inputSchema: zodToJsonSchema(ValidateEmailSchema) as ToolInput,
      },
      {
        name: ToolName.PARSE_JSON,
        description: "Parses a JSON string and validates it",
        inputSchema: zodToJsonSchema(ParseJsonSchema) as ToolInput,
      },
      {
        name: ToolName.FORMAT_DATA,
        description: "Formats data in different output formats",
        inputSchema: zodToJsonSchema(FormatDataSchema) as ToolInput,
      },
      
      // Advanced Features
      {
        name: ToolName.LONG_RUNNING_TASK,
        description: "Demonstrates a long-running task with progress updates",
        inputSchema: zodToJsonSchema(LongRunningTaskSchema) as ToolInput,
      },
      {
        name: ToolName.ANNOTATED_RESPONSE,
        description: "Demonstrates annotated responses with metadata",
        inputSchema: zodToJsonSchema(AnnotatedResponseSchema) as ToolInput,
      },
      {
        name: ToolName.IMAGE_GENERATOR,
        description: "Generates sample images",
        inputSchema: zodToJsonSchema(ImageGeneratorSchema) as ToolInput,
      },
      
      // System Tools
      {
        name: ToolName.GET_SYSTEM_INFO,
        description: "Gets system information",
        inputSchema: zodToJsonSchema(GetSystemInfoSchema) as ToolInput,
      },
      {
        name: ToolName.LIST_FILES,
        description: "Lists files in a directory (simulated)",
        inputSchema: zodToJsonSchema(ListFilesSchema) as ToolInput,
      },
    ];

    return { tools };
  });

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    // Basic Tools
    if (name === ToolName.ECHO) {
      const validatedArgs = EchoSchema.parse(args);
      return {
        content: [{ type: "text", text: `Echo: ${validatedArgs.message}` }],
      };
    }

    if (name === ToolName.ADD) {
      const validatedArgs = AddSchema.parse(args);
      const sum = validatedArgs.a + validatedArgs.b;
      return {
        content: [
          {
            type: "text",
            text: `The sum of ${validatedArgs.a} and ${validatedArgs.b} is ${sum}.`,
          },
        ],
      };
    }

    if (name === ToolName.GET_CURRENT_TIME) {
      const validatedArgs = GetCurrentTimeSchema.parse(args);
      const now = new Date();
      
      let timeString: string;
      if (validatedArgs.timezone) {
        try {
          timeString = now.toLocaleString("en-US", { timeZone: validatedArgs.timezone });
        } catch (error) {
          throw new Error(`Invalid timezone: ${validatedArgs.timezone}`);
        }
      } else {
        timeString = now.toLocaleString();
      }
      
      return {
        content: [
          {
            type: "text",
            text: `Current time: ${timeString}${validatedArgs.timezone ? ` (${validatedArgs.timezone})` : " (local timezone)"}`,
          },
        ],
      };
    }

    // Text Processing Tools
    if (name === ToolName.REVERSE_TEXT) {
      const validatedArgs = ReverseTextSchema.parse(args);
      const reversed = validatedArgs.text.split("").reverse().join("");
      return {
        content: [
          {
            type: "text",
            text: `Original: "${validatedArgs.text}"\nReversed: "${reversed}"`,
          },
        ],
      };
    }

    if (name === ToolName.COUNT_WORDS) {
      const validatedArgs = CountWordsSchema.parse(args);
      const words = validatedArgs.text.trim().split(/\s+/).filter(word => word.length > 0);
      const wordCount = words.length;
      const charCount = validatedArgs.text.length;
      const charCountNoSpaces = validatedArgs.text.replace(/\s/g, "").length;
      
      return {
        content: [
          {
            type: "text",
            text: `Text analysis:
- Words: ${wordCount}
- Characters: ${charCount}
- Characters (no spaces): ${charCountNoSpaces}
- Average word length: ${wordCount > 0 ? (charCountNoSpaces / wordCount).toFixed(1) : 0}`,
          },
        ],
      };
    }

    if (name === ToolName.GENERATE_UUID) {
      const validatedArgs = GenerateUuidSchema.parse(args);
      const uuid = generateUuid();
      return {
        content: [
          {
            type: "text",
            text: `Generated UUID (${validatedArgs.version}): ${uuid}`,
          },
        ],
      };
    }

    // Data Tools
    if (name === ToolName.VALIDATE_EMAIL) {
      const validatedArgs = ValidateEmailSchema.parse(args);
      const isValid = validateEmail(validatedArgs.email);
      return {
        content: [
          {
            type: "text",
            text: `Email "${validatedArgs.email}" is ${isValid ? "valid" : "invalid"}.`,
          },
        ],
      };
    }

    if (name === ToolName.PARSE_JSON) {
      const validatedArgs = ParseJsonSchema.parse(args);
      try {
        const parsed = JSON.parse(validatedArgs.jsonString);
        return {
          content: [
            {
              type: "text",
              text: `JSON parsed successfully:\n${JSON.stringify(parsed, null, 2)}`,
            },
          ],
        };
      } catch (error) {
        return {
          content: [
            {
              type: "text",
              text: `JSON parsing failed: ${error instanceof Error ? error.message : "Unknown error"}`,
            },
          ],
        };
      }
    }

    if (name === ToolName.FORMAT_DATA) {
      const validatedArgs = FormatDataSchema.parse(args);
      let formatted: string;
      
      switch (validatedArgs.format) {
        case "json":
          formatted = JSON.stringify(validatedArgs.data, null, 2);
          break;
        case "yaml":
          formatted = formatAsYaml(validatedArgs.data);
          break;
        case "table":
          formatted = formatAsTable(validatedArgs.data);
          break;
        default:
          formatted = String(validatedArgs.data);
      }
      
      return {
        content: [
          {
            type: "text",
            text: `Data formatted as ${validatedArgs.format}:\n\n${formatted}`,
          },
        ],
      };
    }

    // Advanced Features
    if (name === ToolName.LONG_RUNNING_TASK) {
      const validatedArgs = LongRunningTaskSchema.parse(args);
      const { duration, steps, taskName } = validatedArgs;
      const stepDuration = duration / steps;
      const progressToken = request.params._meta?.progressToken;

      for (let i = 1; i <= steps; i++) {
        await new Promise((resolve) => setTimeout(resolve, stepDuration * 1000));

        if (progressToken !== undefined) {
          await server.notification({
            method: "notifications/progress",
            params: {
              progress: i,
              total: steps,
              progressToken,
            },
          });
        }
      }

      return {
        content: [
          {
            type: "text",
            text: `${taskName} completed! Duration: ${duration} seconds, Steps: ${steps}.`,
          },
        ],
      };
    }

    if (name === ToolName.ANNOTATED_RESPONSE) {
      const validatedArgs = AnnotatedResponseSchema.parse(args);
      const { messageType, includeMetadata } = validatedArgs;
      
      const content = [];
      
      // Main message with annotations based on type
      const priorities = { info: 0.5, warning: 0.7, error: 1.0, success: 0.6 };
      const audiences = { 
        info: ["user", "assistant"], 
        warning: ["user"], 
        error: ["user", "assistant"], 
        success: ["user"] 
      };
      
      content.push({
        type: "text",
        text: `This is a ${messageType} message demonstrating annotations.`,
        annotations: {
          priority: priorities[messageType],
          audience: audiences[messageType],
          messageType: messageType,
        },
      });
      
      if (includeMetadata) {
        content.push({
          type: "text",
          text: `Metadata: Generated at ${new Date().toISOString()}`,
          annotations: {
            priority: 0.2,
            audience: ["assistant"],
            category: "metadata",
          },
        });
      }
      
      return { content };
    }

    if (name === ToolName.IMAGE_GENERATOR) {
      const validatedArgs = ImageGeneratorSchema.parse(args);
      
      return {
        content: [
          {
            type: "text",
            text: `Generated ${validatedArgs.type} image:`,
          },
          {
            type: "image",
            data: SAMPLE_IMAGE,
            mimeType: "image/png",
          },
          {
            type: "text",
            text: "This is a sample 1x1 pixel image for demonstration purposes.",
          },
        ],
      };
    }

    // System Tools
    if (name === ToolName.GET_SYSTEM_INFO) {
      const validatedArgs = GetSystemInfoSchema.parse(args);
      
      const systemInfo = {
        platform: process.platform,
        nodeVersion: process.version,
        architecture: process.arch,
        uptime: process.uptime(),
        memoryUsage: process.memoryUsage(),
        pid: process.pid,
      };
      
      const content = [
        {
          type: "text",
          text: `System Information:\n${JSON.stringify(systemInfo, null, 2)}`,
        },
      ];
      
      if (validatedArgs.includeEnv) {
        content.push({
          type: "text",
          text: `Environment Variables:\n${JSON.stringify(process.env, null, 2)}`,
        });
      }
      
      return { content };
    }

    if (name === ToolName.LIST_FILES) {
      const validatedArgs = ListFilesSchema.parse(args);
      
      // Simulated file listing
      const files = [
        { name: "document.txt", size: 1024, type: "file" },
        { name: "image.png", size: 2048, type: "file" },
        { name: "subfolder", size: 0, type: "directory" },
      ];
      
      if (validatedArgs.includeHidden) {
        files.push({ name: ".hidden", size: 512, type: "file" });
      }
      
      const fileList = files
        .map(f => `${f.type === "directory" ? "📁" : "📄"} ${f.name} (${f.size} bytes)`)
        .join("\n");
      
      return {
        content: [
          {
            type: "text",
            text: `Files in "${validatedArgs.directory}":\n${fileList}\n\nNote: This is a simulated file listing for demonstration purposes.`,
          },
        ],
      };
    }

    throw new Error(`Unknown tool: ${name}`);
  });

  const cleanup = async () => {
    // No cleanup needed for this server
  };

  return { server, cleanup };
};
