# 📜 Dekalog Projektów Manus — Centrum Procedur

> **Wersja:** 2.0 | **Ostatnia aktualizacja:** 2026-03-05  
> Obowiązuje we wszystkich projektach tworzonych i zarządzanych przez Manusa.

---

## I. EFEKTYWNOŚĆ — Rób więcej za mniej

**Zasada:** Każda operacja musi być uzasadniona kosztem i wartością.

- Zawsze sprawdź cache przed wywołaniem AI (SHA256, TTL 30 dni)
- Batch 5-10 elementów = 1 prompt zamiast N wywołań
- Delta-only updates: przetwarzaj tylko nowe dane od ostatniego runu
- Kompresja kontekstu: summary zamiast pełnej historii
- Ustaw `max_tokens` — nigdy nie zostawiaj bez limitu
- Budget guard: sprawdź miesięczny limit przed dużą operacją

**Model routing (od najtańszego):**

| Zadanie | Model | Koszt/1M tokenów |
|---------|-------|-----------------|
| Proste klasyfikacje, tagi | DeepSeek V3 (cache) | $0.014 |
| Kod, debug, refaktor | DeepSeek V3 | $0.028 |
| Długi kontekst (128K+) | Kimi K2 Turbo | $0.15 |
| Analiza, architektura | Claude 3.5 Haiku | $0.25 |
| Złożone zadania, reasoning | Claude 3.5 Sonnet | $3.00 |
| Szybkie, proste | Manus built-in | Free |

---

## II. BEZPIECZEŃSTWO — Żadnych kompromisów

**Zasada:** Sekrety nigdy nie trafiają do kodu ani GitHub.

- Wszystkie klucze API przez `webdev_request_secrets` lub Dexter Vault
- `os.environ.get(KEY)` lub `process.env.KEY` — nigdy hardkodowane
- Skanuj pliki przed każdym `git push` (`grep -r "sk-\|password\|secret"`)
- `service_role` key Supabase — wyłącznie server-side
- Włącz RLS na każdej tabeli z danymi użytkowników
- Nigdy nie commituj `.env` z wartościami
- Repo domyślnie `--private` chyba że jawnie publiczne

---

## III. ARCHITEKTURA — Sprawdzone wzorce

**Zasada:** Używaj sprawdzonych wzorców zamiast wymyślać od nowa.

**Stack webowy (domyślny):**
```
React 19 + Tailwind 4 + tRPC 11 + Drizzle ORM + MySQL/TiDB
```

- tRPC procedury zamiast REST endpoints
- Drizzle schema-first: najpierw `drizzle/schema.ts`, potem `pnpm db:push`
- `server/db.ts` — query helpers, nie inline SQL w routerach
- Optymistyczne aktualizacje przez `onMutate/onError/onSettled`
- DashboardLayout dla narzędzi wewnętrznych
- Nigdy nie używaj fetch/axios bezpośrednio — tylko tRPC hooks

---

## IV. PRZEPŁYW DANYCH — Czysty i przewidywalny

**Zasada:** Dane mają jedno źródło prawdy i jeden kierunek przepływu.

- Pliki statyczne (obrazy, wideo) → CDN przez `manus-upload-file --webdev`
- Metadane plików w DB, bajty w S3 — nigdy odwrotnie
- Timestamps zawsze UTC, konwersja na frontend
- Arrays w PostgreSQL: `ARRAY['a','b']` nie `'["a","b"]'`
- JSONB dla złożonych struktur, TEXT[] dla prostych list
- Supabase SDK: listy Python jako natywne listy, nie `json.dumps()`

---

## V. DEPLOYMENT — Bezpieczny i odwracalny

**Zasada:** Każda zmiana jest odwracalna.

