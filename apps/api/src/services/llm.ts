import Anthropic from "@anthropic-ai/sdk";
import type { Message, MessageParam } from "@anthropic-ai/sdk/resources/messages";

const HAIKU = "claude-haiku-4-5-20251001";
const SONNET = "claude-sonnet-4-20250514";

let client: Anthropic | null = null;

function getClient(): Anthropic {
  const k = process.env.ANTHROPIC_API_KEY;
  if (!k) throw new Error("ANTHROPIC_API_KEY missing");
  if (!client) client = new Anthropic({ apiKey: k });
  return client;
}

function extractText(content: Message["content"]): string {
  for (const b of content) {
    if (b.type === "text") return b.text.trim();
  }
  return "";
}

export async function completeHaiku(
  userPrompt: string,
  maxTokens: number
): Promise<string> {
  const r = await getClient().messages.create({
    model: HAIKU,
    max_tokens: maxTokens,
    messages: [{ role: "user", content: userPrompt }],
  });
  return extractText(r.content);
}

export async function completeSonnet(input: {
  system: string;
  messages: MessageParam[];
  maxTokens: number;
}): Promise<string> {
  const r = await getClient().messages.create({
    model: SONNET,
    max_tokens: input.maxTokens,
    system: input.system,
    messages: input.messages,
  });
  return extractText(r.content);
}
