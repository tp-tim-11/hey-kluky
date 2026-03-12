import { createOpencodeClient } from "@opencode-ai/sdk";

const OPENCODE_URL = process.env.OPENCODE_URL || "http://localhost:4096";
const OPENCODE_PROVIDER_ID = process.env.OPENCODE_PROVIDER_ID || "github-copilot";
const OPENCODE_MODEL_ID = process.env.OPENCODE_MODEL_ID || "gpt-4.1";

let client = null;

function getClient() {
  if (!client) {
    client = createOpencodeClient({
      baseUrl: OPENCODE_URL,
    });
  }
  return client;
}

async function createSession() {
  const sdk = getClient();
  const session = await sdk.session.create({
    body: { title: "Voice Session" },
  });
  return session.data.id;
}

async function sendContext(text, testDir, sessionId) {
  const sdk = getClient();

  // Reuse provided session or create a new one
  if (!sessionId) {
    sessionId = await createSession();
  }

  // Use raw client post for direct API call
  const response = await sdk._client.post({
    url: `/session/${sessionId}/message`,
    body: {
      directory: testDir,
      model: { providerID: OPENCODE_PROVIDER_ID, modelID: OPENCODE_MODEL_ID },
      mode: "plan",
      parts: [{ type: "text", text }],
    },
    headers: {
      "Content-Type": "application/json",
    },
  });

  const data = response.data;

  // Extract text from parts
  const output = data?.parts
    ?.filter(p => p.type === "text")
    ?.map(p => p.text)
    ?.join("") || "";

  return { sessionId, output };
}

async function main() {
  const args = process.argv.slice(2);

  // --create-only: create a new session without sending a message
  if (args[0] === "--create-only") {
    try {
      const sessionId = await createSession();
      console.log(`SESSION:${sessionId}`);
    } catch (error) {
      console.error(`Error: ${error.message}`);
      process.exit(1);
    }
    return;
  }

  if (args.length < 2) {
    console.error("Error: Missing arguments. Usage: node index.js <text> <testDir> [sessionId]");
    process.exit(1);
  }

  const text = args[0];
  const testDir = args[1];
  const sessionId = args[2] || null; // Optional 3rd argument

  try {
    const result = await sendContext(text, testDir, sessionId);
    // First line is SESSION:<id>, remaining lines are the response
    console.log(`SESSION:${result.sessionId}`);
    console.log(result.output);
  } catch (error) {
    console.error(`Error: ${error.message}`);
    process.exit(1);
  }
}

main();
