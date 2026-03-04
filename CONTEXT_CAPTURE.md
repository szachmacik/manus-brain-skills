# CONTEXT CAPTURE — Automatyczne Zapisywanie Kontekstu Rozmów

> Instrukcja dla Manusa: jak i kiedy zapisywać kontekst każdej rozmowy do wspólnej bazy wiedzy.

---

## Zasada podstawowa

**Każda rozmowa, która trwa > 5 minut lub rozwiązuje nietrywialny problem, powinna zakończyć się zapisem notatki.**

Notatka jest surowym materiałem — nocny learning run (02:00) przetworzy ją i wyciągnie wnioski do `manus_experiences`.

---

## Kiedy zapisywać (trigger list)

| Sytuacja | Ważność | Priorytet |
|----------|---------|-----------|
| Rozwiązano błąd produkcyjny | 9–10 | Krytyczny |
| Podjęto decyzję architektoniczną | 8–9 | Wysoki |
| Wdrożono nową funkcjonalność | 7–8 | Wysoki |
| Odkryto anty-wzorzec lub pułapkę | 7–8 | Wysoki |
| Zoptymalizowano istniejące rozwiązanie | 5–7 | Średni |
| Skonfigurowano nowe narzędzie/integrację | 5–6 | Średni |
| Rutynowe zadanie z nowym elementem | 3–5 | Niski |
| Czysto rutynowe zadanie | 1–3 | Opcjonalny |

---

## Format notatki (pełny)

```python
from supabase import create_client
from datetime import date
import os

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

sb.table("manus_conversation_notes").insert({
    # ── Identyfikacja ──────────────────────────────────────
    "conversation_id": f"{date.today()}_krotki-temat",
    # Format: YYYY-MM-DD_slug (np. "2026-03-04_supabase-auth-fix")
    
    "session_date": str(date.today()),
    
    "topic": "Krótki, konkretny opis zadania (max 100 znaków)",
    # Przykład: "Naprawienie błędu CORS w Supabase Edge Functions"
    
    # ── Treść ──────────────────────────────────────────────
    "key_points": [
        "Konkretny wniosek 1 — co się nauczyliśmy",
        "Konkretny wniosek 2 — co działa, co nie działa",
        "Konkretny wniosek 3 — jak to zrobić następnym razem",
    ],
    # Max 5 punktów. Konkretne, nie ogólne.
    
    "decisions_made": [
        "Decyzja: używamy X zamiast Y, bo Z",
        "Decyzja: architektura będzie taka-a-taka",
    ],
    # Decyzje, które wpływają na przyszłe projekty
    
    "problems_solved": [
        "Problem: [opis] → Rozwiązanie: [jak naprawiono]",
    ],
    # Format: "Problem: X → Rozwiązanie: Y"
    
    "open_issues": [
        "Co zostało do zrobienia w następnej sesji",
    ],
    # Otwarte kwestie — system będzie je śledził
    
    # ── Klasyfikacja ───────────────────────────────────────
    "tools_used": ["react", "supabase", "vercel", "typescript"],
    # Narzędzia, biblioteki, platformy użyte w rozmowie
    
    "projects": ["nazwa-projektu-1", "nazwa-projektu-2"],
    # Projekty, których dotyczyła rozmowa
    
    "category": "deployment",
    # deployment | coding | security | workflow | ux | data | integration | general
    
    "tags": ["cors", "edge-functions", "auth"],
    # Szczegółowe tagi do wyszukiwania
    
    # ── Metadane ───────────────────────────────────────────
    "importance": 7,
    # 1–10: 9-10=krytyczne, 7-8=ważne, 5-6=standardowe, 1-4=rutynowe
    
    "has_new_pattern": True,
    # True jeśli odkryto nowy wzorzec lub anty-wzorzec
    
    "estimated_time_saved_future": 30,
    # Ile minut zaoszczędzi ta wiedza w przyszłości (szacunek)
    
}).execute()
```

---

## Format minimalny (szybki zapis)

Gdy czas jest ograniczony, użyj formatu minimalnego:

```python
sb.table("manus_conversation_notes").insert({
    "conversation_id": f"{date.today()}_temat",
    "session_date":    str(date.today()),
    "topic":           "Krótki opis",
    "key_points":      ["Główny wniosek"],
    "tools_used":      ["narzędzie"],
    "projects":        ["projekt"],
    "importance":      5,
}).execute()
```

