# 🧠 Manus Brain — Shared Knowledge Skills

> Wspólna baza wiedzy i doświadczeń dla wszystkich projektów Manusa. Każdy projekt czerpie z tej samej puli wniosków, wzorców i sprawdzonych rozwiązań.

---

## Czym jest ten system?

**Manus Brain** to cyklicznie aktualizowana baza doświadczeń, która pozwala Manusowi:

- **Pamiętać** co zostało zrobione w poprzednich rozmowach i projektach
- **Unikać** błędów, które już raz zostały popełnione
- **Stosować** sprawdzone rozwiązania bez ponownego "odkrywania koła"
- **Uczyć się** codziennie w nocy na podstawie nowych notatek z rozmów
- **Optymalizować** zużycie kredytów dzięki cache i model routingowi

Baza jest zasilana przez **nocny learning run (02:00)** i dostępna dla wszystkich projektów przez Supabase.

---

## Struktura repozytorium

```
manus-brain-skills/
├── README.md                          ← ten plik
├── SKILL.md                           ← główna instrukcja dla Manusa
├── CONTEXT_CAPTURE.md                 ← jak zapisywać kontekst po rozmowie
├── CROSS_PROJECT.md                   ← jak inne projekty korzystają z bazy
├── CREDIT_OPTIMIZATION.md             ← reguły oszczędzania kredytów
│
├── skills/
│   ├── manus-brain/
│   │   └── SKILL.md                   ← skill do użycia w /home/ubuntu/skills/
│   └── templates/
│       ├── note_template.py           ← szablon notatki po rozmowie
│       ├── project_update.py          ← szablon aktualizacji projektu
│       └── experience_query.py        ← szablony zapytań do bazy
│
├── migrations/
│   ├── 001_experiences.sql            ← migracja v1
│   └── 002_extended.sql               ← migracja v2 (projekty, wzorce, health)
│
└── scripts/
    └── learning_engine_v2.py          ← nocny skrypt uczenia się
```

---

## Szybki start dla nowego projektu

### 1. Pobierz kontekst na początku rozmowy

```python
from supabase import create_client
import os

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

# Pobierz ostatni snapshot (najszybszy start)
snapshot = sb.table("manus_context_snapshots") \
    .select("top_experiences, active_projects, recent_patterns") \
    .eq("snapshot_type", "post_run") \
    .order("created_at", desc=True) \
    .limit(1).execute()

# Pobierz top doświadczenia dla kategorii
experiences = sb.table("manus_experiences") \
    .select("title, summary, confidence, tags") \
    .eq("status", "active") \
    .order("confidence", desc=True) \
    .limit(10).execute()
```

### 2. Zapisz notatkę po zakończeniu rozmowy

```python
sb.table("manus_conversation_notes").insert({
    "conversation_id": "2026-03-04_temat",
    "session_date":    "2026-03-04",
    "topic":           "Krótki opis zadania",
    "key_points":      ["wniosek 1", "wniosek 2"],
    "decisions_made":  ["decyzja architektoniczna"],
    "problems_solved": ["problem → rozwiązanie"],
    "tools_used":      ["react", "supabase", "vercel"],
    "projects":        ["nazwa-projektu"],
    "importance":      7,
}).execute()
```

### 3. Zaktualizuj kontekst projektu

```python
sb.table("manus_project_context").upsert({
    "project_name": "moj-projekt",
    "display_name": "Mój Projekt",
    "status":       "active",
    "tech_stack":   ["react", "supabase"],
    "last_activity": "2026-03-04",
}, on_conflict="project_name").execute()
```

---

## Tabele Supabase — mapa

| Tabela | Cel |
|--------|-----|
| `manus_experiences` | Baza wiedzy — wnioski i sprawdzone rozwiązania |
| `manus_conversation_notes` | Surowe notatki z rozmów (przetwarzane nocą) |
| `manus_project_context` | Stan i kontekst każdego projektu |
| `manus_patterns` | Wzorce, anty-wzorce, pułapki |
| `manus_knowledge_graph` | Relacje między wiedzą |
| `manus_knowledge_cache` | Cache AI calls (SHA256, TTL 30 dni) |
| `manus_credit_budget` | Budżet i monitoring kredytów |
| `manus_learning_runs` | Historia nocnych runów |
| `manus_context_snapshots` | Skompresowane snapshoty kontekstu |
| `manus_system_health` | Health score systemu |
| `manus_domain_metrics` | Metryki per domena (deployment, coding, etc.) |
| `manus_feedback` | Feedback o jakości doświadczeń |

---

## Optymalizacja kredytów

System jest zaprojektowany tak, żeby **95% operacji było bezpłatnych**:

| Tier | Operacja | Koszt |
|------|----------|-------|
| 0 | SQL queries, cache hits, odczyt plików | **$0.00** |
| 1 | gpt-4.1-nano — klasyfikacja, tagowanie | ~$0.0001/call |
| 2 | gpt-4.1-mini — synteza, insights | ~$0.001/call |
| ❌ | gpt-4.1, Claude Opus — zakazane | zbyt drogie |

**Szacowany koszt miesięczny: $0.05–0.15** (aktywny użytkownik, 5 rozmów/dzień)

Szczegóły: [CREDIT_OPTIMIZATION.md](./CREDIT_OPTIMIZATION.md)

---

## Harmonogram automatyczny

| Czas | Akcja |
|------|-------|
| **02:00 codziennie** | Nocny learning run — przetwarza nowe notatki |
| Po każdej rozmowie | Zapis notatki do `manus_conversation_notes` |
| Co minutę | Odświeżenie dashboardu (zero AI calls) |

---

## Podstawy naukowe

System oparty na najnowszych badaniach (2025/2026):

- **Stanford ACE** (arXiv:2510.04618) — delta updates, self-learning agents
- **SimpleMem** (arXiv:2601.02553) — semantic lossless compression, 30x token reduction  
- **Maxim AI 2026** — model routing (37–46% savings), semantic caching (15–70% savings)
- **OpenAI Prompt Caching** — 10x cheaper cached tokens

---

## Dashboard

Wizualny podgląd postępów Manusa dostępny po opublikowaniu projektu `manus-brain-dashboard`.

Pokazuje: health score, aktywne doświadczenia, historia runów, budżet kredytów, projekty, wzorce, trendy.

---

*Wersja: 2.0 | Aktualizacja: 2026-03-04*
