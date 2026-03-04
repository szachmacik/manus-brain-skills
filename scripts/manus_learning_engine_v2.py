#!/usr/bin/env python3
"""
MANUS BRAIN — Learning Engine v2
=================================
Pipeline: capture → delta_filter → cache_check → batch_synthesize
          → cluster → reflect → graph_update → health_snapshot → report

Optymalizacje kredytów (2025/2026 standards):
  - Delta-only: przetwarza TYLKO nowe notatki (processed_at IS NULL)
  - Semantic cache SHA256: unika powtórnych AI calls
  - Model routing: nano (proste) / mini (złożone) — nigdy droższych
  - Batch processing: 8 notatek = 1 AI call
  - Budget guard: zatrzymuje się przy 80% limitu
  - Pre-computed views: dashboard czyta z widoków, nie liczy na żywo
  - Early exit: jeśli 0 nowych notatek → koszt $0.00
"""

import os
import json
import hashlib
import time
import logging
from datetime import datetime, date, timedelta
from typing import Optional
from supabase import create_client, Client

# ─── Konfiguracja ────────────────────────────────────────────────────────────

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_KEY", ""))
OPENAI_KEY   = os.environ.get("OPENAI_API_KEY", "")

# Modele — routing wg złożoności
MODEL_NANO     = "gpt-4.1-nano"    # ~$0.0001/1K tokens — proste klasyfikacje
MODEL_MINI     = "gpt-4.1-mini"    # ~$0.0004/1K tokens — synteza i analiza
MODEL_STANDARD = "gpt-4.1"        # ~$0.002/1K tokens  — TYLKO gdy niezbędne

# Limity
BATCH_SIZE          = 8       # notatek na jeden AI call
MAX_TOKENS_PER_CALL = 2000    # max output tokens
CACHE_TTL_DAYS      = 30      # ważność cache
BUDGET_ALERT_PCT    = 0.80    # zatrzymaj przy 80% budżetu
MAX_EXPERIENCES     = 500     # max aktywnych experiences (stare → deprecated)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("manus-brain")


# ─── Supabase client ─────────────────────────────────────────────────────────

def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL i SUPABASE_KEY muszą być ustawione")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ─── OpenAI helper z cache ────────────────────────────────────────────────────

def call_ai(sb: Client, prompt: str, system: str = "", model: str = MODEL_MINI,
            max_tokens: int = MAX_TOKENS_PER_CALL) -> tuple[str, int, bool]:
    """
    Wywołuje AI z cache'owaniem. Zwraca (output, tokens_used, from_cache).
    Jeśli wynik jest w cache → tokens_used = 0, from_cache = True.
    """
    import requests

    # Cache key = SHA256(model + system + prompt)
    cache_input = f"{model}|{system}|{prompt}"
    cache_key   = hashlib.sha256(cache_input.encode()).hexdigest()

    # Sprawdź cache
    cached = sb.table("manus_knowledge_cache") \
               .select("id, output_text, output_tokens, hit_count") \
               .eq("cache_key", cache_key) \
               .eq("is_valid", True) \
               .gt("expires_at", datetime.utcnow().isoformat()) \
               .limit(1).execute()

    if cached.data:
        entry = cached.data[0]
        # Aktualizuj hit count
        sb.table("manus_knowledge_cache").update({
            "hit_count": entry["hit_count"] + 1,
            "last_hit_at": datetime.utcnow().isoformat(),
            "tokens_saved": (entry.get("tokens_saved", 0) or 0) + entry["output_tokens"]
        }).eq("id", entry["id"]).execute()
        log.info(f"  CACHE HIT [{cache_key[:8]}] — zaoszczędzono {entry['output_tokens']} tokenów")
        return entry["output_text"], 0, True

    # Wywołaj AI
    if not OPENAI_KEY:
        log.warning("Brak OPENAI_API_KEY — pomijam AI call")
        return "", 0, False

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "max_tokens": max_tokens,
              "temperature": 0.3},
        timeout=60
    )
    resp.raise_for_status()
    data = resp.json()
    output = data["choices"][0]["message"]["content"]
    tokens = data["usage"]["total_tokens"]

    # Zapisz do cache
    expires = (datetime.utcnow() + timedelta(days=CACHE_TTL_DAYS)).isoformat()
    sb.table("manus_knowledge_cache").upsert({
        "cache_key":     cache_key,
        "input_hash":    cache_key,
        "input_preview": prompt[:200],
        "output_text":   output,
        "output_tokens": data["usage"]["completion_tokens"],
        "model_used":    model,
        "hit_count":     0,
        "tokens_saved":  0,
        "expires_at":    expires,
        "is_valid":      True,
        "updated_at":    datetime.utcnow().isoformat()
    }, on_conflict="cache_key").execute()

    log.info(f"  AI CALL [{model}] — {tokens} tokenów")
    return output, tokens, False


