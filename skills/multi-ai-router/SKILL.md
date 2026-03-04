# SKILL: Multi-AI Router

**Wersja:** 1.0  
**Autor:** Manus Brain System  
**Data:** 2026-03-05  
**Repozytorium:** https://github.com/szachmacik/manus-brain-skills

---

## Opis

Ten skill umożliwia Manusowi korzystanie z czterech modeli AI w jednym zunifikowanym systemie:

| Model | Provider | Endpoint | Najlepszy do |
|-------|----------|----------|--------------|
| **claude-3-5-sonnet** | Anthropic | `api.anthropic.com/v1` | Analiza, kod, długie dokumenty |
| **claude-3-haiku** | Anthropic | `api.anthropic.com/v1` | Szybkie zadania, tanie wywołania |
| **kimi-k2-turbo-preview** | Moonshot AI | `api.moonshot.ai/v1` | Bardzo długi kontekst (128K+), bazy danych |
| **deepseek-chat** | DeepSeek | `api.deepseek.com` | Najtańszy, dobry do rutynowych zadań |
| **deepseek-reasoner** | DeepSeek | `api.deepseek.com` | Rozumowanie krok po kroku (R1) |
| **manus-built-in** | Manus | `BUILT_IN_FORGE_API_URL` | Domyślny, zawsze dostępny |

---

## Konfiguracja kluczy API

Klucze przechowywane są w Dexter Vault i zmiennych środowiskowych projektu:

```
ANTHROPIC_API_KEY    — Claude (api.anthropic.com)
MOONSHOT_API_KEY     — Kimi K2 (api.moonshot.ai)
DEEPSEEK_API_KEY     — DeepSeek V3/R1 (api.deepseek.com)
```

Manus built-in jest zawsze dostępny przez `BUILT_IN_FORGE_API_KEY` + `BUILT_IN_FORGE_API_URL`.

---

## Reguły Auto-Routingu (model_routing)

System automatycznie wybiera model na podstawie zadania:

```
ANALIZA KODU / DEBUGGING          → claude-3-5-sonnet
DŁUGI KONTEKST (>50K tokenów)     → kimi-k2-turbo-preview
ROZUMOWANIE / MATEMATYKA          → deepseek-reasoner
RUTYNOWE ZADANIA / SYNTEZA        → deepseek-chat
SZYBKIE ODPOWIEDZI / KLASYFIKACJA → claude-3-haiku
DOMYŚLNE / FALLBACK               → manus-built-in
```

---

## Optymalizacja kosztów (2026)

### Cennik porównawczy (input/output per 1M tokenów)

| Model | Input | Output | Cache Input |
|-------|-------|--------|-------------|
| claude-3-5-sonnet | $3.00 | $15.00 | $0.30 |
| claude-3-haiku | $0.25 | $1.25 | $0.03 |
| kimi-k2-turbo | $0.15 | $2.50 | — |
| deepseek-chat | $0.27 | $1.10 | $0.014 |
| deepseek-reasoner | $0.55 | $2.19 | $0.14 |
| manus-built-in | wliczone w kredyty | — | — |

### Zasady oszczędzania

1. **Używaj deepseek-chat do 80% rutynowych zadań** — najtańszy przy dobrej jakości
2. **Kimi K2 tylko gdy kontekst >50K tokenów** — unikalny w tej klasie cenowej
3. **Claude tylko do krytycznych zadań** — kod produkcyjny, bezpieczeństwo, architektura
4. **Zawsze sprawdź cache przed wywołaniem** — oszczędność do 90% przy powtarzających się zapytaniach
5. **Batch processing** — grupuj podobne zadania w jedno wywołanie

---

## Użycie w projekcie (tRPC)

### Backend — wywołanie modelu

```typescript
// server/routers/ai.ts
import { aiRouter } from "./routers/ai";

// W procedurze tRPC:
const result = await ctx.ai.chat({
  model: "auto",  // auto-routing lub konkretny model
  messages: [
    { role: "system", content: "You are a helpful assistant." },
    { role: "user", content: userMessage }
  ],
  task_type: "analysis",  // dla auto-routingu
  max_tokens: 2000,
  temperature: 0.7
});
```

### Frontend — hook React

```typescript
// Wywołanie przez tRPC
const chatMutation = trpc.ai.chat.useMutation();

const response = await chatMutation.mutateAsync({
  model: "auto",
  messages: [{ role: "user", content: "Przeanalizuj ten kod..." }],
  task_type: "code_analysis"
});

console.log(response.content);    // odpowiedź
console.log(response.model_used); // który model użyto
console.log(response.cost_usd);   // koszt wywołania
```

### Dostępne task_type dla auto-routingu

```
"analysis"       → claude-3-5-sonnet
"code_review"    → claude-3-5-sonnet
"long_context"   → kimi-k2-turbo-preview
"reasoning"      → deepseek-reasoner
"synthesis"      → deepseek-chat
"classification" → claude-3-haiku
"translation"    → deepseek-chat
"summary"        → deepseek-chat
"default"        → manus-built-in
```

---

## Fallback Chain

Gdy model jest niedostępny (brak klucza, błąd API):

```
claude-3-5-sonnet → claude-3-haiku → manus-built-in
kimi-k2-turbo     → deepseek-chat  → manus-built-in
deepseek-reasoner → deepseek-chat  → manus-built-in
```

---

## Integracja z Manus Brain Dashboard

Panel **Multi-AI Router** w dashboardzie umożliwia:
- Testowanie każdego modelu z custom promptem
- Podgląd statystyk użycia (tokeny, koszty, latencja)
- Konfigurację reguł auto-routingu
- Historię wywołań z kosztami

---

## Dodawanie do nowego projektu

1. Skopiuj `server/routers/ai.ts` z manus-brain-dashboard
2. Dodaj do `server/routers.ts`: `ai: aiRouter`
3. Dodaj klucze API do `.env` (lub przez `webdev_request_secrets`)
4. Opcjonalnie: skopiuj `AIModelsPanel.tsx` do frontendu

---

## Bezpieczeństwo

- **NIGDY** nie loguj kluczy API w konsoli ani bazie danych
- Klucze przechowuj wyłącznie w zmiennych środowiskowych lub Dexter Vault
- Loguj tylko: model, tokeny, koszt, latencję — bez treści promptów w produkcji
- Rate limiting: max 100 wywołań/minutę per użytkownik

---

## Powiązane skille

- `manus-brain/SKILL.md` — baza doświadczeń i RAG
- `CREDIT_OPTIMIZATION.md` — reguły oszczędzania kredytów
- `PROCEDURES.md` — Centrum Procedur i Dekalog projektów
