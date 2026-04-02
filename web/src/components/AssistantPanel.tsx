"use client";

import { useEffect, useState } from "react";
import { getAIHistory } from "@/lib/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";

interface AssistantPanelProps {
  context?: string;
  compact?: boolean;
  districtId?: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
}

const prompts = [
  "Summarize the latest simulation in simple terms.",
  "Which district improved the most with RL?",
  "Recommend settings for heavy east-west traffic.",
  "Explain why emergency wait time increased.",
];

export function AssistantPanel({ context, compact, districtId }: AssistantPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Ask me about district performance, simulations, or recommended parameters.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!districtId) {
      return;
    }
    getAIHistory(districtId)
      .then((data) => {
        const history = (data.history ?? []).slice().reverse();
        if (history.length > 0) {
          setMessages(
            history.map((entry) => ({
              role: entry.role,
              content: entry.content,
            })),
          );
        }
      })
      .catch(() => undefined);
  }, [districtId]);

  async function sendMessage(content: string) {
    if (!content.trim()) {
      return;
    }

    const nextMessages: Message[] = [...messages, { role: "user", content }];
    setMessages(nextMessages);
    setInput("");
    setLoading(true);

    try {
      if (districtId) {
        await fetch(
          `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/api/districts/${districtId}/ai/history`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ district_id: districtId, role: "user", content }),
            credentials: "include",
          },
        );
      }

      const response = await fetch("/api/ai/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: nextMessages, context }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.error || "Assistant request failed.");
      }

      const assistantMessage: Message = { role: "assistant", content: data.output };
      setMessages([...nextMessages, assistantMessage]);

      if (districtId) {
        await fetch(
          `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/api/districts/${districtId}/ai/history`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ district_id: districtId, role: "assistant", content: data.output }),
            credentials: "include",
          },
        );
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Assistant unavailable.";
      setMessages([...nextMessages, { role: "assistant", content: message }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className={compact ? "p-0" : "p-0"}>
      <CardContent className={compact ? "p-4" : "p-5"}>
        <div className="flex items-center justify-between">
          <div>
            <p className="eyebrow">AI Assistant</p>
            <h3 className="text-lg font-semibold">Ops Copilot</h3>
          </div>
          <Badge variant="info">LLM Live</Badge>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {prompts.map((prompt) => (
            <Button
              key={prompt}
              variant="outline"
              size="sm"
              onClick={() => sendMessage(prompt)}
              type="button"
            >
              {prompt}
            </Button>
          ))}
        </div>

        <div className="mt-4 max-h-72 space-y-3 overflow-y-auto">
          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`rounded-lg px-3 py-2 text-sm shadow-soft ${
                message.role === "user"
                  ? "bg-surface text-ink border border-accent/30 ml-6"
                  : "bg-surface-2 text-ink border border-border"
              }`}
            >
              {message.content}
            </div>
          ))}
        </div>

        <div className="mt-4 flex gap-2">
          <Input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask the assistant..."
          />
          <Button onClick={() => sendMessage(input)} disabled={loading} type="button">
            {loading ? "Sending..." : "Send"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
