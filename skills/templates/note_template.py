"""
MANUS BRAIN — Szablon notatki po rozmowie
Skopiuj, wypełnij i uruchom po każdej ważnej sesji.
"""
from supabase import create_client
from datetime import date
import os

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

# ════════════════════════════════════════════════════════════════
# WYPEŁNIJ PONIŻSZE POLA
# ════════════════════════════════════════════════════════════════

TODAY = str(date.today())  # np. "2026-03-04"

note = {
    # ── Identyfikacja ────────────────────────────────────────────
    "conversation_id": f"{TODAY}_ZMIEN-NA-TEMAT",
    # Format: YYYY-MM-DD_slug (np. "2026-03-04_supabase-auth-fix")

    "session_date": TODAY,

    "topic": "ZMIEŃ: Krótki opis zadania (max 100 znaków)",
    # Przykład: "Naprawienie błędu CORS w Supabase Edge Functions"

    # ── Treść ────────────────────────────────────────────────────
    "key_points": [
        "ZMIEŃ: Konkretny wniosek 1 — co się nauczyliśmy",
        "ZMIEŃ: Konkretny wniosek 2 — co działa / co nie działa",
        # Dodaj więcej lub usuń — max 5 punktów
    ],

    "decisions_made": [
        "ZMIEŃ: Decyzja: używamy X zamiast Y, bo Z",
        # Usuń jeśli brak decyzji
    ],

    "problems_solved": [
        "ZMIEŃ: Problem: [opis] → Rozwiązanie: [jak naprawiono]",
        # Usuń jeśli brak problemów
    ],

    "open_issues": [
        "ZMIEŃ: Co zostało do zrobienia",
        # Usuń jeśli wszystko zamknięte
    ],

    # ── Klasyfikacja ─────────────────────────────────────────────
    "tools_used": ["ZMIEŃ", "np.", "react", "supabase", "vercel"],

    "projects": ["ZMIEŃ-na-nazwe-projektu"],
    # Nazwy projektów z manus_project_context

    "category": "general",
    # deployment | coding | security | workflow | ux | data | integration | general

    "tags": ["ZMIEŃ", "tag1", "tag2"],
    # Szczegółowe tagi do wyszukiwania

    # ── Metadane ─────────────────────────────────────────────────
    "importance": 5,
    # 1–10: 9-10=krytyczne, 7-8=ważne, 5-6=standardowe, 1-4=rutynowe

    "has_new_pattern": False,
    # True jeśli odkryto nowy wzorzec lub anty-wzorzec

    "estimated_time_saved_future": 15,
    # Ile minut zaoszczędzi ta wiedza w przyszłości (szacunek)
}

# ════════════════════════════════════════════════════════════════
# ZAPIS — nie zmieniaj poniżej
# ════════════════════════════════════════════════════════════════

result = sb.table("manus_conversation_notes").insert(note).execute()

if result.data:
    print(f"✅ Notatka zapisana: {note['conversation_id']}")
    print(f"   Ważność: {note['importance']}/10")
    print(f"   Projekty: {', '.join(note['projects'])}")
    print(f"   Tagi: {', '.join(note['tags'])}")
    print(f"   Zostanie przetworzona dziś w nocy o 02:00")
else:
    print(f"❌ Błąd zapisu: {result}")
