import { NextResponse } from "next/server";

const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const OPENAI_MODEL = process.env.OPENAI_MODEL ?? "gpt-4o-mini";

function extractOutput(payload: any): string {
  if (payload?.output_text) {
    return payload.output_text;
  }
  const output = payload?.output ?? [];
  const texts: string[] = [];
  for (const item of output) {
    for (const content of item.content ?? []) {
      if (content.type === "output_text" && typeof content.text === "string") {
        texts.push(content.text);
      }
    }
  }
  return texts.join("\n").trim();
}

export async function POST(request: Request) {
  if (!OPENAI_API_KEY) {
    return NextResponse.json({ error: "OPENAI_API_KEY is not configured." }, { status: 500 });
  }

  const body = await request.json();
  const kind = body.kind ?? "summary";
  const payload = body.payload ?? {};

  const system =
    "You are the FlowMind Ops Assistant. Generate concise operations summaries for city managers. " +
    "Never invent metrics that are not provided.";

  const prompt = `Summary type: ${kind}\nData: ${JSON.stringify(payload)}`;

  try {
    const response = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${OPENAI_API_KEY}`,
      },
      body: JSON.stringify({
        model: OPENAI_MODEL,
        input: [
          { role: "system", content: system },
          { role: "user", content: prompt },
        ],
        temperature: 0.2,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      return NextResponse.json({ error: data?.error?.message ?? "OpenAI request failed." }, { status: 500 });
    }

    const output = extractOutput(data) || "No summary generated.";
    return NextResponse.json({ output });
  } catch (error) {
    const message = error instanceof Error ? error.message : "OpenAI request failed.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
