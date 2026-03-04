# SKILL: manus-brain
**Opis:** Baza doświadczeń Manusa — ładuj kontekst, zapisuj wnioski, ucz się między projektami.
**Wersja:** 2.0 | **Repo:** https://github.com/szachmacik/manus-brain-skills

---

## KIEDY UŻYWAĆ

Czytaj ten skill NA POCZĄTKU każdej rozmowy gdy:
- Zadanie dotyczy projektu, który był wcześniej omawiany
- Użytkownik mówi "pamiętasz?", "jak poprzednio", "kontynuuj", "sprawdź co robiliśmy"
- Zadanie dotyczy deploymentu, kodowania, integracji, bezpieczeństwa
- Chcesz sprawdzić czy podobny problem był już rozwiązany

Czytaj ten skill NA KOŃCU każdej ważnej rozmowy gdy:
- Rozwiązałeś nietrywialny problem
- Wdrożyłeś coś nowego
- Podjęto decyzję architektoniczną
- Odkryłeś błąd lub anty-wzorzec

---

## KROK 1: ŁADUJ KONTEKST (start rozmowy)

```python
from supabase import create_client
import os

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

# Najszybszy start — pre-computed snapshot
snap = sb.table("manus_context_snapshots") \
    .select("top_experiences, active_projects, recent_patterns, knowledge_gaps") \
    .eq("snapshot_type", "post_run") \
    .order("created_at", desc=True) \
    .limit(1).execute()

if snap.data:
    ctx = snap.data[0]
    # ctx["top_experiences"] — lista top wniosków
    # ctx["active_projects"] — aktywne projekty
    # ctx["recent_patterns"] — ostatnie wzorce
    # ctx["knowledge_gaps"]  — luki w wiedzy
```

---

## KROK 2: SZUKAJ WIEDZY (podczas zadania)

```python
# Po tagach
exp = sb.table("manus_experiences") \
    .select("title, summary, confidence, recommended_action") \
    .eq("status", "active") \
    .overlaps("tags", ["vercel", "deployment"]) \
    .order("confidence", desc=True).limit(5).execute().data

# Anty-wzorce (sprawdzaj przed deploymentem)
anti = sb.table("manus_patterns") \
    .select("pattern_name, description, recommended_action") \
    .eq("status", "active").eq("pattern_type", "anti_pattern") \
    .order("occurrence_count", desc=True).limit(5).execute().data
```

---

## KROK 3: STOSUJ WIEDZĘ

| Confidence | Działanie |
|-----------|-----------|
| > 0.8 | Stosuj bezwarunkowo |
| 0.5–0.8 | Stosuj z ostrożnością, weryfikuj |
| < 0.5 | Traktuj jako wskazówkę |
| Brak | Działaj standardowo, zapisz wynik |

---

## KROK 4: ZAPISZ NOTATKĘ (koniec rozmowy)

```python
from datetime import date

sb.table("manus_conversation_notes").insert({
    "conversation_id": f"{date.today()}_temat-sesji",
    "session_date":    str(date.today()),
    "topic":           "Krótki opis zadania",
    "key_points":      ["wniosek 1", "wniosek 2"],
    "decisions_made":  ["decyzja architektoniczna"],
    "problems_solved": ["Problem: X → Rozwiązanie: Y"],
    "tools_used":      ["react", "supabase"],
    "projects":        ["nazwa-projektu"],
    "importance":      7,        # 1-10
    "has_new_pattern": False,
}).execute()
```

---

## KROK 5: ZAKTUALIZUJ PROJEKT

```python
sb.table("manus_project_context").upsert({
    "project_name":  "nazwa-projektu",
    "display_name":  "Pełna nazwa",
    "status":        "active",
    "tech_stack":    ["react", "supabase", "vercel"],
    "open_issues":   [{"issue": "opis", "priority": "high"}],
    "last_activity": str(date.today()),
}, on_conflict="project_name").execute()
```

---

## OPTYMALIZACJA KREDYTÓW (OBOWIĄZKOWE)

```
MODEL ROUTING:
  Klasyfikacja, tagowanie    → gpt-4.1-nano  (najtańszy)
  Synteza, analiza, wnioski  → gpt-4.1-mini  (balans)
  Złożone rozumowanie        → gpt-4.1       (rzadko!)

CACHE FIRST:
  Zawsze sprawdź cache przed AI call
  hash = SHA256(model + prompt)
  Jeśli cache hit → 0 tokenów

BATCH:
  8 notatek = 1 AI call (oszczędność 87%)

CONTEXT:
  Max 500 tokenów kontekstu
  Max 5 experiences, nie cała baza
```

---

## TABELE QUICK REFERENCE

| Tabela | Cel |
|--------|-----|
| `manus_experiences` | Baza wiedzy — czytaj i zapisuj |
| `manus_conversation_notes` | Notatki z rozmów — zapisuj po sesji |
| `manus_project_context` | Kontekst projektów — aktualizuj |
| `manus_patterns` | Wzorce i anty-wzorce — sprawdzaj |
| `manus_context_snapshots` | Skompresowany kontekst — szybki start |
| `manus_knowledge_cache` | Cache AI calls — automatyczne |
| `manus_credit_budget` | Budżet — sprawdzaj przed drogimi ops |

---

## HARMONOGRAM

| Czas | Akcja |
|------|-------|
| 02:00 codziennie | Nocny learning run |
| Po każdej rozmowie | Zapis notatki ($0.00) |
| Co minutę | Dashboard refresh ($0.00) |

---

*Szacowany koszt: $0.05–0.15/miesiąc | Repo: github.com/szachmacik/manus-brain-skills*
