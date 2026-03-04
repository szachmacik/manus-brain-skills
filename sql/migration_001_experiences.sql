-- ============================================================
-- MANUS BRAIN — Baza Doświadczeń
-- Oparta na: Stanford ACE (2025), SimpleMem (2026), Maxim AI best practices
-- Projekt: ai-control-center (qhscjlfavyqkaplcwhxu)
-- ============================================================

-- ---------------------------------------------------------------
-- 1. manus_experiences
--    Każde doświadczenie/wniosek wyciągnięty z rozmów.
--    Wzorowane na ACE "playbook bullets" z metadanymi jakości.
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.manus_experiences (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Treść i klasyfikacja
    title           TEXT NOT NULL,                          -- krótki tytuł (max 80 znaków)
    summary         TEXT NOT NULL,                          -- skompresowany wniosek (SimpleMem: semantic lossless compression)
    full_content    TEXT,                                   -- pełna treść (opcjonalna, ładowana na żądanie)
    category        TEXT NOT NULL DEFAULT 'general',        -- deployment | coding | security | ux | workflow | general
    tags            TEXT[] DEFAULT '{}',                    -- tagi do hybrid search
    domain          TEXT DEFAULT 'global',                  -- projekt/domena której dotyczy

    -- ACE-style quality counters (zamiast fine-tuningu)
    helpful_count   INTEGER NOT NULL DEFAULT 0,             -- ile razy ten wniosek pomógł
    harmful_count   INTEGER NOT NULL DEFAULT 0,             -- ile razy zaszkodził / był błędny
    applied_count   INTEGER NOT NULL DEFAULT 0,             -- ile razy zastosowano
    confidence      FLOAT NOT NULL DEFAULT 0.5,             -- 0.0-1.0, aktualizowane automatycznie

    -- Status i cykl życia
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active','deprecated','pending_review','archived')),
    source_type     TEXT NOT NULL DEFAULT 'conversation'
                    CHECK (source_type IN ('conversation','task_result','manual','reflection')),
    source_ref      TEXT,                                   -- ID rozmowy/zadania źródłowego

    -- Delta tracking (ACE: nigdy nie nadpisuj całości, tylko delta)
    version         INTEGER NOT NULL DEFAULT 1,
    parent_id       UUID REFERENCES public.manus_experiences(id),  -- poprzednia wersja
    delta_type      TEXT CHECK (delta_type IN ('add','modify','merge','split',NULL)),

    -- Embedding do semantic search (pgvector jeśli dostępne, inaczej NULL)
    embedding_hash  TEXT,                                   -- SHA256 summary — do cache invalidation

    -- Timestamps
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_applied_at TIMESTAMPTZ,
    reviewed_at     TIMESTAMPTZ
);

-- Indeksy do szybkiego wyszukiwania
CREATE INDEX IF NOT EXISTS idx_experiences_category    ON public.manus_experiences(category);
CREATE INDEX IF NOT EXISTS idx_experiences_status      ON public.manus_experiences(status);
CREATE INDEX IF NOT EXISTS idx_experiences_domain      ON public.manus_experiences(domain);
CREATE INDEX IF NOT EXISTS idx_experiences_confidence  ON public.manus_experiences(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_experiences_tags        ON public.manus_experiences USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_experiences_updated     ON public.manus_experiences(updated_at DESC);

-- RLS
ALTER TABLE public.manus_experiences ENABLE ROW LEVEL SECURITY;
CREATE POLICY "manus_full_access" ON public.manus_experiences
    USING (true) WITH CHECK (true);


-- ---------------------------------------------------------------
-- 2. manus_learning_runs
--    Log każdego cyklicznego przebiegu uczenia się.
--    Kluczowe dla delta-only updates — wiemy co już przetworzono.
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.manus_learning_runs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identyfikacja przebiegu
    run_type            TEXT NOT NULL DEFAULT 'nightly'
                        CHECK (run_type IN ('nightly','manual','incremental','emergency')),
    triggered_by        TEXT DEFAULT 'scheduler',           -- scheduler | user | manus

    -- Zakres przetwarzania (delta-only: tylko nowe od last_run)
    processed_from      TIMESTAMPTZ,                        -- od kiedy przetwarzano notatki
    processed_until     TIMESTAMPTZ,                        -- do kiedy (zazwyczaj now())
    notes_scanned       INTEGER DEFAULT 0,                  -- liczba przeskanowanych notatek
    notes_new           INTEGER DEFAULT 0,                  -- ile było nowych (delta)
    notes_skipped       INTEGER DEFAULT 0,                  -- ile pominięto (cache hit)

    -- Wyniki uczenia
    experiences_added   INTEGER DEFAULT 0,
    experiences_updated INTEGER DEFAULT 0,
    experiences_deprecated INTEGER DEFAULT 0,
    insights_generated  INTEGER DEFAULT 0,

    -- Optymalizacja kredytów (kluczowe metryki)
    tokens_used         INTEGER DEFAULT 0,                  -- łączne tokeny zużyte
    tokens_saved_cache  INTEGER DEFAULT 0,                  -- tokeny zaoszczędzone przez cache
    model_used          TEXT DEFAULT 'gpt-4.1-mini',        -- model użyty (tani domyślnie)
    cost_estimate_usd   FLOAT DEFAULT 0.0,                  -- szacowany koszt w USD
    cache_hit_rate      FLOAT DEFAULT 0.0,                  -- % cache hitów

    -- Status i czas
    status              TEXT NOT NULL DEFAULT 'running'
                        CHECK (status IN ('running','completed','failed','partial')),
    error_message       TEXT,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at        TIMESTAMPTZ,
    duration_seconds    INTEGER,

    -- Podsumowanie dla dashboardu (pre-computed, żeby dashboard nie robił AI calls)
    summary_md          TEXT,                               -- markdown podsumowanie dla rodzica
    key_learnings       JSONB DEFAULT '[]'::jsonb           -- top 3-5 wniosków z tego przebiegu
);

