"""
Seed brakujących tabel Manus Brain v2 — dopasowane do rzeczywistej struktury:
- manus_domain_metrics: domain, category, period_date, experiences_count, avg_confidence,
                        avg_helpful_rate, notes_count, tokens_used, top_tags, health_score, trend_direction
- manus_system_health: snapshot_date, total_experiences, active_experiences, deprecated_count,
                       avg_confidence, high_confidence_pct, notes_last_7d, experiences_added_7d,
                       learning_runs_7d, total_cost_usd, cost_per_experience, cache_hit_rate_avg,
                       tokens_saved_total, graph_edges, avg_connections, knowledge_score,
                       efficiency_score, growth_score, overall_health, alerts
- manus_knowledge_graph: source_id, target_id, relation_type, weight, auto_detected
- manus_conversation_notes: conversation_id, session_date, topic, key_points, decisions_made,
                             problems_solved, open_issues, tools_used, projects, importance,
                             has_new_pattern, processed_at, gdrive_note_path
"""
import os
import json
from datetime import datetime, timedelta, date
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://qhscjlfavyqkaplcwhxu.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

now = datetime.utcnow()

# ─── 1. Domain Metrics (ostatnie 14 dni) ─────────────────────────────────────
print("Seeding domain_metrics...")
domains_config = [
    ("react",      "frontend",    3, 0.88),
    ("supabase",   "database",    2, 0.85),
    ("vercel",     "deployment",  2, 0.82),
    ("openai",     "ai",          1, 0.90),
    ("coolify",    "deployment",  1, 0.75),
    ("python",     "backend",     2, 0.87),
    ("deployment", "devops",      2, 0.80),
]
domain_data = []
for i in range(14):
    d = str((now - timedelta(days=13-i)).date())
    for domain, category, base_exp, base_conf in domains_config:
        exp_count = base_exp + (i // 5)
        quality = min(base_conf + (i * 0.005), 0.97)
        trend = "up" if i > 7 else ("stable" if i > 3 else "new")
        domain_data.append({
            "domain": domain,
            "category": category,
            "period_date": d,
            "experiences_count": exp_count,
            "avg_confidence": round(quality, 3),
            "avg_helpful_rate": round(quality - 0.05, 3),
            "notes_count": i + 1,
            "tokens_used": 200 + i * 50,
            "top_tags": json.dumps([domain, category, "learning"]),
            "health_score": round(quality * 100, 1),
            "trend_direction": trend,
        })

for row in domain_data:
    sb.table("manus_domain_metrics").upsert(row, on_conflict="domain,period_date").execute()
print(f"  ✓ {len(domain_data)} domain metric rows")

# ─── 2. System Health (ostatnie 14 dni + dzisiaj) ────────────────────────────
print("Seeding system_health...")
health_rows = []
for i in range(14):
    d = str((now - timedelta(days=13-i)).date())
    exp_count = 5 + i
    knowledge_score = round(min(exp_count / 20, 1.0) * 100, 1)
    efficiency_score = round((0.4 + i * 0.04) * 100, 1)
    growth_score = round((0.3 + i * 0.05) * 100, 1)
    overall = round((knowledge_score * 0.4 + efficiency_score * 0.3 + growth_score * 0.3), 1)
    health_rows.append({
        "snapshot_date": d,
        "total_experiences": exp_count,
        "active_experiences": exp_count,
        "deprecated_count": max(0, i - 10),
        "avg_confidence": round(0.65 + i * 0.02, 3),
        "high_confidence_pct": round(0.3 + i * 0.04, 3),
        "notes_last_7d": min(i * 2, 14),
        "experiences_added_7d": min(i, 5),
        "learning_runs_7d": min(i, 7),
        "total_cost_usd": round(i * 0.002, 6),
        "cost_per_experience": round(0.002 if exp_count == 0 else (i * 0.002) / exp_count, 6),
        "cache_hit_rate_avg": round(0.0 + i * 0.04, 3),
        "tokens_saved_total": i * 300,
        "graph_edges": max(0, i - 2),
        "avg_connections": round(max(0, (i - 2) / max(exp_count, 1)), 2),
        "knowledge_score": knowledge_score,
        "efficiency_score": efficiency_score,
        "growth_score": growth_score,
        "overall_health": min(overall, 95.0),
        "alerts": json.dumps([]),
    })

# Dzisiaj — rzeczywiste dane
exp_res = sb.table("manus_experiences").select("id,confidence").execute()
experiences = exp_res.data or []
pat_res = sb.table("manus_patterns").select("id").execute()
patterns = pat_res.data or []
proj_res = sb.table("manus_project_context").select("id").execute()
projects = proj_res.data or []

exp_count = len(experiences)
avg_conf = round(sum(e.get("confidence", 0.8) for e in experiences) / max(exp_count, 1), 3)
high_conf_pct = round(len([e for e in experiences if e.get("confidence", 0) >= 0.8]) / max(exp_count, 1), 3)

knowledge_score = round(min(exp_count / 20, 1.0) * 100, 1)
efficiency_score = round(0.95 * 100, 1)  # bardzo oszczędny system
growth_score = round(min(len(patterns) / 10, 1.0) * 100, 1)
overall = round(knowledge_score * 0.4 + efficiency_score * 0.3 + growth_score * 0.3, 1)

today_health = {
    "snapshot_date": str(now.date()),
    "total_experiences": exp_count,
    "active_experiences": exp_count,
    "deprecated_count": 0,
    "avg_confidence": avg_conf,
    "high_confidence_pct": high_conf_pct,
    "notes_last_7d": 5,
    "experiences_added_7d": exp_count,
    "learning_runs_7d": 0,
    "total_cost_usd": 0.0,
    "cost_per_experience": 0.0,
    "cache_hit_rate_avg": 0.0,
    "tokens_saved_total": 0,
    "graph_edges": 6,
    "avg_connections": round(6 / max(exp_count, 1), 2),
    "knowledge_score": knowledge_score,
    "efficiency_score": efficiency_score,
    "growth_score": growth_score,
    "overall_health": min(overall, 95.0),
    "alerts": json.dumps([]),
}
health_rows.append(today_health)

for row in health_rows:
    sb.table("manus_system_health").upsert(row, on_conflict="snapshot_date").execute()
print(f"  ✓ {len(health_rows)} health rows | Today health: {today_health['overall_health']}/100")

# ─── 3. Knowledge Graph ───────────────────────────────────────────────────────
print("Seeding knowledge_graph...")
exp_map = {e.get("title", "")[:25]: e["id"] for e in experiences if e.get("title")}

relations = [
    ("Delta-only updates", "Batch processing", "related_to", 0.9),
    ("Delta-only updates", "gpt-4.1-mini wystar", "related_to", 0.85),
    ("Batch processing: 8", "gpt-4.1-mini wystar", "related_to", 0.88),
    ("Supabase RLS blokuj", "Vercel wymaga NEXT_", "related_to", 0.6),
    ("React useEffect cle", "Tailwind 4 używa OK", "related_to", 0.7),
    ("Coolify wymaga heal", "Vercel wymaga NEXT_", "similar_to", 0.75),
]

graph_edges = []
for src_frag, tgt_frag, rel_type, weight in relations:
    src_id = next((eid for title, eid in exp_map.items() if src_frag[:12] in title), None)
    tgt_id = next((eid for title, eid in exp_map.items() if tgt_frag[:12] in title), None)
    if src_id and tgt_id and src_id != tgt_id:
        graph_edges.append({
            "source_id": src_id,
            "target_id": tgt_id,
            "relation_type": rel_type,
            "weight": weight,
            "auto_detected": True,
        })

if graph_edges:
    sb.table("manus_knowledge_graph").upsert(graph_edges).execute()
    print(f"  ✓ {len(graph_edges)} knowledge graph edges")
else:
    print("  ⚠ Brak pasujących par")

# ─── 4. Conversation Notes ───────────────────────────────────────────────────
print("Seeding conversation_notes...")
notes = [
    {
        "conversation_id": "conv-manus-brain-setup-001",
        "session_date": str((now - timedelta(days=1)).date()),
        "topic": "Manus Brain — setup systemu bazy doświadczeń",
        "key_points": ["RAG system na Supabase", "delta-only updates", "semantic cache SHA256", "nocny learning run o 02:00", "budget guard $5/miesiąc"],
        "decisions_made": ["Użyj gpt-4.1-mini jako domyślny model", "Batch po 8 notatek = 1 AI call", "Google Drive jako backup"],
        "problems_solved": ["Brak anon key w env — rozwiązano przez MCP", "Kolumny nie pasowały do seed — dodano ALTER TABLE"],
        "open_issues": ["Dodać auto-seed po każdej rozmowie", "Skonfigurować powiadomienia po nocnym runie"],
        "tools_used": ["supabase", "python", "rclone", "github"],
        "projects": ["manus-brain-dashboard"],
        "importance": 9,
        "has_new_pattern": True,
        "processed_at": None,
        "gdrive_note_path": "Manus Brain/notes/conv-manus-brain-setup-001.md",
    },
    {
        "conversation_id": "conv-cross-project-001",
        "session_date": str((now - timedelta(days=1)).date()),
        "topic": "Cross-project knowledge sharing — GitHub repo",
        "key_points": ["Publiczne repo szachmacik/manus-brain-skills", "SKILL.md zainstalowany lokalnie", "Szablony Python dla notatek i zapytań"],
        "decisions_made": ["Repo publiczne — brak sekretów w plikach", "SKILL.md jako główny punkt wejścia dla Manusa"],
        "problems_solved": ["Project ID Supabase w SKILL.md — zastąpiono zmienną env"],
        "open_issues": [],
        "tools_used": ["github", "git", "rclone"],
        "projects": ["manus-brain-dashboard"],
        "importance": 8,
        "has_new_pattern": False,
        "processed_at": None,
        "gdrive_note_path": "Manus Brain/notes/conv-cross-project-001.md",
    },
    {
        "conversation_id": "conv-credit-optimization-001",
        "session_date": str((now - timedelta(days=2)).date()),
        "topic": "Optymalizacja kredytów Manus — najlepsze praktyki 2026",
        "key_points": ["Stanford ACE framework — delta updates", "SimpleMem — efektywna pamięć długoterminowa", "Model routing: nano→klasyfikacja, mini→synteza"],
        "decisions_made": ["Cache TTL 30 dni", "Budget guard: zatrzymaj przy 80% limitu", "Batch processing jako priorytet"],
        "problems_solved": [],
        "open_issues": ["Wdrożyć embedding-based cache (pgvector)"],
        "tools_used": ["openai", "python"],
        "projects": ["manus-brain-dashboard"],
        "importance": 10,
        "has_new_pattern": True,
        "processed_at": None,
        "gdrive_note_path": "Manus Brain/notes/conv-credit-optimization-001.md",
    },
    {
        "conversation_id": "conv-supabase-rls-001",
        "session_date": str((now - timedelta(days=3)).date()),
        "topic": "Supabase RLS — konfiguracja Row Level Security",
        "key_points": ["RLS domyślnie blokuje wszystko", "Zawsze dodaj policy przed wdrożeniem", "anon role wymaga explicit SELECT policy"],
        "decisions_made": ["Tabele manus_* mają RLS wyłączone (wewnętrzny system)", "Produkcyjne tabele zawsze z RLS"],
        "problems_solved": ["Dashboard nie mógł czytać danych — brak policy dla anon"],
        "open_issues": [],
        "tools_used": ["supabase", "postgres"],
        "projects": ["ai-control-center"],
        "importance": 7,
        "has_new_pattern": True,
        "processed_at": None,
        "gdrive_note_path": "Manus Brain/notes/conv-supabase-rls-001.md",
    },
    {
        "conversation_id": "conv-vercel-deployment-001",
        "session_date": str((now - timedelta(days=5)).date()),
        "topic": "Vercel deployment — zmienne środowiskowe i NEXT_PUBLIC_",
        "key_points": ["NEXT_PUBLIC_ prefix wymagany dla client-side vars", "Bez prefixu = undefined w przeglądarce"],
        "decisions_made": ["Wszystkie client-side vars muszą mieć NEXT_PUBLIC_"],
        "problems_solved": ["API URL undefined po stronie klienta — brak NEXT_PUBLIC_"],
        "open_issues": [],
        "tools_used": ["vercel", "nextjs"],
        "projects": ["educational-sales-site"],
        "importance": 8,
        "has_new_pattern": True,
        "processed_at": None,
        "gdrive_note_path": "Manus Brain/notes/conv-vercel-deployment-001.md",
    },
]

for note in notes:
    sb.table("manus_conversation_notes").upsert(note, on_conflict="conversation_id").execute()
print(f"  ✓ {len(notes)} conversation notes")

print(f"\n✅ Seed zakończony!")
print(f"   Domain metrics: {len(domain_data)} rows (14 dni × 7 domen)")
print(f"   System health: {len(health_rows)} rows")
print(f"   Knowledge graph: {len(graph_edges)} edges")
print(f"   Conversation notes: {len(notes)} notes")
print(f"   Health score today: {today_health['overall_health']}/100")
