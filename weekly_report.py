#!/usr/bin/env python3
"""
Manus Brain — Weekly Report Push Notification
Uruchamiany co niedzielę o 08:00
Pobiera dane z Supabase, generuje podsumowanie AI, wysyła Web Push na telefon.

Optymalizacje kredytów:
- Używa gpt-4.1-mini (tani model)
- Max 500 tokenów na raport
- Dane zagregowane (nie surowe) → mały kontekst
"""

import os
import json
import hashlib
import requests
from datetime import datetime, timedelta, timezone
from supabase import create_client

# ── Konfiguracja ──────────────────────────────────────────────────────────────
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY = os.environ.get("VITE_VAPID_PUBLIC_KEY", "")
VAPID_EMAIL = os.environ.get("VAPID_EMAIL", "mailto:admin@manus.space")

# Dashboard URL — link w powiadomieniu
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "https://manus-brain.manus.space")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_week_stats() -> dict:
    """Pobiera zagregowane statystyki z ostatnich 7 dni."""
    now = datetime.now(timezone.utc)
    week_ago = (now - timedelta(days=7)).isoformat()

    # Nowe doświadczenia
    exp_res = supabase.table("manus_experiences") \
        .select("id, title, category, confidence, created_at") \
        .gte("created_at", week_ago) \
        .execute()
    new_experiences = exp_res.data or []

    # Nocne runy
    runs_res = supabase.table("manus_learning_runs") \
        .select("id, status, notes_new, experiences_added, cost_estimate_usd, cache_hit_rate, started_at") \
        .gte("started_at", week_ago) \
        .execute()
    runs = runs_res.data or []

    # Notatki oczekujące
    notes_res = supabase.table("manus_conversation_notes") \
        .select("id, topic, importance, processed_at") \
        .is_("processed_at", "null") \
        .execute()
    pending_notes = notes_res.data or []

    # Ostatni health snapshot
    health_res = supabase.table("manus_system_health") \
        .select("overall_health, knowledge_score, efficiency_score, total_experiences") \
        .order("snapshot_date", desc=True) \
        .limit(2) \
        .execute()
    health_data = health_res.data or []

    # Wzorce wykryte w tygodniu
    patterns_res = supabase.table("manus_patterns") \
        .select("id, pattern_name, pattern_type, occurrence_count") \
        .gte("created_at", week_ago) \
        .execute()
    new_patterns = patterns_res.data or []

    # Budżet miesięczny
    budget_res = supabase.table("manus_credit_budget") \
        .select("budget_usd, spent_usd, tokens_used") \
        .eq("period_type", "monthly") \
        .order("period_start", desc=True) \
        .limit(1) \
        .execute()
    budget = budget_res.data[0] if budget_res.data else None

    # Oblicz metryki
    total_cost = sum(r.get("cost_estimate_usd", 0) or 0 for r in runs)
    total_notes_processed = sum(r.get("notes_new", 0) or 0 for r in runs)
    avg_cache_hit = (
        sum(r.get("cache_hit_rate", 0) or 0 for r in runs) / len(runs)
        if runs else 0
    )
    current_health = health_data[0].get("overall_health", 0) if health_data else 0
    prev_health = health_data[1].get("overall_health", 0) if len(health_data) > 1 else current_health
    health_trend = current_health - prev_health

    budget_pct = 0
    if budget:
        budget_pct = round((budget.get("spent_usd", 0) / max(budget.get("budget_usd", 5), 0.001)) * 100, 1)

    return {
        "week_start": week_ago[:10],
        "week_end": now.strftime("%Y-%m-%d"),
        "new_experiences": len(new_experiences),
        "new_experiences_list": [e["title"] for e in new_experiences[:3]],
        "learning_runs": len(runs),
        "successful_runs": sum(1 for r in runs if r.get("status") == "completed"),
        "notes_processed": total_notes_processed,
        "pending_notes": len(pending_notes),
        "pending_high_priority": sum(1 for n in pending_notes if (n.get("importance") or 0) >= 8),
        "new_patterns": len(new_patterns),
        "total_cost_usd": round(total_cost, 4),
        "avg_cache_hit_rate": round(avg_cache_hit, 2),
        "current_health": round(current_health, 1),
        "health_trend": round(health_trend, 1),
        "budget_used_pct": budget_pct,
        "total_experiences": health_data[0].get("total_experiences", 0) if health_data else 0,
    }