CREATE INDEX IF NOT EXISTS idx_runs_status      ON public.manus_learning_runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_started     ON public.manus_learning_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_type        ON public.manus_learning_runs(run_type);

ALTER TABLE public.manus_learning_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "manus_full_access" ON public.manus_learning_runs
    USING (true) WITH CHECK (true);


-- ---------------------------------------------------------------
-- 3. manus_knowledge_cache
--    Cache wyników AI — serce optymalizacji kredytów.
--    Semantic cache: jeśli podobne pytanie było już przetworzone, nie wywołuj LLM.
--    Inspiracja: Maxim AI / Bifrost semantic caching (15-70% oszczędności).
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.manus_knowledge_cache (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Klucz cache
    cache_key       TEXT NOT NULL UNIQUE,                   -- SHA256(normalized_input)
    input_hash      TEXT NOT NULL,                          -- hash surowego inputu
    input_preview   TEXT,                                   -- pierwsze 200 znaków (do debugowania)

    -- Wynik
    output_text     TEXT NOT NULL,                          -- skompresowana odpowiedź
    output_tokens   INTEGER DEFAULT 0,
    model_used      TEXT,

    -- Metryki użycia
    hit_count       INTEGER NOT NULL DEFAULT 0,             -- ile razy ten cache był użyty
    tokens_saved    INTEGER NOT NULL DEFAULT 0,             -- łączne tokeny zaoszczędzone
    last_hit_at     TIMESTAMPTZ,

    -- TTL i ważność
    expires_at      TIMESTAMPTZ DEFAULT (now() + INTERVAL '30 days'),
    is_valid        BOOLEAN NOT NULL DEFAULT true,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cache_key        ON public.manus_knowledge_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_cache_valid      ON public.manus_knowledge_cache(is_valid, expires_at);
CREATE INDEX IF NOT EXISTS idx_cache_hits       ON public.manus_knowledge_cache(hit_count DESC);

ALTER TABLE public.manus_knowledge_cache ENABLE ROW LEVEL SECURITY;
CREATE POLICY "manus_full_access" ON public.manus_knowledge_cache
    USING (true) WITH CHECK (true);


-- ---------------------------------------------------------------
-- 4. manus_skill_registry
--    Rejestr umiejętności Manusa z wersjonowaniem i oceną skuteczności.
--    Odpowiednik ACE "playbook sections" na poziomie skill.
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.manus_skill_registry (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    skill_name      TEXT NOT NULL UNIQUE,                   -- np. "deploy-vercel", "supabase-migration"
    display_name    TEXT NOT NULL,
    description     TEXT,
    category        TEXT DEFAULT 'general',
    version         TEXT DEFAULT '1.0.0',

    -- Skuteczność (aktualizowana przez learning runs)
    success_rate    FLOAT DEFAULT 0.5,                      -- 0.0-1.0
    usage_count     INTEGER DEFAULT 0,
    last_used_at    TIMESTAMPTZ,

    -- Zawartość skill (skrócona wersja do kontekstu)
    skill_summary   TEXT,                                   -- max 500 tokenów — do szybkiego ładowania
    gdrive_path     TEXT,                                   -- pełna ścieżka na Google Drive

    -- Status
    status          TEXT DEFAULT 'active'
                    CHECK (status IN ('active','deprecated','draft')),
    needs_update    BOOLEAN DEFAULT false,                  -- flaga: wymaga aktualizacji po learning run

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.manus_skill_registry ENABLE ROW LEVEL SECURITY;
CREATE POLICY "manus_full_access" ON public.manus_skill_registry
    USING (true) WITH CHECK (true);


-- ---------------------------------------------------------------
-- 5. manus_conversation_notes
--    Notatki z rozmów — surowe dane wejściowe do learning runs.
--    Manus zapisuje tu skrót każdej ważnej rozmowy (nie pełną treść).
--    Delta tracking: processed_at = NULL oznacza "do przetworzenia".
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.manus_conversation_notes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identyfikacja rozmowy
    conversation_id TEXT,                                   -- ID z platformy Manus (jeśli dostępne)
    session_date    DATE NOT NULL DEFAULT CURRENT_DATE,

    -- Treść (skompresowana — SimpleMem: semantic lossless compression)
    topic           TEXT NOT NULL,                          -- temat rozmowy (1 zdanie)
    key_points      TEXT[] DEFAULT '{}',                    -- główne punkty (max 5)
    decisions_made  TEXT[] DEFAULT '{}',                    -- podjęte decyzje
    problems_solved TEXT[] DEFAULT '{}',                    -- rozwiązane problemy
    open_issues     TEXT[] DEFAULT '{}',                    -- nierozwiązane kwestie
    tools_used      TEXT[] DEFAULT '{}',                    -- użyte narzędzia/serwisy
    projects        TEXT[] DEFAULT '{}',                    -- projekty których dotyczyło

    -- Jakość i priorytet
    importance      INTEGER DEFAULT 3                       -- 1-5, wyższy = ważniejszy
                    CHECK (importance BETWEEN 1 AND 5),
    has_new_pattern BOOLEAN DEFAULT false,                  -- czy zawiera nowy wzorzec do nauczenia

    -- Delta processing
    processed_at    TIMESTAMPTZ,                            -- NULL = czeka na przetworzenie
    learning_run_id UUID REFERENCES public.manus_learning_runs(id),

    -- Metadane
    gdrive_note_path TEXT,                                  -- ścieżka do pełnej notatki na GDrive
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notes_unprocessed ON public.manus_conversation_notes(processed_at)
    WHERE processed_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_notes_date        ON public.manus_conversation_notes(session_date DESC);
CREATE INDEX IF NOT EXISTS idx_notes_importance  ON public.manus_conversation_notes(importance DESC);

ALTER TABLE public.manus_conversation_notes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "manus_full_access" ON public.manus_conversation_notes
    USING (true) WITH CHECK (true);


-- ---------------------------------------------------------------
-- 6. manus_credit_budget
--    Budżet kredytów — kontrola kosztów na poziomie systemu.
--    Manus sprawdza ten budżet przed każdym wywołaniem AI.
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.manus_credit_budget (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    period_type     TEXT DEFAULT 'monthly'
                    CHECK (period_type IN ('daily','weekly','monthly')),

    -- Limity
    budget_usd      FLOAT NOT NULL DEFAULT 5.0,             -- limit w USD
    spent_usd       FLOAT NOT NULL DEFAULT 0.0,             -- wydane
    tokens_budget   INTEGER DEFAULT 500000,                 -- limit tokenów
    tokens_used     INTEGER DEFAULT 0,

    -- Alerty
    alert_threshold FLOAT DEFAULT 0.8,                      -- alert przy 80% budżetu
    is_alert_sent   BOOLEAN DEFAULT false,
    is_paused       BOOLEAN DEFAULT false,                  -- pauza gdy przekroczono

    -- Model routing priorytety (JSON config)
    model_config    JSONB DEFAULT '{
        "simple_task": "gpt-4.1-nano",
        "standard_task": "gpt-4.1-mini",
        "complex_task": "gpt-4.1-mini",
        "max_tokens_per_call": 2000,
        "cache_ttl_days": 30,
        "batch_size": 10
    }'::jsonb,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.manus_credit_budget ENABLE ROW LEVEL SECURITY;
CREATE POLICY "manus_full_access" ON public.manus_credit_budget
    USING (true) WITH CHECK (true);

-- Domyślny budżet miesięczny
INSERT INTO public.manus_credit_budget (period_start, period_end, period_type, budget_usd)
VALUES (date_trunc('month', now())::date, (date_trunc('month', now()) + INTERVAL '1 month - 1 day')::date, 'monthly', 5.0)
ON CONFLICT DO NOTHING;


-- ---------------------------------------------------------------
-- 7. Trigger: auto-update updated_at
-- ---------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
    CREATE TRIGGER trg_experiences_updated BEFORE UPDATE ON public.manus_experiences
        FOR EACH ROW EXECUTE FUNCTION update_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TRIGGER trg_cache_updated BEFORE UPDATE ON public.manus_knowledge_cache
        FOR EACH ROW EXECUTE FUNCTION update_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TRIGGER trg_skills_updated BEFORE UPDATE ON public.manus_skill_registry
        FOR EACH ROW EXECUTE FUNCTION update_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TRIGGER trg_budget_updated BEFORE UPDATE ON public.manus_credit_budget
        FOR EACH ROW EXECUTE FUNCTION update_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
