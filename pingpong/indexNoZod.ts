#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";

const PING_PATTERN = "^ping$";

const PingPongSchema = {
  type: "object" as const,
  properties: {
    message: {
      type: "string",
      pattern: PING_PATTERN,
      description: "Message must be 'ping'"
    }
  },
  required: ["message"]
};

function validatePingPongInput(args: unknown): { message: string } {
  if (typeof args !== 'object' || args === null) {
    throw new Error('Arguments must be an object');
  }

  const { message } = args as any;
  if (typeof message !== 'string') {
    throw new Error('Message must be a string');
  }

  if (!new RegExp(PING_PATTERN).test(message)) {
    throw new Error('Message must be exactly "ping"');
  }

  return { message };
}

const createServer = () => {
  const server = new Server(
    {
      name: "example-servers/pingpong",
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
      {
        name: "pingPong",
        description: "Handles ping-pong protocol",
        inputSchema: PingPongSchema,
      },
    ];

    return { tools };
  });

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    if (name === "pingPong") {
      const validatedArgs = validatePingPongInput(args);
      return {
        content: [{
          type: "text",
          text: "pong"
        }]
      };
    }

    throw new Error(`Unknown tool: ${name}`);
  });

  return { server };
};

console.error('Starting pingpong server...');

async function main() {
  const transport = new StdioServerTransport();
  const {server} = createServer();

  await server.connect(transport);

  // Cleanup on exit
  process.on("SIGINT", async () => {
    await server.close();
    process.exit(0);
  });
}

main().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});
