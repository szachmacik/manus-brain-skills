# CROSS-PROJECT KNOWLEDGE SHARING
> Jak każdy projekt Manusa czerpie ze wspólnej bazy wiedzy i wdraża sprawdzone rozwiązania

---

## Filozofia

Każdy projekt Manusa nie zaczyna od zera. Zamiast tego:

1. **Na początku każdej rozmowy** — Manus ładuje kontekst z bazy (co wiemy, co nie działa, jakie projekty są aktywne)
2. **Podczas wykonywania zadania** — stosuje sprawdzone wzorce, unika znanych pułapek
3. **Po zakończeniu rozmowy** — zapisuje nowe wnioski, które jutro w nocy zasilą bazę

Dzięki temu wiedza zdobyta przy projekcie A automatycznie pomaga przy projekcie B.

---

## Przepływ wiedzy między projektami

```
Projekt A (np. ai-control-center)
    │
    │  Manus odkrywa: "Vercel wymaga VITE_ prefix dla env vars"
    │
    ▼
manus_conversation_notes (Supabase)
    │
    │  02:00 — nocny learning run
    │
    ▼
manus_experiences
    title: "Vercel env vars — VITE_ prefix wymagany"
    category: "deployment"
    confidence: 0.9
    tags: ["vercel", "env-vars", "vite"]
    │
    │  Następna rozmowa — Projekt B (np. educational-sales-site)
    │
    ▼
Manus automatycznie stosuje wiedzę przy deploymencie Projektu B
→ Unika błędu, który kosztował 30 min przy Projekcie A
```

---

## Jak Manus ładuje kontekst na początku rozmowy

### Automatyczny start (zalecany)

```python
from supabase import create_client
import os

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

def load_manus_context(project_name: str = None, category: str = None):
    """
    Ładuje kontekst Manusa na początku rozmowy.
    Zwraca skompresowany kontekst gotowy do użycia.
    """
    
    # 1. Ostatni snapshot (najszybszy — pre-computed)
    snapshot = sb.table("manus_context_snapshots") \
        .select("top_experiences, active_projects, recent_patterns, knowledge_gaps") \
        .eq("snapshot_type", "post_run") \
        .order("created_at", desc=True) \
        .limit(1).execute()
    
    # 2. Kontekst konkretnego projektu (jeśli podany)
    project_ctx = None
    if project_name:
        result = sb.table("manus_project_context") \
            .select("*") \
            .eq("project_name", project_name) \
            .execute()
        project_ctx = result.data[0] if result.data else None
    
    # 3. Top doświadczenia dla kategorii (jeśli podana)
    category_exp = []
    if category:
        result = sb.table("manus_experiences") \
            .select("title, summary, confidence, tags, recommended_action") \
            .eq("status", "active") \
            .eq("category", category) \
            .order("confidence", desc=True) \
            .limit(5).execute()
        category_exp = result.data
    
    # 4. Aktywne anty-wzorce (zawsze sprawdzaj)
    anti_patterns = sb.table("manus_patterns") \
        .select("pattern_name, description, recommended_action") \
        .eq("status", "active") \
        .eq("pattern_type", "anti_pattern") \
        .order("occurrence_count", desc=True) \
        .limit(5).execute()
    
    return {
        "snapshot":      snapshot.data[0] if snapshot.data else None,
        "project":       project_ctx,
        "experiences":   category_exp,
        "anti_patterns": anti_patterns.data,
    }

# Użycie:
ctx = load_manus_context(
    project_name="moj-projekt",
    category="deployment"
)
```

### Minimalny start (szybki)

```python
# Tylko ostatni snapshot — wystarczy dla większości rozmów
snapshot = sb.table("manus_context_snapshots") \
    .select("top_experiences, recent_patterns") \
    .eq("snapshot_type", "post_run") \
    .order("created_at", desc=True) \
    .limit(1).single().execute()

print(snapshot.data["top_experiences"])
```

---

## Wyszukiwanie wiedzy podczas zadania

### Znajdź rozwiązanie dla konkretnego problemu

```python
def find_experience(query_tags: list, category: str = None):
    """Znajdź doświadczenia pasujące do tagów."""
    q = sb.table("manus_experiences") \
        .select("title, summary, confidence, recommended_action, source_notes") \
        .eq("status", "active") \
        .overlaps("tags", query_tags) \
        .order("confidence", desc=True) \
        .limit(5)
    
    if category:
        q = q.eq("category", category)
    
    return q.execute().data

# Przykład: szukam wiedzy o Supabase auth
results = find_experience(
    query_tags=["supabase", "auth", "jwt"],
    category="security"
)
```

### Sprawdź czy podobny problem był już rozwiązany

```python
def check_known_issues(domain: str, tags: list):
    """Sprawdź znane problemy i anty-wzorce."""
    patterns = sb.table("manus_patterns") \
        .select("pattern_name, description, recommended_action, occurrence_count") \
        .eq("status", "active") \
        .overlaps("tags", tags) \
        .order("occurrence_count", desc=True) \
        .execute()
    
    return patterns.data

# Przykład: sprawdzam przed deploymentem
issues = check_known_issues(
    domain="deployment",
    tags=["vercel", "env-vars"]
)
```

