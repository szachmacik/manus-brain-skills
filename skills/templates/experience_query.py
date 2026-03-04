"""
MANUS BRAIN — Szablony zapytań do bazy wiedzy
Użyj tych funkcji na początku rozmowy lub podczas zadania.
"""
from supabase import create_client
import os

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


# ════════════════════════════════════════════════════════════════
# 1. SZYBKI START — ładuj na początku każdej rozmowy
# ════════════════════════════════════════════════════════════════

def quick_context(project_name: str = None) -> dict:
    """
    Ładuje skompresowany kontekst Manusa.
    Używaj na początku każdej rozmowy — zero AI calls, ~10ms.
    """
    # Ostatni pre-computed snapshot
    snap = sb.table("manus_context_snapshots") \
        .select("top_experiences, active_projects, recent_patterns, knowledge_gaps") \
        .eq("snapshot_type", "post_run") \
        .order("created_at", desc=True) \
        .limit(1).execute()

    result = {"snapshot": snap.data[0] if snap.data else None}

    # Kontekst projektu (opcjonalnie)
    if project_name:
        proj = sb.table("manus_project_context") \
            .select("display_name, tech_stack, open_issues, recent_progress, url") \
            .eq("project_name", project_name) \
            .execute()
        result["project"] = proj.data[0] if proj.data else None

    return result


# ════════════════════════════════════════════════════════════════
# 2. WYSZUKIWANIE DOŚWIADCZEŃ
# ════════════════════════════════════════════════════════════════

def find_by_tags(tags: list, limit: int = 5) -> list:
    """Znajdź doświadczenia pasujące do tagów."""
    return sb.table("manus_experiences") \
        .select("title, summary, confidence, recommended_action") \
        .eq("status", "active") \
        .overlaps("tags", tags) \
        .order("confidence", desc=True) \
        .limit(limit).execute().data


def find_by_category(category: str, limit: int = 5) -> list:
    """
    Znajdź top doświadczenia dla kategorii.
    Kategorie: deployment | coding | security | workflow | ux | data | integration | general
    """
    return sb.table("manus_experiences") \
        .select("title, summary, confidence, recommended_action, tags") \
        .eq("status", "active") \
        .eq("category", category) \
        .order("confidence", desc=True) \
        .limit(limit).execute().data


def find_by_domain(domain: str, limit: int = 5) -> list:
    """Znajdź doświadczenia dla domeny (np. 'supabase', 'vercel', 'react')."""
    return sb.table("manus_experiences") \
        .select("title, summary, confidence, recommended_action") \
        .eq("status", "active") \
        .eq("domain", domain) \
        .order("confidence", desc=True) \
        .limit(limit).execute().data


# ════════════════════════════════════════════════════════════════
# 3. ANTY-WZORCE I PUŁAPKI
# ════════════════════════════════════════════════════════════════

def get_anti_patterns(tags: list = None, limit: int = 5) -> list:
    """Pobierz znane anty-wzorce. Sprawdzaj przed każdym deploymentem."""
    q = sb.table("manus_patterns") \
        .select("pattern_name, description, recommended_action, occurrence_count") \
        .eq("status", "active") \
        .in_("pattern_type", ["anti_pattern", "pitfall"]) \
        .order("occurrence_count", desc=True)

    if tags:
        q = q.overlaps("tags", tags)

    return q.limit(limit).execute().data


def get_best_practices(category: str = None, limit: int = 5) -> list:
    """Pobierz sprawdzone dobre praktyki."""
    q = sb.table("manus_patterns") \
        .select("pattern_name, description, recommended_action") \
        .eq("status", "active") \
        .eq("pattern_type", "best_practice") \
        .order("occurrence_count", desc=True)

    if category:
        q = q.eq("category", category)

    return q.limit(limit).execute().data


# ════════════════════════════════════════════════════════════════
# 4. PROJEKTY
# ════════════════════════════════════════════════════════════════

def get_active_projects() -> list:
    """Pobierz wszystkie aktywne projekty z ich stanem."""
    return sb.table("manus_project_context") \
        .select("project_name, display_name, tech_stack, url, open_issues, last_activity") \
        .eq("status", "active") \
        .order("last_activity", desc=True) \
        .execute().data


def get_project(project_name: str) -> dict | None:
    """Pobierz pełny kontekst konkretnego projektu."""
    result = sb.table("manus_project_context") \
        .select("*") \
        .eq("project_name", project_name) \
        .execute()
    return result.data[0] if result.data else None


# ════════════════════════════════════════════════════════════════
# 5. FEEDBACK
# ════════════════════════════════════════════════════════════════

def mark_helpful(experience_id: str):
    """Oznacz doświadczenie jako pomocne — wzmacnia jego confidence."""
    exp = sb.table("manus_experiences") \
        .select("helpful_count, applied_count") \
        .eq("id", experience_id).single().execute().data
    
    sb.table("manus_experiences").update({
        "helpful_count": (exp["helpful_count"] or 0) + 1,
        "applied_count": (exp["applied_count"] or 0) + 1,
    }).eq("id", experience_id).execute()
    print(f"✅ Oznaczono jako pomocne: {experience_id}")


def report_issue(experience_id: str, feedback_type: str, comment: str):
    """
    Zgłoś problem z doświadczeniem.
    feedback_type: harmful | outdated | incomplete
    """
    sb.table("manus_feedback").insert({
        "experience_id": experience_id,
        "feedback_type": feedback_type,
        "comment":       comment,
    }).execute()
    print(f"⚠️  Zgłoszono problem ({feedback_type}): {experience_id}")


# ════════════════════════════════════════════════════════════════
# PRZYKŁAD UŻYCIA
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== SZYBKI KONTEKST ===")
    ctx = quick_context(project_name="ai-control-center")
    if ctx["snapshot"]:
        print("Top experiences:", ctx["snapshot"].get("top_experiences", [])[:3])
    
    print("\n=== ANTY-WZORCE DEPLOYMENT ===")
    for p in get_anti_patterns(tags=["vercel", "deployment"]):
        print(f"  ⚠️  {p['pattern_name']}: {p['description'][:80]}...")
    
    print("\n=== TOP DOŚWIADCZENIA CODING ===")
    for e in find_by_category("coding", limit=3):
        print(f"  ✅ [{e['confidence']:.0%}] {e['title']}")
