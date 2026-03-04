"""
MANUS BRAIN — Szablon aktualizacji kontekstu projektu
Uruchamiaj po każdej sesji pracy nad projektem.
"""
from supabase import create_client
from datetime import date
import os

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

TODAY = str(date.today())

# ════════════════════════════════════════════════════════════════
# WYPEŁNIJ PONIŻSZE POLA
# ════════════════════════════════════════════════════════════════

PROJECT_NAME = "ZMIEŃ-na-nazwe-projektu"  # np. "ai-control-center"

project = {
    "project_name":    PROJECT_NAME,
    "display_name":    "ZMIEŃ: Pełna nazwa projektu",
    "status":          "active",
    # active | paused | completed | archived

    "tech_stack": ["ZMIEŃ", "react", "supabase", "vercel"],
    # Wszystkie technologie używane w projekcie

    "related_domains": ["frontend", "deployment"],
    # deployment | coding | security | workflow | ux | data | integration

    "url":         "https://ZMIEŃ.manus.space",
    "github_url":  "https://github.com/szachmacik/ZMIEŃ",

    # ── Postęp (dołączany do historii) ──────────────────────────
    "recent_progress_entry": {
        "date": TODAY,
        "what": "ZMIEŃ: Co zostało zrobione w tej sesji",
        "files_changed": ["ZMIEŃ/plik.tsx"],
        # Opcjonalnie — usuń jeśli nie potrzebujesz
    },

    # ── Otwarte kwestie ──────────────────────────────────────────
    "open_issues": [
        {"issue": "ZMIEŃ: Opis problemu", "priority": "medium"},
        # priority: high | medium | low
        # Usuń lub dodaj wpisy
    ],

    "last_activity": TODAY,
}

# ════════════════════════════════════════════════════════════════
# ZAPIS — nie zmieniaj poniżej
# ════════════════════════════════════════════════════════════════

# Pobierz aktualny stan projektu
existing_result = sb.table("manus_project_context") \
    .select("recent_progress") \
    .eq("project_name", PROJECT_NAME) \
    .execute()

existing_progress = []
if existing_result.data:
    existing_progress = existing_result.data[0].get("recent_progress") or []

# Dołącz nowy wpis do historii (max 10 ostatnich)
new_progress_entry = project.pop("recent_progress_entry", None)
if new_progress_entry:
    project["recent_progress"] = (existing_progress[-9:] + [new_progress_entry])

# Upsert projektu
result = sb.table("manus_project_context").upsert(
    project, on_conflict="project_name"
).execute()

if result.data:
    print(f"✅ Projekt zaktualizowany: {PROJECT_NAME}")
    print(f"   Status: {project['status']}")
    print(f"   Tech stack: {', '.join(project['tech_stack'])}")
    print(f"   Otwarte kwestie: {len(project.get('open_issues', []))}")
else:
    print(f"❌ Błąd: {result}")