---

## Wdrażanie wiedzy w istniejących projektach

### Automatyczny audit projektu

```python
def audit_project_against_knowledge(project_name: str):
    """
    Sprawdza projekt pod kątem znanych problemów i możliwych ulepszeń.
    Zwraca listę rekomendacji.
    """
    
    # Pobierz kontekst projektu
    project = sb.table("manus_project_context") \
        .select("*").eq("project_name", project_name) \
        .single().execute().data
    
    tech_stack = project.get("tech_stack", [])
    
    # Znajdź doświadczenia dla tech stacku projektu
    improvements = sb.table("manus_experiences") \
        .select("title, summary, confidence, recommended_action") \
        .eq("status", "active") \
        .overlaps("tags", tech_stack) \
        .gt("confidence", 0.7) \
        .order("confidence", desc=True) \
        .limit(10).execute()
    
    # Znajdź anty-wzorce dla tech stacku
    risks = sb.table("manus_patterns") \
        .select("pattern_name, description, recommended_action") \
        .eq("status", "active") \
        .eq("pattern_type", "anti_pattern") \
        .overlaps("tags", tech_stack) \
        .execute()
    
    return {
        "project":      project_name,
        "improvements": improvements.data,
        "risks":        risks.data,
        "tech_stack":   tech_stack,
    }
```

---

## Przykłady cross-project knowledge w akcji

### Scenariusz 1: Deployment nowego projektu

```
Projekt: polaris-track (nowy)
Tech stack: React + Supabase + Vercel

Manus ładuje kontekst → znajdzie doświadczenia z tagami [vercel, supabase]:

✅ "Vercel wymaga VITE_ prefix dla env vars" (confidence: 0.95)
   → Manus automatycznie używa VITE_SUPABASE_URL zamiast SUPABASE_URL

✅ "Supabase RLS musi być włączone przed deploymentem" (confidence: 0.88)
   → Manus sprawdza RLS przed deploymentem

⚠️  ANTY-WZORZEC: "Nie commituj .env do GitHub" (occurrence: 3)
   → Manus weryfikuje .gitignore
```

### Scenariusz 2: Naprawa błędu w istniejącym projekcie

```
Projekt: educational-sales-site
Problem: Wolne ładowanie strony

Manus szuka: find_experience(["performance", "react", "optimization"])

Znajdzie: "React.lazy + Suspense redukuje initial bundle o 60%" (confidence: 0.82)
         "Supabase select() bez limit() pobiera wszystkie rekordy" (confidence: 0.91)

→ Stosuje oba rozwiązania bez ponownego "odkrywania"
```

### Scenariusz 3: Nowa integracja

```
Projekt: integration-hub
Zadanie: Integracja Stripe

Manus szuka: find_experience(["stripe", "payments", "webhook"])

Znajdzie: "Stripe webhooks wymagają raw body — nie parsuj JSON przed weryfikacją" (confidence: 0.94)
         "Zawsze używaj idempotency keys dla Stripe API calls" (confidence: 0.87)

→ Implementuje poprawnie od razu, bez typowych błędów
```

---

## Priorytetyzacja wiedzy między projektami

Nie wszystkie doświadczenia są równie wartościowe. System priorytetyzuje:

| Kryterium | Waga | Opis |
|-----------|------|------|
| `confidence` | 40% | Jak pewne jest to doświadczenie |
| `applied_count` | 30% | Ile razy zostało zastosowane |
| `helpful_count` | 20% | Ile razy pomogło |
| `recency` | 10% | Jak świeże jest doświadczenie |

```python
# Formuła rankingu (używana przez learning engine)
score = (
    experience.confidence * 0.4 +
    min(experience.applied_count / 10, 1) * 0.3 +
    min(experience.helpful_count / 5, 1) * 0.2 +
    recency_score * 0.1
)
```

---

## Synchronizacja między projektami (automatyczna)

System automatycznie synchronizuje wiedzę:

```
Każdej nocy o 02:00:
1. Przetwarza nowe notatki ze WSZYSTKICH projektów
2. Aktualizuje manus_experiences (upsert — nie duplikuje)
3. Wykrywa wzorce cross-project (np. ten sam błąd w 3 projektach)
4. Aktualizuje manus_context_snapshots (gotowy do użycia następnego dnia)
5. Oblicza health score per domena
6. Zapisuje raport na Google Drive
```

Dzięki temu wiedza z projektu A jest dostępna dla projektu B już następnego dnia rano.

---

## Integracja z istniejącymi projektami

### Dodaj do istniejącego projektu w 3 krokach

**Krok 1:** Dodaj zmienne środowiskowe (jeśli nie ma)
```bash
# .env.local
SUPABASE_URL=https://[project-id].supabase.co
SUPABASE_KEY=[anon-key]
```

**Krok 2:** Zainstaluj klienta Supabase
```bash
pip install supabase  # Python
# lub
pnpm add @supabase/supabase-js  # Node.js
```

**Krok 3:** Skopiuj szablony z `skills/templates/` i dostosuj do projektu

---

*Wersja: 2.0 | Część systemu Manus Brain*