# ─── Budget guard ─────────────────────────────────────────────────────────────

def check_budget(sb: Client) -> tuple[bool, dict]:
    """Sprawdza budżet. Zwraca (can_proceed, budget_info)."""
    today = date.today()
    period_start = today.replace(day=1).isoformat()

    result = sb.table("manus_credit_budget") \
               .select("*") \
               .eq("period_type", "monthly") \
               .gte("period_end", today.isoformat()) \
               .limit(1).execute()

    if not result.data:
        # Utwórz nowy budżet na ten miesiąc
        import calendar
        last_day = calendar.monthrange(today.year, today.month)[1]
        period_end = today.replace(day=last_day).isoformat()
        budget = {
            "period_start": period_start, "period_end": period_end,
            "period_type": "monthly", "budget_usd": 5.0, "spent_usd": 0.0,
            "tokens_budget": 500000, "tokens_used": 0,
            "alert_threshold": BUDGET_ALERT_PCT, "is_alert_sent": False,
            "is_paused": False,
            "model_config": {
                "simple_task": MODEL_NANO, "standard_task": MODEL_MINI,
                "max_tokens_per_call": MAX_TOKENS_PER_CALL,
                "cache_ttl_days": CACHE_TTL_DAYS, "batch_size": BATCH_SIZE
            }
        }
        sb.table("manus_credit_budget").insert(budget).execute()
        return True, budget

    budget = result.data[0]
    if budget.get("is_paused"):
        log.warning("Budżet wstrzymany — pomijam run")
        return False, budget

    used_pct = budget["spent_usd"] / budget["budget_usd"]
    if used_pct >= BUDGET_ALERT_PCT:
        log.warning(f"Budżet {used_pct*100:.1f}% — zatrzymuję")
        return False, budget

    return True, budget


def update_budget(sb: Client, budget: dict, tokens_used: int, cost_usd: float):
    """Aktualizuje wydatki w budżecie."""
    sb.table("manus_credit_budget").update({
        "spent_usd":   budget["spent_usd"] + cost_usd,
        "tokens_used": budget["tokens_used"] + tokens_used,
        "updated_at":  datetime.utcnow().isoformat()
    }).eq("id", budget["id"]).execute()


# ─── PIPELINE STEP 1: Pobierz nowe notatki (delta-only) ──────────────────────

def fetch_new_notes(sb: Client, limit: int = 100) -> list[dict]:
    """Pobiera TYLKO nieprzetworzone notatki (delta-only)."""
    result = sb.table("manus_conversation_notes") \
               .select("*") \
               .is_("processed_at", "null") \
               .order("importance", desc=True) \
               .order("created_at", desc=False) \
               .limit(limit).execute()
    notes = result.data or []
    log.info(f"Znaleziono {len(notes)} nowych notatek do przetworzenia")
    return notes


# ─── PIPELINE STEP 2: Synteza wniosków z batcha notatek ──────────────────────

SYNTHESIS_SYSTEM = """Jesteś ekspertem od wyciągania wniosków z rozmów z AI.
Analizujesz notatki z sesji i wyciągasz konkretne, praktyczne wnioski.
Odpowiadasz ZAWSZE w formacie JSON. Bądź zwięzły i konkretny."""

