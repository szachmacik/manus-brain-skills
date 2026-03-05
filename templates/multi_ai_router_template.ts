/**
 * Multi-AI Router — szablon reużywalny dla projektów Manus
 * Kopiuj do: server/routers/ai.ts
 * 
 * Wymaga zmiennych środowiskowych:
 * - ANTHROPIC_API_KEY (opcjonalne — Claude)
 * - MOONSHOT_API_KEY (opcjonalne — Kimi K2)
 * - DEEPSEEK_API_KEY (opcjonalne — DeepSeek V3)
 * - BUILT_IN_FORGE_API_KEY + BUILT_IN_FORGE_API_URL (Manus built-in — zawsze dostępne)
 * 
 * Routing strategy (od najtańszego):
 * - "quick" → Manus built-in (free)
 * - "code" → DeepSeek V3 ($0.028/1M)
 * - "long" → Kimi K2 ($0.15/1M)
 * - "analysis" → Claude 3.5 Haiku ($0.25/1M)
 * - "complex" → Claude 3.5 Sonnet ($3/1M)
 * - "auto" → wybiera optymalny model automatycznie
 */

import { z } from "zod";
import { publicProcedure, router } from "../_core/trpc";
import { invokeLLM } from "../_core/llm";

// Modele i ich koszty (USD per 1M tokenów)
const AI_MODELS = {
  manus: { name: "Manus Built-in", costPer1M: 0, provider: "manus" },
  "deepseek-v3": { name: "DeepSeek V3", costPer1M: 0.028, provider: "deepseek" },
  "kimi-k2": { name: "Kimi K2 Turbo", costPer1M: 0.15, provider: "moonshot" },
  "claude-haiku": { name: "Claude 3.5 Haiku", costPer1M: 0.25, provider: "anthropic" },
  "claude-sonnet": { name: "Claude 3.5 Sonnet", costPer1M: 3.0, provider: "anthropic" },
} as const;

type ModelKey = keyof typeof AI_MODELS;

// Auto-routing na podstawie typu zadania
function selectModel(taskType: string, preferredModel?: string): ModelKey {
  if (preferredModel && preferredModel in AI_MODELS) {
    return preferredModel as ModelKey;
  }
  const routing: Record<string, ModelKey> = {
    quick: "manus",
    simple: "manus",
    code: "deepseek-v3",
    debug: "deepseek-v3",
    refactor: "deepseek-v3",
    long: "kimi-k2",
    document: "kimi-k2",
    analysis: "claude-haiku",
    review: "claude-haiku",
    complex: "claude-sonnet",
    architecture: "claude-sonnet",
    reasoning: "claude-sonnet",
    auto: "manus",
  };
  return routing[taskType] ?? "manus";
}

// Wywołanie modelu przez odpowiednie API
async function callModel(
  model: ModelKey,
  messages: Array<{ role: string; content: string }>,
  maxTokens: number = 2000
): Promise<{ content: string; tokensUsed: number; cost: number }> {
  const modelInfo = AI_MODELS[model];

  // Manus built-in — zawsze dostępny
  if (modelInfo.provider === "manus") {
    const response = await invokeLLM({ messages: messages as any, max_tokens: maxTokens });
    const tokensUsed = response.usage?.total_tokens ?? 500;
    return {
      content: response.choices[0]?.message?.content ?? "",
      tokensUsed,
      cost: 0,
    };
  }

  // DeepSeek — OpenAI-compatible API
  if (modelInfo.provider === "deepseek") {
    const apiKey = process.env.DEEPSEEK_API_KEY;
    if (!apiKey) throw new Error("DEEPSEEK_API_KEY not configured");
    const res = await fetch("https://api.deepseek.com/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({ model: "deepseek-chat", messages, max_tokens: maxTokens }),
    });
    const data = await res.json() as any;
    const tokensUsed = data.usage?.total_tokens ?? 500;
    return { content: data.choices[0]?.message?.content ?? "", tokensUsed, cost: (tokensUsed / 1_000_000) * modelInfo.costPer1M };
  }

  // Kimi K2 — OpenAI-compatible API
  if (modelInfo.provider === "moonshot") {
    const apiKey = process.env.MOONSHOT_API_KEY;
    if (!apiKey) throw new Error("MOONSHOT_API_KEY not configured");
    const res = await fetch("https://api.moonshot.ai/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({ model: "kimi-k2-turbo-preview", messages, max_tokens: maxTokens }),
    });
    const data = await res.json() as any;
    const tokensUsed = data.usage?.total_tokens ?? 500;
    return { content: data.choices[0]?.message?.content ?? "", tokensUsed, cost: (tokensUsed / 1_000_000) * modelInfo.costPer1M };
  }

  // Claude — Anthropic API
  if (modelInfo.provider === "anthropic") {
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) throw new Error("ANTHROPIC_API_KEY not configured");
    const claudeModel = model === "claude-sonnet" ? "claude-3-5-sonnet-20241022" : "claude-3-5-haiku-20241022";
    const systemMsg = messages.find(m => m.role === "system")?.content;
    const userMessages = messages.filter(m => m.role !== "system");
    const res = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-api-key": apiKey, "anthropic-version": "2023-06-01" },
      body: JSON.stringify({ model: claudeModel, max_tokens: maxTokens, system: systemMsg, messages: userMessages }),
    });
    const data = await res.json() as any;
    const tokensUsed = (data.usage?.input_tokens ?? 0) + (data.usage?.output_tokens ?? 0);
    return { content: data.content?.[0]?.text ?? "", tokensUsed, cost: (tokensUsed / 1_000_000) * modelInfo.costPer1M };
  }

  throw new Error(`Unknown provider: ${modelInfo.provider}`);
}

export const aiRouter = router({
  // Główny endpoint — wyślij prompt do wybranego modelu
  chat: publicProcedure
    .input(z.object({
      prompt: z.string().min(1).max(10000),
      systemPrompt: z.string().optional(),
      taskType: z.enum(["quick", "simple", "code", "debug", "refactor", "long", "document", "analysis", "review", "complex", "architecture", "reasoning", "auto"]).default("auto"),
      preferredModel: z.string().optional(),
      maxTokens: z.number().min(100).max(8000).default(2000),
    }))
    .mutation(async ({ input }) => {
      const model = selectModel(input.taskType, input.preferredModel);
      const messages = [
        ...(input.systemPrompt ? [{ role: "system", content: input.systemPrompt }] : []),
        { role: "user", content: input.prompt },
      ];

      let result;
      let usedModel = model;

      try {
        result = await callModel(model, messages, input.maxTokens);
      } catch (err) {
        // Fallback do Manus built-in
        console.warn(`[AI Router] ${model} failed, falling back to manus:`, err);
        usedModel = "manus";
        result = await callModel("manus", messages, input.maxTokens);
      }

      return {
        content: result.content,
        model: usedModel,
        modelName: AI_MODELS[usedModel].name,
        tokensUsed: result.tokensUsed,
        estimatedCost: result.cost,
        taskType: input.taskType,
      };
    }),

  // Lista dostępnych modeli
  listModels: publicProcedure.query(() => {
    return Object.entries(AI_MODELS).map(([key, info]) => ({
      id: key,
      name: info.name,
      costPer1M: info.costPer1M,
      available: key === "manus" ||
        (key.startsWith("deepseek") && !!process.env.DEEPSEEK_API_KEY) ||
        (key.startsWith("kimi") && !!process.env.MOONSHOT_API_KEY) ||
        (key.startsWith("claude") && !!process.env.ANTHROPIC_API_KEY),
    }));
  }),
});
