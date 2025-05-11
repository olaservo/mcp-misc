#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const PING_PATTERN = "^ping$";

const server = new McpServer(
  {
    name: "example-servers/pingpong",
    version: "1.0.0",
  }
);

// Register the pingpong tool with debug logging
server.tool(
  'pingPong',
  'Handles ping-pong protocol',
  {
    type: "object",
    required: ["message"],
    properties: {
      message: {
        type: "string",
        pattern: PING_PATTERN
      }
    }
  },
  async (params) => {
    // Deep debug logging
    console.error('[DEBUG] pingPong tool invoked');
    console.error('[DEBUG] params:', JSON.stringify(params));
    console.error('[DEBUG] typeof params:', typeof params);
    if (params && typeof params === 'object') {
      console.error('[DEBUG] params keys:', Object.keys(params));
      for (const [k, v] of Object.entries(params)) {
        console.error(`[DEBUG] param key: ${k}, value:`, v, 'typeof:', typeof v);
      }
    }

    // Try both possible locations
    const msg = params?.message ?? params?.arguments?.message;
    console.error('[DEBUG] msg:', msg);
    console.error('[DEBUG] params.message:', params?.message);
    console.error('[DEBUG] params.arguments?.message:', params?.arguments?.message);

    return {
      content: [{
        type: "text",
        text: msg === "ping" ? "pong" : "Invalid message"
      }]
    };
  }
);

console.error('Starting pingpong server...');

async function main() {
  const transport = new StdioServerTransport();
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