def synthesize_batch(sb: Client, notes: list[dict]) -> tuple[list[dict], int]:
    """
    Przetwarza batch notatek → lista nowych experiences.
    Zwraca (experiences, tokens_used).
    """
    # Przygotuj skompresowany kontekst
    notes_text = []
    for n in notes:
        parts = [f"TEMAT: {n.get('topic','?')}"]
        if n.get('key_points'):
            parts.append(f"PUNKTY: {'; '.join(n['key_points'][:3])}")
        if n.get('problems_solved'):
            parts.append(f"ROZWIĄZANO: {'; '.join(n['problems_solved'][:2])}")
        if n.get('decisions_made'):
            parts.append(f"DECYZJE: {'; '.join(n['decisions_made'][:2])}")
        notes_text.append(" | ".join(parts))

    notes_block = "\n".join(f"{i+1}. {t}" for i, t in enumerate(notes_text))

    prompt = f"""Przeanalizuj te notatki z rozmów z AI i wyciągnij konkretne wnioski/doświadczenia.

NOTATKI:
{notes_block}

Zwróć JSON z listą wniosków:
{{
  "experiences": [
    {{
      "title": "Krótki tytuł (max 80 znaków)",
      "summary": "Opis co się nauczyliśmy (max 300 znaków)",
      "category": "deployment|coding|security|workflow|ux|general|data|integration",
      "domain": "opcjonalnie: vercel|supabase|react|python|docker|etc",
      "tags": ["tag1", "tag2"],
      "confidence": 0.7,
      "action": "new|update|skip",
      "similar_title": "tytuł istniejącego wpisu jeśli action=update"
    }}
  ],
  "patterns": [
    {{
      "name": "Nazwa wzorca",
      "type": "anti_pattern|best_practice|pitfall|workflow",
      "description": "Opis wzorca",
      "trigger": "Kiedy się pojawia"
    }}
  ]
}}

Wyciągnij max 3-5 najważniejszych wniosków. Pomiń oczywiste rzeczy."""

    output, tokens, from_cache = call_ai(sb, prompt, SYNTHESIS_SYSTEM, MODEL_MINI)

    if not output:
        return [], 0

    try:
        # Wyciągnij JSON z odpowiedzi
        start = output.find('{')
        end   = output.rfind('}') + 1
        if start >= 0 and end > start:
            data = json.loads(output[start:end])
            return data.get("experiences", []), tokens
    except json.JSONDecodeError as e:
        log.error(f"Błąd parsowania JSON: {e}")

    return [], tokens


# ─── PIPELINE STEP 3: Upsert experiences ─────────────────────────────────────

def upsert_experiences(sb: Client, new_exps: list[dict], existing: list[dict]) -> tuple[int, int]:
    """
    Dodaje nowe lub aktualizuje istniejące experiences.
    Zwraca (added, updated).
    """
    added = updated = 0
    existing_titles = {e["title"].lower(): e for e in existing}

    for exp in new_exps:
        if exp.get("action") == "skip":
            continue

        title_lower = exp["title"].lower()

        # Sprawdź czy podobny wpis już istnieje
        similar_key = exp.get("similar_title", "").lower()
        existing_entry = existing_titles.get(similar_key) or existing_titles.get(title_lower)

        if existing_entry and exp.get("action") == "update":
            # Aktualizuj istniejący
            new_confidence = min(1.0, existing_entry["confidence"] * 0.7 + exp["confidence"] * 0.3)
            sb.table("manus_experiences").update({
                "summary":     exp["summary"],
                "confidence":  new_confidence,
                "tags":        list(set((existing_entry.get("tags") or []) + (exp.get("tags") or []))),
                "version":     (existing_entry.get("version") or 1) + 1,
                "delta_type":  "updated",
                "updated_at":  datetime.utcnow().isoformat()
            }).eq("id", existing_entry["id"]).execute()
            updated += 1
            log.info(f"  UPDATED: {exp['title'][:50]}")
        else:
            # Dodaj nowy
            sb.table("manus_experiences").insert({
                "title":       exp["title"],
                "summary":     exp["summary"],
                "category":    exp.get("category", "general"),
                "domain":      exp.get("domain"),
                "tags":        exp.get("tags", []),
                "confidence":  exp.get("confidence", 0.6),
                "status":      "active",
                "source_type": "conversation",
                "version":     1,
                "delta_type":  "new",
                "helpful_count": 0,
                "harmful_count": 0,
                "applied_count": 0
            }).execute()
            added += 1
            log.info(f"  ADDED: {exp['title'][:50]}")

    return added, updated