def generate_ai_summary(stats: dict) -> dict:
    """Generuje krótkie podsumowanie AI (max 500 tokenów)."""
    if not OPENAI_API_KEY:
        # Fallback bez AI
        health_emoji = "🟢" if stats["current_health"] >= 70 else "🟡" if stats["current_health"] >= 40 else "🔴"
        trend_arrow = "↑" if stats["health_trend"] > 0 else "↓" if stats["health_trend"] < 0 else "→"
        return {
            "title": f"Manus Brain — Raport tygodniowy ({stats['week_end']})",
            "body": (
                f"{health_emoji} Health: {stats['current_health']}/100 {trend_arrow} | "
                f"Nowe wnioski: {stats['new_experiences']} | "
                f"Koszt AI: ${stats['total_cost_usd']:.4f} | "
                f"Oczekujące notatki: {stats['pending_notes']}"
            ),
            "priority": "normal",
        }

    # Cache key — nie generuj jeśli dane się nie zmieniły
    cache_key = hashlib.sha256(json.dumps(stats, sort_keys=True).encode()).hexdigest()[:16]
    cache_res = supabase.table("manus_knowledge_cache") \
        .select("result_json") \
        .eq("query_hash", f"weekly_{cache_key}") \
        .execute()

    if cache_res.data:
        return cache_res.data[0]["result_json"]

    prompt = f"""Jesteś asystentem raportującym właścicielowi postępy AI systemu Manus Brain.
Napisz KRÓTKIE podsumowanie tygodniowe (max 2 zdania) na podstawie tych danych:

- Nowe doświadczenia: {stats['new_experiences']} (łącznie: {stats['total_experiences']})
- Nocne runy: {stats['successful_runs']}/{stats['learning_runs']} udanych
- Przetworzone notatki: {stats['notes_processed']}, oczekujące: {stats['pending_notes']}
- Health score: {stats['current_health']}/100 (trend: {stats['health_trend']:+.1f})
- Koszt tygodnia: ${stats['total_cost_usd']:.4f}
- Cache hit rate: {stats['avg_cache_hit_rate']*100:.0f}%
- Budżet miesięczny: {stats['budget_used_pct']}% wykorzystany

Zwróć JSON: {{"title": "krótki tytuł", "body": "2 zdania po polsku", "priority": "low/normal/high"}}
Priority: high jeśli health < 40 lub budżet > 80%, normal jeśli health 40-70, low jeśli wszystko OK."""

    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": "gpt-4.1-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )
        resp.raise_for_status()
        result = json.loads(resp.json()["choices"][0]["message"]["content"])

        # Zapisz do cache (TTL 7 dni)
        supabase.table("manus_knowledge_cache").upsert({
            "query_hash": f"weekly_{cache_key}",
            "query_text": "weekly_report",
            "result_json": result,
            "model_used": "gpt-4.1-mini",
            "tokens_used": resp.json()["usage"]["total_tokens"],
        }).execute()

        return result
    except Exception as e:
        print(f"[AI] Błąd generowania podsumowania: {e}")
        return {
            "title": f"Manus Brain — Raport {stats['week_end']}",
            "body": f"Health: {stats['current_health']}/100 | Nowe wnioski: {stats['new_experiences']} | Koszt: ${stats['total_cost_usd']:.4f}",
            "priority": "normal",
        }


