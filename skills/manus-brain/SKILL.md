# SKILL: Manus Brain — Baza Doświadczeń v2
**Lokalizacja:** `Google Drive: Manus Brain/SKILL.md`
**Wersja:** 2.0 | **Aktualizacja:** 2026-03-04

---

## KIEDY UŻYWAĆ TEGO SKILL

Czytaj ten plik NA POCZĄTKU każdej rozmowy z użytkownikiem, jeśli:
- Zadanie dotyczy projektu, który był wcześniej omawiany
- Użytkownik mówi "pamiętasz?", "jak poprzednio", "kontynuuj"
- Zadanie dotyczy deploymentu, kodowania, integracji, bezpieczeństwa
- Chcesz sprawdzić czy podobny problem był już rozwiązany

---

## ARCHITEKTURA SYSTEMU

```
ROZMOWA
   │
   ▼
[1] LOAD CONTEXT          ← Czytaj context snapshot z Supabase
   │
   ▼
[2] CHECK EXPERIENCES     ← Szukaj podobnych doświadczeń
   │
   ▼
[3] EXECUTE TASK          ← Wykonaj zadanie z uwzględnieniem wiedzy
   │
   ▼
[4] SAVE NOTE             ← Zapisz notatkę po zakończeniu
   │
   ▼
[5] NIGHTLY RUN (02:00)   ← System automatycznie przetwarza notatki
   │
   ▼
[6] DASHBOARD UPDATE      ← Widoczne na dashboardzie
```

---

## KROK 1: ŁADOWANIE KONTEKSTU (na początku rozmowy)

### Najszybszy start — ostatni context snapshot
```sql
SELECT top_experiences, active_projects, recent_patterns, knowledge_gaps
FROM manus_context_snapshots
WHERE snapshot_type = 'post_run'
ORDER BY created_at DESC
LIMIT 1;
```

### Top experiences (zawsze przy złożonym zadaniu)
```sql
SELECT title, summary, category, confidence, tags
FROM manus_experiences
WHERE status = 'active'
ORDER BY confidence DESC, applied_count DESC
LIMIT 10;
```

### Aktywne projekty
```sql
SELECT project_name, display_name, tech_stack, open_issues, recent_progress
FROM manus_project_context
WHERE status = 'active'
ORDER BY last_activity DESC;
```

### Wzorce do unikania
```sql
SELECT pattern_name, pattern_type, description, recommended_action
FROM manus_patterns
WHERE status = 'active' AND pattern_type IN ('anti_pattern', 'pitfall')
ORDER BY occurrence_count DESC
LIMIT 5;
```

---

## KROK 2: WYSZUKIWANIE DOŚWIADCZEŃ

### Po kategorii
```sql
SELECT title, summary, confidence, tags
FROM manus_experiences
WHERE status = 'active' AND category = 'deployment'
ORDER BY confidence DESC LIMIT 5;
-- kategorie: deployment|coding|security|workflow|ux|general|data|integration
```

### Po tagach
```sql
SELECT title, summary, confidence
FROM manus_experiences
WHERE status = 'active' AND tags && ARRAY['vercel', 'deployment']
ORDER BY confidence DESC;
```

### Po domenie
```sql
SELECT title, summary, confidence
FROM manus_experiences
WHERE status = 'active' AND domain = 'supabase'
ORDER BY confidence DESC;
```

---

## KROK 3: ZASADY WYKONANIA ZADANIA

### Hierarchia decyzji
1. **confidence > 0.8** → Stosuj bezwarunkowo
2. **confidence 0.5–0.8** → Stosuj z ostrożnością, weryfikuj
3. **confidence < 0.5** → Traktuj jako wskazówkę, nie regułę
4. **Brak doświadczenia** → Działaj standardowo, zapisz wynik jako nowe

### Optymalizacja kredytów (OBOWIĄZKOWE)
```
MODEL ROUTING:
  Klasyfikacja, tagowanie       → gpt-4.1-nano  (0.1x koszt)
  Synteza, analiza, wnioski     → gpt-4.1-mini  (0.2x koszt)
  Złożone rozumowanie, kod prod → gpt-4.1       (1x koszt — rzadko!)

CACHE FIRST:
  hash = SHA256(model + system + prompt)
  if cache[hash] exists → return cached (0 tokenów)

BATCH:
  8 notatek = 1 AI call (oszczędność 87% tokenów)

CONTEXT COMPRESSION (SimpleMem):
  Max 500 tokenów na kontekst
  Max 5 experiences, nie cała baza
```

---

## KROK 4: ZAPISYWANIE NOTATKI (po zakończeniu zadania)

### Kiedy zapisywać
- Po każdym zadaniu trwającym > 5 minut
- Po rozwiązaniu nietrywialnego problemu
- Po wdrożeniu czegoś nowego
- Po odkryciu błędu lub anty-wzorca

### Format notatki
```python
from supabase import create_client
import os

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

sb.table("manus_conversation_notes").insert({
    "conversation_id": "2026-03-04_temat_sesji",
    "session_date":    "2026-03-04",
    "topic":           "Krótki temat rozmowy",
    "key_points":      ["punkt 1", "punkt 2", "punkt 3"],
    "decisions_made":  ["decyzja 1", "decyzja 2"],
    "problems_solved": ["problem i jak go rozwiązano"],
    "open_issues":     ["co zostało do zrobienia"],
    "tools_used":      ["vercel", "supabase", "react"],
    "projects":        ["nazwa-projektu"],
    "importance":      7,        # 1-10 (10 = krytyczne)
    "has_new_pattern": True      # czy odkryto nowy wzorzec
}).execute()
```