# ─── PIPELINE STEP 4: Reflection — deprecate słabych ─────────────────────────

def reflect_and_deprecate(sb: Client) -> int:
    """
    Deprecate experiences które są szkodliwe lub przestarzałe.
    Zwraca liczbę zdeprecjonowanych.
    """
    # Reguła 1: harmful > helpful AND confidence < 0.3
    result = sb.table("manus_experiences") \
               .select("id, title, harmful_count, helpful_count, confidence") \
               .eq("status", "active") \
               .lt("confidence", 0.3) \
               .execute()

    deprecated = 0
    for exp in (result.data or []):
        if (exp.get("harmful_count", 0) or 0) > (exp.get("helpful_count", 0) or 0):
            sb.table("manus_experiences").update({
                "status":     "deprecated",
                "delta_type": "deprecated",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", exp["id"]).execute()
            deprecated += 1
            log.info(f"  DEPRECATED: {exp['title'][:50]}")

    # Reguła 2: Ogranicz do MAX_EXPERIENCES (najstarsze → archived)
    all_active = sb.table("manus_experiences") \
                   .select("id, created_at") \
                   .eq("status", "active") \
                   .order("confidence", desc=False) \
                   .order("created_at", desc=False) \
                   .execute()

    if len(all_active.data or []) > MAX_EXPERIENCES:
        to_archive = (all_active.data or [])[:(len(all_active.data) - MAX_EXPERIENCES)]
        for exp in to_archive:
            sb.table("manus_experiences").update({
                "status": "archived", "updated_at": datetime.utcnow().isoformat()
            }).eq("id", exp["id"]).execute()

    return deprecated


# ─── PIPELINE STEP 5: Knowledge graph update ─────────────────────────────────

def update_knowledge_graph(sb: Client, new_exp_titles: list[str], tokens_budget: int) -> int:
    """
    Wykrywa relacje między nowymi a istniejącymi experiences.
    Używa nano modelu — bardzo tanie.
    Zwraca tokens_used.
    """
    if not new_exp_titles or tokens_budget < 500:
        return 0

    # Pobierz top experiences do porównania
    existing = sb.table("manus_experiences") \
                 .select("id, title, category, tags") \
                 .eq("status", "active") \
                 .order("confidence", desc=True) \
                 .limit(20).execute()

    if not existing.data or len(existing.data) < 2:
        return 0

    titles_list = "\n".join(f"- {e['title']}" for e in (existing.data or []))
    new_list    = "\n".join(f"- {t}" for t in new_exp_titles[:5])

    prompt = f"""Znajdź relacje między nowymi a istniejącymi wnioskami.

NOWE:
{new_list}

ISTNIEJĄCE:
{titles_list}

Zwróć JSON:
{{"relations": [{{"source": "tytuł nowego", "target": "tytuł istniejącego", "type": "reinforces|extends|requires|contradicts"}}]}}

Max 5 relacji. Tylko oczywiste powiązania."""

    output, tokens, _ = call_ai(sb, prompt, "", MODEL_NANO, 500)

    if output:
        try:
            start = output.find('{')
            end   = output.rfind('}') + 1
            data  = json.loads(output[start:end])
            relations = data.get("relations", [])

            # Pobierz ID po tytułach
            all_exps = {e["title"].lower(): e["id"] for e in (existing.data or [])}

            for rel in relations[:5]:
                src_id = all_exps.get(rel.get("source", "").lower())
                tgt_id = all_exps.get(rel.get("target", "").lower())
                if src_id and tgt_id and src_id != tgt_id:
                    sb.table("manus_knowledge_graph").upsert({
                        "source_id":    src_id,
                        "target_id":    tgt_id,
                        "relation_type": rel.get("type", "reinforces"),
                        "weight":        0.6,
                        "auto_detected": True
                    }, on_conflict="source_id,target_id,relation_type").execute()
        except Exception as e:
            log.warning(f"Graph update error: {e}")

    return tokens


# ─── PIPELINE STEP 6: Domain metrics update ──────────────────────────────────

def update_domain_metrics(sb: Client):
    """Aktualizuje metryki per domena/kategoria (bez AI — czyste SQL)."""
    today = date.today().isoformat()

    # Pobierz agregaty z bazy
    result = sb.table("manus_experiences") \
               .select("category, domain, confidence, helpful_count, harmful_count") \
               .eq("status", "active").execute()

    if not result.data:
        return

    # Grupuj per category
    from collections import defaultdict
    groups: dict = defaultdict(list)
    for exp in result.data:
        key = (exp.get("domain") or "general", exp.get("category") or "general")
        groups[key].append(exp)

    for (domain, category), exps in groups.items():
        avg_conf = sum(e.get("confidence", 0) for e in exps) / len(exps)
        total_helpful = sum(e.get("helpful_count", 0) or 0 for e in exps)
        total_harmful = sum(e.get("harmful_count", 0) or 0 for e in exps)
        helpful_rate  = total_helpful / max(1, total_helpful + total_harmful)

        # Health score: 60% confidence + 40% helpful rate
        health = avg_conf * 0.6 + helpful_rate * 0.4

        sb.table("manus_domain_metrics").upsert({
            "domain":           domain,
            "category":         category,
            "period_date":      today,
            "experiences_count": len(exps),
            "avg_confidence":   round(avg_conf, 3),
            "avg_helpful_rate": round(helpful_rate, 3),
            "health_score":     round(health, 3),
            "trend_direction":  "improving" if health > 0.7 else "stable" if health > 0.4 else "declining"
        }, on_conflict="domain,category,period_date").execute()

    log.info(f"  Zaktualizowano metryki dla {len(groups)} domen/kategorii")


# ─── PIPELINE STEP 7: System health snapshot ─────────────────────────────────

def create_health_snapshot(sb: Client, run_stats: dict) -> dict:
    """Tworzy dzienny snapshot stanu systemu."""
    today = date.today().isoformat()

    # Pobierz dane
    exps = sb.table("manus_experiences").select("id, status, confidence").execute()
    notes = sb.table("manus_conversation_notes").select("id, session_date").execute()
    runs  = sb.table("manus_learning_runs") \
              .select("cost_estimate_usd, cache_hit_rate, tokens_saved_cache") \
              .eq("status", "completed") \
              .gte("started_at", (datetime.utcnow() - timedelta(days=7)).isoformat()) \
              .execute()
    graph = sb.table("manus_knowledge_graph").select("id", count="exact").execute()

    all_exps   = exps.data or []
    active_exp = [e for e in all_exps if e["status"] == "active"]
    depr_exp   = [e for e in all_exps if e["status"] == "deprecated"]
    all_notes  = notes.data or []
    all_runs   = runs.data or []

    avg_conf = sum(e.get("confidence", 0) for e in active_exp) / max(1, len(active_exp))
    high_conf_pct = len([e for e in active_exp if e.get("confidence", 0) > 0.8]) / max(1, len(active_exp))

    notes_7d = len([n for n in all_notes if n.get("session_date", "") >= (date.today() - timedelta(days=7)).isoformat()])
    total_cost = sum(r.get("cost_estimate_usd", 0) or 0 for r in all_runs)
    avg_cache  = sum(r.get("cache_hit_rate", 0) or 0 for r in all_runs) / max(1, len(all_runs))
    tokens_saved = sum(r.get("tokens_saved_cache", 0) or 0 for r in all_runs)
    graph_edges  = graph.count or 0

    # Composite scores (0-100)
    knowledge_score  = min(100, avg_conf * 60 + high_conf_pct * 40) * 100 / 100
    efficiency_score = min(100, avg_cache * 60 + min(1, tokens_saved / 10000) * 40) * 100
    growth_score     = min(100, min(1, notes_7d / 10) * 50 + min(1, run_stats.get("added", 0) / 5) * 50) * 100
    overall_health   = (knowledge_score * 0.4 + efficiency_score * 0.3 + growth_score * 0.3)

    # Alerty
    alerts = []
    if avg_conf < 0.5:
        alerts.append({"type": "warning", "msg": "Niska średnia pewność wniosków"})
    if avg_cache < 0.5:
        alerts.append({"type": "info", "msg": "Cache hit rate poniżej 50%"})
    if notes_7d == 0:
        alerts.append({"type": "warning", "msg": "Brak nowych notatek w ostatnich 7 dniach"})

    snapshot = {
        "snapshot_date":       today,
        "total_experiences":   len(all_exps),
        "active_experiences":  len(active_exp),
        "deprecated_count":    len(depr_exp),
        "avg_confidence":      round(avg_conf, 3),
        "high_confidence_pct": round(high_conf_pct, 3),
        "notes_last_7d":       notes_7d,
        "experiences_added_7d": run_stats.get("added", 0),
        "learning_runs_7d":    len(all_runs),
        "total_cost_usd":      round(total_cost, 6),
        "cost_per_experience": round(total_cost / max(1, len(active_exp)), 6),
        "cache_hit_rate_avg":  round(avg_cache, 3),
        "tokens_saved_total":  tokens_saved,
        "graph_edges":         graph_edges,
        "avg_connections":     round(graph_edges / max(1, len(active_exp)), 2),
        "knowledge_score":     round(knowledge_score, 1),
        "efficiency_score":    round(efficiency_score, 1),
        "growth_score":        round(growth_score, 1),
        "overall_health":      round(overall_health, 1),
        "alerts":              alerts
    }

    sb.table("manus_system_health").upsert(snapshot, on_conflict="snapshot_date").execute()
    log.info(f"  Health snapshot: overall={overall_health:.1f}/100")
    return snapshot


# ─── PIPELINE STEP 8: Context snapshot (dla Manusa) ──────────────────────────

def save_context_snapshot(sb: Client, run_id: str, snapshot_type: str = "post_run"):
    """
    Zapisuje snapshot kontekstu — co Manus powinien wiedzieć na początku rozmowy.
    To jest serce systemu RAG.
    """
    # Top experiences
    top_exp = sb.table("manus_experiences") \
                .select("title, summary, category, confidence, tags") \
                .eq("status", "active") \
                .order("confidence", desc=True) \
                .limit(15).execute()

    # Active projects
    projects = sb.table("manus_project_context") \
                 .select("project_name, display_name, status, tech_stack, open_issues") \
                 .eq("status", "active") \
                 .limit(10).execute()

    # Recent patterns
    patterns = sb.table("manus_patterns") \
                 .select("pattern_name, pattern_type, description, recommended_action") \
                 .eq("status", "active") \
                 .order("occurrence_count", desc=True) \
                 .limit(5).execute()

    # Knowledge gaps — kategorie z małą liczbą experiences
    domain_metrics = sb.table("manus_domain_metrics") \
                       .select("domain, category, experiences_count, health_score") \
                       .order("experiences_count", desc=False) \
                       .limit(5).execute()

    gaps = [
        {"domain": m["domain"], "category": m["category"], "count": m["experiences_count"]}
        for m in (domain_metrics.data or [])
        if m.get("experiences_count", 0) < 3
    ]

    sb.table("manus_context_snapshots").insert({
        "snapshot_type":   snapshot_type,
        "learning_run_id": run_id,
        "top_experiences": top_exp.data or [],
        "active_projects": projects.data or [],
        "recent_patterns": patterns.data or [],
        "knowledge_gaps":  gaps,
        "recommendations": [
            "Sprawdź SKILL.md przed każdym zadaniem",
            "Używaj doświadczeń z bazy jako kontekstu",
            "Zapisuj nowe wzorce po każdej rozmowie"
        ]
    }).execute()

    log.info(f"  Context snapshot zapisany ({snapshot_type})")


# ─── PIPELINE STEP 9: Generuj raport markdown ────────────────────────────────

def generate_report(run_stats: dict, health: dict, budget: dict) -> str:
    """Generuje raport markdown bez AI (zero tokenów)."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    cost = run_stats.get("cost_usd", 0)
    cache_pct = run_stats.get("cache_hit_rate", 0) * 100

    lines = [
        f"# Manus Brain — Raport nocny {now}",
        "",
        "## Podsumowanie",
        f"- **Notatki przeskanowane:** {run_stats.get('notes_scanned', 0)}",
        f"- **Nowe wnioski:** +{run_stats.get('added', 0)}",
        f"- **Zaktualizowane:** {run_stats.get('updated', 0)}",
        f"- **Zdeprecjonowane:** {run_stats.get('deprecated', 0)}",
        f"- **Koszt:** ${cost:.5f}",
        f"- **Cache hit rate:** {cache_pct:.0f}%",
        f"- **Tokeny użyte:** {run_stats.get('tokens_used', 0):,}",
        f"- **Tokeny zaoszczędzone:** {run_stats.get('tokens_saved', 0):,}",
        "",
        "## Stan systemu",
        f"- **Health score:** {health.get('overall_health', 0):.1f}/100",
        f"- **Aktywne wnioski:** {health.get('active_experiences', 0)}",
        f"- **Średnia pewność:** {health.get('avg_confidence', 0)*100:.1f}%",
        f"- **Krawędzie grafu:** {health.get('graph_edges', 0)}",
        "",
        "## Budżet miesięczny",
        f"- **Wydane:** ${budget.get('spent_usd', 0):.5f} / ${budget.get('budget_usd', 5):.2f}",
        f"- **Pozostało:** ${budget.get('budget_usd', 5) - budget.get('spent_usd', 0):.5f}",
        "",
    ]

    if health.get("alerts"):
        lines.append("## Alerty")
        for alert in health["alerts"]:
            icon = "⚠️" if alert["type"] == "warning" else "ℹ️"
            lines.append(f"- {icon} {alert['msg']}")
        lines.append("")

    return "\n".join(lines)


# ─── GŁÓWNA FUNKCJA ───────────────────────────────────────────────────────────

def run_learning_pipeline(run_type: str = "nightly", triggered_by: str = "scheduler"):
    """
    Główny pipeline uczenia się.
    Uruchamiany co noc o 02:00 przez harmonogram.
    """
    start_time = time.time()
    log.info(f"=== Manus Brain Learning Engine v2 — {run_type} ===")

    sb = get_supabase()

    # Sprawdź budżet
    can_proceed, budget = check_budget(sb)
    if not can_proceed:
        log.warning("Budżet wyczerpany lub wstrzymany — przerywam")
        return

    # Utwórz rekord run
    run_record = sb.table("manus_learning_runs").insert({
        "run_type":     run_type,
        "triggered_by": triggered_by,
        "status":       "running",
        "started_at":   datetime.utcnow().isoformat(),
        "model_used":   MODEL_MINI
    }).execute()
    run_id = run_record.data[0]["id"]

    # Context snapshot PRZED runem
    save_context_snapshot(sb, run_id, "pre_run")

    # Pobierz nowe notatki (delta-only)
    notes = fetch_new_notes(sb)
    notes_scanned = len(notes)

    if notes_scanned == 0:
        log.info("Brak nowych notatek — early exit (koszt: $0.00)")
        # Aktualizuj run jako completed z zerowymi kosztami
        sb.table("manus_learning_runs").update({
            "status":             "completed",
            "notes_scanned":      0,
            "notes_new":          0,
            "experiences_added":  0,
            "experiences_updated": 0,
            "tokens_used":        0,
            "cost_estimate_usd":  0.0,
            "cache_hit_rate":     1.0,
            "completed_at":       datetime.utcnow().isoformat(),
            "duration_seconds":   int(time.time() - start_time),
            "summary_md":         "# Brak nowych notatek\n\nSystem nie miał nic do przetworzenia."
        }).eq("id", run_id).execute()
        return

    # Pobierz istniejące experiences (do porównania)
    existing_exps = sb.table("manus_experiences") \
                      .select("id, title, confidence, tags, helpful_count, harmful_count") \
                      .eq("status", "active") \
                      .execute()
    existing = existing_exps.data or []

    # Przetwarzaj w batchach
    total_tokens = 0
    total_added  = 0
    total_updated = 0
    new_exp_titles: list[str] = []
    cache_hits = 0
    total_calls = 0

    for i in range(0, len(notes), BATCH_SIZE):
        batch = notes[i:i + BATCH_SIZE]
        log.info(f"Batch {i//BATCH_SIZE + 1}/{(len(notes)-1)//BATCH_SIZE + 1} ({len(batch)} notatek)")

        # Sprawdź budżet przed każdym batchem
        can_proceed, budget = check_budget(sb)
        if not can_proceed:
            log.warning("Budżet wyczerpany w trakcie — zatrzymuję")
            break

        new_exps, tokens = synthesize_batch(sb, batch)
        total_tokens += tokens
        total_calls  += 1
        if tokens == 0:
            cache_hits += 1

        added, updated = upsert_experiences(sb, new_exps, existing)
        total_added   += added
        total_updated += updated
        new_exp_titles.extend([e["title"] for e in new_exps if e.get("action") != "skip"])

        # Oznacz notatki jako przetworzone
        note_ids = [n["id"] for n in batch]
        sb.table("manus_conversation_notes").update({
            "processed_at":    datetime.utcnow().isoformat(),
            "learning_run_id": run_id
        }).in_("id", note_ids).execute()

    # Reflection
    deprecated = reflect_and_deprecate(sb)

    # Knowledge graph (tylko jeśli mamy nowe experiences i budżet)
    graph_tokens = 0
    remaining_budget = budget["budget_usd"] - budget["spent_usd"]
    if new_exp_titles and remaining_budget > 0.001:
        graph_tokens = update_knowledge_graph(sb, new_exp_titles, int(remaining_budget * 1000))
        total_tokens += graph_tokens

    # Domain metrics (bez AI)
    update_domain_metrics(sb)

    # Koszt
    cost_usd = total_tokens * 0.0000004  # ~$0.0004/1K tokens dla mini

    # Health snapshot
    run_stats = {
        "notes_scanned": notes_scanned,
        "added":         total_added,
        "updated":       total_updated,
        "deprecated":    deprecated,
        "tokens_used":   total_tokens,
        "tokens_saved":  0,  # będzie obliczone z cache stats
        "cost_usd":      cost_usd,
        "cache_hit_rate": cache_hits / max(1, total_calls)
    }
    health = create_health_snapshot(sb, run_stats)

    # Context snapshot PO runie
    save_context_snapshot(sb, run_id, "post_run")

    # Raport
    report_md = generate_report(run_stats, health, budget)
    duration  = int(time.time() - start_time)

    # Aktualizuj budżet
    update_budget(sb, budget, total_tokens, cost_usd)

    # Finalizuj run
    sb.table("manus_learning_runs").update({
        "status":               "completed",
        "notes_scanned":        notes_scanned,
        "notes_new":            notes_scanned,
        "experiences_added":    total_added,
        "experiences_updated":  total_updated,
        "experiences_deprecated": deprecated,
        "tokens_used":          total_tokens,
        "cost_estimate_usd":    cost_usd,
        "cache_hit_rate":       cache_hits / max(1, total_calls),
        "completed_at":         datetime.utcnow().isoformat(),
        "duration_seconds":     duration,
        "summary_md":           report_md,
        "key_learnings":        new_exp_titles[:10]
    }).eq("id", run_id).execute()

    # Zapisz raport na Google Drive (opcjonalnie)
    _save_report_to_gdrive(report_md, run_stats)

    log.info(f"=== DONE === +{total_added} added, {total_updated} updated, {deprecated} deprecated")
    log.info(f"    Koszt: ${cost_usd:.5f} | Tokeny: {total_tokens:,} | Czas: {duration}s")


def _save_report_to_gdrive(report_md: str, stats: dict):
    """Opcjonalnie zapisuje raport na Google Drive przez rclone."""
    try:
        import subprocess
        today = date.today().isoformat()
        fname = f"/tmp/manus_run_{today}.md"
        with open(fname, "w") as f:
            f.write(report_md)
        result = subprocess.run([
            "rclone", "copy", fname,
            "manus_google_drive:Manus Brain/learning-runs/",
            "--config", "/home/ubuntu/.gdrive-rclone.ini"
        ], capture_output=True, timeout=30)
        if result.returncode == 0:
            log.info(f"  Raport zapisany na Google Drive: learning-runs/{today}.md")
    except Exception as e:
        log.warning(f"  Google Drive upload failed: {e}")


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    run_type = sys.argv[1] if len(sys.argv) > 1 else "nightly"
    triggered_by = sys.argv[2] if len(sys.argv) > 2 else "manual"
    run_learning_pipeline(run_type, triggered_by)