---

## Aktualizacja kontekstu projektu (po każdej pracy nad projektem)

```python
# Pobierz aktualny stan projektu
current = sb.table("manus_project_context") \
    .select("*").eq("project_name", "moj-projekt") \
    .execute()

existing = current.data[0] if current.data else {}

# Zaktualizuj
sb.table("manus_project_context").upsert({
    "project_name":    "moj-projekt",
    "display_name":    "Mój Projekt — Opis",
    "status":          "active",  # active | paused | completed | archived
    "tech_stack":      ["react", "supabase", "vercel", "typescript"],
    "related_domains": ["frontend", "deployment", "auth"],
    "url":             "https://moj-projekt.manus.space",
    "github_url":      "https://github.com/szachmacik/moj-projekt",
    
    # Dołącz nowy postęp do istniejących
    "recent_progress": (existing.get("recent_progress") or [])[-4:] + [{
        "date":  str(date.today()),
        "what":  "Co zostało zrobione w tej sesji",
        "files": ["client/src/App.tsx", "server/index.ts"],
    }],
    
    # Zaktualizuj otwarte kwestie
    "open_issues": [
        {"issue": "Opis problemu", "priority": "high"},  # high | medium | low
        {"issue": "Kolejna kwestia", "priority": "medium"},
    ],
    
    "last_activity": str(date.today()),
    
}, on_conflict="project_name").execute()
```

---

## Feedback o doświadczeniu (gdy coś pomogło lub zaszkodziło)

```python
# Doświadczenie pomogło — wzmocnij je
sb.rpc("increment_experience_helpful", {
    "exp_id": "uuid-doswiadczenia"
}).execute()

# Doświadczenie jest nieaktualne lub błędne — zgłoś
sb.table("manus_feedback").insert({
    "experience_id": "uuid-doswiadczenia",
    "feedback_type": "outdated",  # helpful | harmful | outdated | incomplete
    "comment":       "Dlaczego nie działa / jest nieaktualne",
    "context":       "W jakim kontekście użyto tego doświadczenia",
}).execute()
```

---

## Checklist końca rozmowy

Przed zakończeniem każdej ważnej rozmowy sprawdź:

- [ ] Czy zapisałem notatkę do `manus_conversation_notes`?
- [ ] Czy zaktualizowałem `manus_project_context` dla dotkniętych projektów?
- [ ] Czy oznaczyłem `has_new_pattern: True` jeśli odkryto wzorzec?
- [ ] Czy ustawiłem odpowiednią ważność (`importance`)?
- [ ] Czy `open_issues` odzwierciedla aktualny stan?

---

## Przykłady dobrych notatek

### Przykład 1: Błąd deploymentu

```python
{
    "topic": "Naprawa błędu 502 po deployu na Vercel — brakujące env vars",
    "key_points": [
        "Vercel nie dziedziczy env vars z .env.local — trzeba je ustawić w dashboard",
        "SUPABASE_URL musi być VITE_SUPABASE_URL dla frontendu (prefix VITE_)",
        "Po zmianie env vars wymagany redeploy — nie wystarczy restart",
    ],
    "problems_solved": [
        "Problem: 502 Bad Gateway po deployu → Rozwiązanie: dodanie brakujących VITE_ env vars w Vercel dashboard"
    ],
    "tags": ["vercel", "env-vars", "deployment", "502"],
    "importance": 8,
    "has_new_pattern": True,
}
```

### Przykład 2: Optymalizacja

```python
{
    "topic": "Optymalizacja zapytań Supabase — indeksy na kolumnach filtrowania",
    "key_points": [
        "Zapytania bez indeksu na created_at były 10x wolniejsze przy >1000 rekordach",
        "CREATE INDEX CONCURRENTLY nie blokuje tabeli — bezpieczne na produkcji",
        "Composite index (status, created_at) lepszy niż dwa osobne dla typowych zapytań",
    ],
    "tags": ["supabase", "postgresql", "performance", "indexes"],
    "importance": 7,
}
```

---

*Wersja: 2.0 | Część systemu Manus Brain*
