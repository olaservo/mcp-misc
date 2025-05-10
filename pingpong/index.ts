#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
  ToolSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";
import { zodToJsonSchema } from "zod-to-json-schema";

type ToolInput = z.infer<typeof ToolSchema.shape.inputSchema>;

const PingPongSchema = z.object({
  message: z.string()
    .regex(/^ping$/)
    .describe("Message must be 'ping'"),
});

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
        inputSchema: zodToJsonSchema(PingPongSchema) as ToolInput,
      },
    ];

    return { tools };
  });

  server.setRequestHandler(CallToolRequestSchema, async (request: z.infer<typeof CallToolRequestSchema>) => {
    const { name, arguments: args } = request.params;

    if (name === "pingPong") {
      const validatedArgs = PingPongSchema.parse(args);
      return {
        content: [{
          type: "text",
          text: validatedArgs.message === "ping" ? "pong" : "Invalid message"
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