def send_web_push(title: str, body: str, priority: str, stats: dict) -> int:
    """Wysyła Web Push do wszystkich aktywnych subskrypcji."""
    if not VAPID_PRIVATE_KEY:
        print("[Push] Brak kluczy VAPID — pomijam wysyłanie push")
        return 0

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        print("[Push] Instaluję pywebpush...")
        import subprocess
        subprocess.run(["pip3", "install", "pywebpush", "-q"], check=True)
        from pywebpush import webpush, WebPushException

    # Pobierz aktywne subskrypcje z bazy
    subs_res = supabase.table("push_subscriptions") \
        .select("id, endpoint, p256dh, auth, device_name") \
        .eq("is_active", True) \
        .execute()
    subscriptions = subs_res.data or []

    if not subscriptions:
        print("[Push] Brak aktywnych subskrypcji")
        return 0

    # Payload powiadomienia
    health_emoji = "🟢" if stats["current_health"] >= 70 else "🟡" if stats["current_health"] >= 40 else "🔴"
    priority_emoji = {"high": "🔴", "normal": "🔵", "low": "🟢"}.get(priority, "🔵")

    payload = json.dumps({
        "title": f"{priority_emoji} {title}",
        "body": body,
        "icon": "/favicon.ico",
        "badge": "/favicon.ico",
        "url": DASHBOARD_URL,
        "tag": "weekly-report",
        "data": {
            "type": "weekly_report",
            "health": stats["current_health"],
            "health_emoji": health_emoji,
            "new_experiences": stats["new_experiences"],
            "cost": stats["total_cost_usd"],
            "pending_notes": stats["pending_notes"],
            "url": DASHBOARD_URL,
        },
        "actions": [
            {"action": "open_dashboard", "title": "📊 Otwórz Dashboard"},
            {"action": "dismiss", "title": "Zamknij"},
        ],
    })

    sent = 0
    failed_ids = []

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub["endpoint"],
                    "keys": {
                        "p256dh": sub["p256dh"],
                        "auth": sub["auth"],
                    },
                },
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_EMAIL},
            )
            sent += 1
            print(f"[Push] ✓ Wysłano do: {sub.get('device_name', sub['id'][:8])}")
        except WebPushException as e:
            print(f"[Push] ✗ Błąd dla {sub['id'][:8]}: {e}")
            if e.response and e.response.status_code in (404, 410):
                failed_ids.append(sub["id"])

    # Dezaktywuj nieważne subskrypcje
    for sub_id in failed_ids:
        supabase.table("push_subscriptions") \
            .update({"is_active": False}) \
            .eq("id", sub_id) \
            .execute()
        print(f"[Push] Dezaktywowano wygasłą subskrypcję: {sub_id[:8]}")

    return sent


def save_notification_to_db(title: str, body: str, priority: str, stats: dict, sent_count: int):
    """Zapisuje powiadomienie do historii w bazie danych."""
    try:
        supabase.table("notifications").insert({
            "type": "weekly_report",
            "title": title,
            "body": body,
            "priority": priority,
            "data": {
                "stats": stats,
                "sent_to_devices": sent_count,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        print(f"[DB] Błąd zapisu powiadomienia: {e}")


def run_weekly_report():
    """Główna funkcja — uruchamiana co niedzielę o 08:00."""
    print(f"\n{'='*60}")
    print(f"[Manus Brain] Tygodniowy raport — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")

    # 1. Pobierz statystyki tygodnia
    print("\n[1/4] Pobieranie statystyk tygodnia...")
    stats = get_week_stats()
    print(f"  → Nowe doświadczenia: {stats['new_experiences']}")
    print(f"  → Nocne runy: {stats['successful_runs']}/{stats['learning_runs']}")
    print(f"  → Health score: {stats['current_health']}/100 ({stats['health_trend']:+.1f})")
    print(f"  → Koszt tygodnia: ${stats['total_cost_usd']:.4f}")
    print(f"  → Oczekujące notatki: {stats['pending_notes']} ({stats['pending_high_priority']} pilnych)")

    # 2. Generuj podsumowanie AI
    print("\n[2/4] Generowanie podsumowania AI...")
    summary = generate_ai_summary(stats)
    print(f"  → Tytuł: {summary['title']}")
    print(f"  → Treść: {summary['body']}")
    print(f"  → Priorytet: {summary['priority']}")

    # 3. Wyślij Web Push
    print("\n[3/4] Wysyłanie Web Push...")
    sent = send_web_push(summary["title"], summary["body"], summary["priority"], stats)
    print(f"  → Wysłano do {sent} urządzeń")

    # 4. Zapisz do historii
    print("\n[4/4] Zapisywanie do historii...")
    save_notification_to_db(summary["title"], summary["body"], summary["priority"], stats, sent)

    print(f"\n✅ Raport tygodniowy zakończony — {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")

    return {
        "stats": stats,
        "summary": summary,
        "sent_to": sent,
    }


if __name__ == "__main__":
    result = run_weekly_report()
    print(json.dumps(result, indent=2, default=str))