### Skala ważności
| Wartość | Opis |
|---------|------|
| 9–10 | Krytyczny błąd, ważna decyzja architektoniczna |
| 7–8  | Nowe rozwiązanie, ważny wzorzec, deployment |
| 5–6  | Standardowe zadanie, drobna optymalizacja |
| 3–4  | Rutynowe zadanie, mała zmiana |
| 1–2  | Drobna poprawka, kosmetyczna zmiana |

---

## KROK 5: AKTUALIZACJA PROJEKTU

```python
sb.table("manus_project_context").upsert({
    "project_name":    "nazwa-projektu",
    "display_name":    "Wyświetlana nazwa",
    "status":          "active",
    "tech_stack":      ["react", "supabase", "vercel"],
    "related_domains": ["deployment", "frontend"],
    "open_issues":     [{"issue": "opis", "priority": "high"}],
    "recent_progress": [{"date": "2026-03-04", "what": "co zrobiono"}],
    "last_activity":   "2026-03-04",
    "url":             "https://projekt.manus.space"
}, on_conflict="project_name").execute()
```

---

## KROK 6: FEEDBACK DO DOŚWIADCZEŃ

```python
# Doświadczenie pomogło
sb.table("manus_experiences").update({
    "helpful_count": helpful_count + 1,
    "applied_count": applied_count + 1,
    "last_applied_at": datetime.utcnow().isoformat()
}).eq("id", experience_id).execute()

# Doświadczenie zaszkodziło / jest nieaktualne
sb.table("manus_feedback").insert({
    "experience_id": experience_id,
    "feedback_type": "harmful",  # harmful | outdated | incomplete
    "comment":       "Dlaczego nie zadziałało",
    "context":       "W jakim kontekście użyto"
}).execute()
```

---

## TABELE SUPABASE — QUICK REFERENCE

| Tabela | Cel | Kiedy używać |
|--------|-----|--------------|
| `manus_experiences` | Baza wiedzy | Czytaj na początku, zapisuj wnioski |
| `manus_conversation_notes` | Notatki z rozmów | Zapisuj po każdej rozmowie |
| `manus_project_context` | Kontekst projektów | Aktualizuj po pracy nad projektem |
| `manus_patterns` | Wzorce i anty-wzorce | Sprawdzaj przed zadaniem |
| `manus_knowledge_graph` | Relacje między wiedzą | Powiązane tematy |
| `manus_system_health` | Stan systemu | Dashboard |
| `manus_domain_metrics` | Metryki per domena | Dashboard |
| `manus_knowledge_cache` | Cache AI calls | Automatyczne |
| `manus_credit_budget` | Budżet kredytów | Przed drogimi operacjami |
| `manus_learning_runs` | Historia runów | Logi nocnego uczenia |
| `manus_context_snapshots` | Snapshoty kontekstu | Szybki start rozmowy |
| `manus_feedback` | Feedback użytkownika | Gdy coś nie działa |

---

## HARMONOGRAM AUTOMATYCZNY

| Czas | Akcja | Koszt |
|------|-------|-------|
| 02:00 codziennie | Nocny run uczenia się | $0.01–0.15 |
| Po każdej rozmowie | Zapis notatki | $0.00 |
| Co minutę | Odświeżenie dashboardu | $0.00 |
| Raz dziennie | Health snapshot | $0.00 |

---

## GOOGLE DRIVE — STRUKTURA

```
Manus Brain/
├── SKILL.md                    ← ten plik (instrukcje dla Manusa)
├── MEMORY.md                   ← aktualny stan wiedzy (auto-update)
├── CREDIT_OPTIMIZATION.md      ← szczegółowe reguły oszczędzania
├── learning-runs/              ← raporty z nocnych runów
│   ├── 2026-03-04.md
│   └── ...
├── scripts/
│   ├── manus_learning_engine_v2.py
│   ├── migration_001_experiences.sql
│   └── migration_002_extended.sql
└── snapshots/                  ← snapshoty kontekstu
    └── latest.json
```

---

## SUPABASE CONNECTION

```python
from supabase import create_client
import os

sb = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"]
)
# Project ID: qhscjlfavyqkaplcwhxu
# Region: eu-central-1
```

---

## SZACOWANE KOSZTY

| Operacja | Częstotliwość | Koszt |
|----------|--------------|-------|
| Dodanie notatki | Po każdej rozmowie | **$0.00** |
| Pobranie kontekstu | Na początku zadania | **$0.00** |
| Nocny run (10 notatek) | Codziennie | **~$0.002** |
| Nocny run (50 notatek) | Raz w tygodniu | **~$0.01** |
| Miesięczny koszt | — | **~$0.05–0.15** |

*Przy 80%+ cache hit rate koszty spadają do $0.01–0.05/miesiąc.*

---

## ŹRÓDŁA I STANDARDY

- **Stanford ACE** (arXiv:2510.04618) — delta updates, playbook bullets, brevity bias prevention
- **SimpleMem** (arXiv:2601.02553) — semantic lossless compression, 30x token reduction
- **Maxim AI 2026** — model routing (37–46% savings), semantic caching (15–70% savings)
- **OpenAI Prompt Caching** — 10x cheaper cached tokens

*Wygenerowano: 2026-03-04 | Wersja: 2.0*