- `webdev_save_checkpoint` przed każdą ryzykowną operacją
- `webdev_rollback_checkpoint` — nigdy `git reset --hard`
- Publish tylko przez UI (przycisk Publish) — nigdy przez kod
- Sprawdź TypeScript przed commitem: `npx tsc --noEmit`
- Testy Vitest przed każdym checkpointem: `pnpm test`
- Restart serwera po `pnpm add`: `webdev_restart_server`

---

## VI. CLAUDE SUPPORT — AI jako wewnętrzny ekspert

**Zasada:** Gdy Manus napotka problem po 3 próbach, deleguje do Claude.

- Claude API: `api.anthropic.com/v1` — klucz przez Dexter Vault
- Trigger: 3 nieudane próby naprawy tego samego błędu
- Kontekst: pełny opis błędu + ostatnie 10 akcji + pliki
- Model: `claude-3-5-sonnet-20241022` dla trudnych problemów
- Wynik: zapisz rozwiązanie do `manus_experiences` w Supabase
- Koszt: max $0.50/sesję debugowania

---

## VII. MONITORING — Wiedz co się dzieje

**Zasada:** System musi być transparentny i mierzalny.

- Health Score obliczany co godzinę (0-100)
- Alerty push gdy Health Score < 60
- Nocny learning run o 02:00 — delta-only, max $0.10/run
- Tygodniowy raport push w niedzielę o 08:00
- Loguj każde wywołanie AI do `ai_usage_logs`
- Budget alert gdy miesięczny koszt > 80% limitu

---

## VIII. WIEDZA — Ucz się i pamiętaj

**Zasada:** Każde doświadczenie jest wartościowe — zapisz je.

- Po każdej rozmowie: notatka do `manus_conversation_notes`
- Po każdym projekcie: doświadczenia do `manus_experiences`
- Wykryte anty-wzorce → `manus_patterns` (pattern_type: anti_pattern)
- Sprawdzone rozwiązania → `manus_patterns` (pattern_type: best_practice)
- Procedury krok-po-kroku → `manus_patterns` (pattern_type: procedure)
- SKILL.md w `/home/ubuntu/skills/manus-brain/` — czytaj na początku zadania

---

## IX. CROSS-PROJECT — Wiedza jest wspólna

**Zasada:** Rozwiązanie z jednego projektu jest dostępne we wszystkich.

- GitHub repo: `szachmacik/manus-brain-skills` — publiczne szablony
- Supabase `ai-control-center` — wspólna baza wiedzy
- Importuj `server/routers/ai.ts` dla Multi-AI Router
- Importuj `server/routers/push.ts` dla Web Push
- Sprawdź `manus_experiences` przed implementacją — może już to zrobiliśmy
- Aktualizuj bazę po każdym nowym projekcie

---

## X. DOSKONALENIE — Zawsze lepiej niż wczoraj

**Zasada:** System jest żywy i ciągle się poprawia.

- Nocny learning run analizuje nowe doświadczenia i aktualizuje wnioski
- Health Score trendy pokazują kierunek zmian
- Wzorce z occurrence_count > 5 → kandydaci do automatyzacji
- Procedury z confidence > 0.9 → wbuduj w domyślny workflow
- Raz na miesiąc: przegląd deprecated doświadczeń
- Raz na kwartał: aktualizacja Dekaloga na podstawie nowych wzorców

---

## Szybka ściągawka

```bash
# Nowy projekt
webdev_init_project → todo.md → webdev_add_feature → secrets → schema → db:push → backend → frontend → tsc → checkpoint → Publish

# Przed każdym AI call
cache? → batch? → model routing → delta-only → max_tokens → budget check

# Przed każdym commitem  
npx tsc --noEmit → pnpm test → webdev_save_checkpoint → git push

# Problem po 3 próbach
→ Deleguj do Claude (ANTHROPIC_API_KEY w Dexter Vault)
→ Zapisz rozwiązanie do manus_experiences
```

---

*Dekalog jest żywym dokumentem. Aktualizowany automatycznie przez nocny learning run na podstawie nowych doświadczeń z bazy wiedzy.*
