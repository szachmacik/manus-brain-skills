-- ============================================================
-- MANUS BRAIN — Migration 002: Extended Schema v2
-- Optymalny przepływ danych: context capture → embed → cluster
-- → synthesize → reflect → serve → learn
-- ============================================================

-- ─── 1. KNOWLEDGE GRAPH — relacje między doświadczeniami ────
CREATE TABLE IF NOT EXISTS manus_knowledge_graph (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id       uuid NOT NULL REFERENCES manus_experiences(id) ON DELETE CASCADE,
  target_id       uuid NOT NULL REFERENCES manus_experiences(id) ON DELETE CASCADE,
  relation_type   text NOT NULL, -- 'reinforces','contradicts','extends','requires','supersedes'
  weight          float DEFAULT 0.5 CHECK (weight BETWEEN 0 AND 1),
  auto_detected   boolean DEFAULT true,
  created_at      timestamptz DEFAULT now(),
  UNIQUE(source_id, target_id, relation_type)
);

-- ─── 2. DOMAIN METRICS — trendy per kategoria/domena ────────
CREATE TABLE IF NOT EXISTS manus_domain_metrics (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  domain          text NOT NULL,
  category        text NOT NULL,
  period_date     date NOT NULL DEFAULT CURRENT_DATE,
  experiences_count    integer DEFAULT 0,
  avg_confidence       float DEFAULT 0,
  avg_helpful_rate     float DEFAULT 0,
  notes_count          integer DEFAULT 0,
  tokens_used          integer DEFAULT 0,
  top_tags             jsonb DEFAULT '[]',
  health_score         float DEFAULT 0,  -- 0-1 composite score
  trend_direction      text DEFAULT 'stable', -- 'improving','declining','stable'
  created_at      timestamptz DEFAULT now(),
  UNIQUE(domain, category, period_date)
);

-- ─── 3. SYSTEM HEALTH — codzienny snapshot stanu systemu ────
CREATE TABLE IF NOT EXISTS manus_system_health (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  snapshot_date   date NOT NULL DEFAULT CURRENT_DATE,
  -- Knowledge quality
  total_experiences    integer DEFAULT 0,
  active_experiences   integer DEFAULT 0,
  deprecated_count     integer DEFAULT 0,
  avg_confidence       float DEFAULT 0,
  high_confidence_pct  float DEFAULT 0,  -- % > 0.8
  -- Learning velocity
  notes_last_7d        integer DEFAULT 0,
  experiences_added_7d integer DEFAULT 0,
  learning_runs_7d     integer DEFAULT 0,
  -- Cost efficiency
  total_cost_usd       float DEFAULT 0,
  cost_per_experience  float DEFAULT 0,
  cache_hit_rate_avg   float DEFAULT 0,
  tokens_saved_total   integer DEFAULT 0,
  -- Graph connectivity
  graph_edges          integer DEFAULT 0,
  avg_connections      float DEFAULT 0,
  -- Composite scores
  knowledge_score      float DEFAULT 0,  -- 0-100
  efficiency_score     float DEFAULT 0,  -- 0-100
  growth_score         float DEFAULT 0,  -- 0-100
  overall_health       float DEFAULT 0,  -- 0-100
  -- Alerts
  alerts               jsonb DEFAULT '[]',
  created_at      timestamptz DEFAULT now(),
  UNIQUE(snapshot_date)
);

-- ─── 4. PROJECT CONTEXT — kontekst aktywnych projektów ──────
CREATE TABLE IF NOT EXISTS manus_project_context (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_name    text NOT NULL UNIQUE,
  display_name    text,
  description     text,
  status          text DEFAULT 'active', -- 'active','paused','completed','archived'
  tech_stack      text[] DEFAULT '{}',
  related_domains text[] DEFAULT '{}',
  key_decisions   jsonb DEFAULT '[]',
  open_issues     jsonb DEFAULT '[]',
  recent_progress jsonb DEFAULT '[]',
  gdrive_path     text,
  url             text,
  last_activity   date,
  experience_refs uuid[] DEFAULT '{}',  -- powiązane experiences
  note_count      integer DEFAULT 0,
  created_at      timestamptz DEFAULT now(),
  updated_at      timestamptz DEFAULT now()
);

-- ─── 5. PATTERN REGISTRY — wykryte wzorce zachowań ──────────
CREATE TABLE IF NOT EXISTS manus_patterns (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  pattern_name    text NOT NULL,
  pattern_type    text NOT NULL, -- 'anti_pattern','best_practice','workflow','pitfall'
  description     text NOT NULL,
  trigger_context text,          -- kiedy ten wzorzec się pojawia
  recommended_action text,       -- co zrobić gdy wykryty
  examples        jsonb DEFAULT '[]',
  occurrence_count integer DEFAULT 1,
  last_seen_at    timestamptz DEFAULT now(),
  confidence      float DEFAULT 0.5,
  tags            text[] DEFAULT '{}',
  status          text DEFAULT 'active',
  created_at      timestamptz DEFAULT now(),
  updated_at      timestamptz DEFAULT now()
);

-- ─── 6. CONTEXT SNAPSHOTS — snapshoty kontekstu przed runem ─
CREATE TABLE IF NOT EXISTS manus_context_snapshots (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  snapshot_type   text NOT NULL, -- 'pre_run','post_run','manual'
  learning_run_id uuid REFERENCES manus_learning_runs(id),
  top_experiences jsonb DEFAULT '[]',   -- top 10 experiences w momencie snapshotu
  active_projects jsonb DEFAULT '[]',
  recent_patterns jsonb DEFAULT '[]',
  credit_status   jsonb DEFAULT '{}',
  knowledge_gaps  jsonb DEFAULT '[]',   -- obszary gdzie brakuje wiedzy
  recommendations jsonb DEFAULT '[]',   -- co Manus powinien zbadać
  created_at      timestamptz DEFAULT now()
);

-- ─── 7. FEEDBACK LOG — feedback od użytkownika ──────────────
CREATE TABLE IF NOT EXISTS manus_feedback (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  experience_id   uuid REFERENCES manus_experiences(id),
  feedback_type   text NOT NULL, -- 'helpful','harmful','outdated','incomplete','perfect'
  comment         text,
  context         text,          -- w jakim kontekście użyto
  given_by        text DEFAULT 'user',
  processed       boolean DEFAULT false,
  created_at      timestamptz DEFAULT now()
);

-- ─── INDEKSY dla optymalnego przepływu danych ───────────────

-- Experiences — szybkie wyszukiwanie
CREATE INDEX IF NOT EXISTS idx_exp_status_confidence
  ON manus_experiences(status, confidence DESC);
CREATE INDEX IF NOT EXISTS idx_exp_category_domain
  ON manus_experiences(category, domain);
CREATE INDEX IF NOT EXISTS idx_exp_tags
  ON manus_experiences USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_exp_updated
  ON manus_experiences(updated_at DESC);

-- Notes — delta processing
CREATE INDEX IF NOT EXISTS idx_notes_unprocessed
  ON manus_conversation_notes(processed_at) WHERE processed_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_notes_session_date
  ON manus_conversation_notes(session_date DESC);
CREATE INDEX IF NOT EXISTS idx_notes_importance
  ON manus_conversation_notes(importance DESC);

-- Knowledge graph — traversal
CREATE INDEX IF NOT EXISTS idx_graph_source
  ON manus_knowledge_graph(source_id);
CREATE INDEX IF NOT EXISTS idx_graph_target
  ON manus_knowledge_graph(target_id);
CREATE INDEX IF NOT EXISTS idx_graph_relation
  ON manus_knowledge_graph(relation_type);

-- Domain metrics — time series
CREATE INDEX IF NOT EXISTS idx_domain_metrics_date
  ON manus_domain_metrics(period_date DESC);
CREATE INDEX IF NOT EXISTS idx_domain_metrics_domain
  ON manus_domain_metrics(domain, period_date DESC);

-- System health — time series
CREATE INDEX IF NOT EXISTS idx_health_date
  ON manus_system_health(snapshot_date DESC);

-- Cache — lookup
CREATE INDEX IF NOT EXISTS idx_cache_key
  ON manus_knowledge_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_cache_expires
  ON manus_knowledge_cache(expires_at) WHERE is_valid = true;

-- Patterns — search
CREATE INDEX IF NOT EXISTS idx_patterns_type
  ON manus_patterns(pattern_type, status);
CREATE INDEX IF NOT EXISTS idx_patterns_tags
  ON manus_patterns USING GIN(tags);

-- Feedback — processing queue
CREATE INDEX IF NOT EXISTS idx_feedback_unprocessed
  ON manus_feedback(processed) WHERE processed = false;

-- ─── VIEWS dla dashboardu ────────────────────────────────────

-- Aktualny stan wiedzy (dla dashboardu)
CREATE OR REPLACE VIEW manus_knowledge_summary AS
SELECT
  COUNT(*) FILTER (WHERE status = 'active')          AS active_count,
  COUNT(*) FILTER (WHERE status = 'deprecated')      AS deprecated_count,
  ROUND(AVG(confidence) FILTER (WHERE status='active')::numeric, 3) AS avg_confidence,
  COUNT(*) FILTER (WHERE status='active' AND confidence > 0.8) AS high_confidence_count,
  COUNT(DISTINCT category)                           AS category_count,
  COUNT(DISTINCT domain) FILTER (WHERE domain IS NOT NULL) AS domain_count,
  MAX(updated_at)                                    AS last_updated
FROM manus_experiences;

-- Top experiences per kategoria
CREATE OR REPLACE VIEW manus_top_by_category AS
SELECT DISTINCT ON (category)
  id, title, summary, category, confidence, helpful_count, applied_count, tags
FROM manus_experiences
WHERE status = 'active'
ORDER BY category, confidence DESC;

-- Statystyki notatek
CREATE OR REPLACE VIEW manus_notes_stats AS
SELECT
  COUNT(*) AS total_notes,
  COUNT(*) FILTER (WHERE processed_at IS NULL) AS pending_notes,
  COUNT(*) FILTER (WHERE processed_at IS NOT NULL) AS processed_notes,
  COUNT(*) FILTER (WHERE session_date >= CURRENT_DATE - 7) AS notes_last_7d,
  COUNT(*) FILTER (WHERE session_date >= CURRENT_DATE - 30) AS notes_last_30d,
  MAX(session_date) AS latest_session
FROM manus_conversation_notes;

-- Efektywność cache
CREATE OR REPLACE VIEW manus_cache_stats AS
SELECT
  COUNT(*) FILTER (WHERE is_valid = true) AS active_entries,
  COUNT(*) FILTER (WHERE is_valid = false OR expires_at < now()) AS expired_entries,
  SUM(hit_count) AS total_hits,
  SUM(tokens_saved) AS total_tokens_saved,
  ROUND(AVG(hit_count)::numeric, 1) AS avg_hits_per_entry
FROM manus_knowledge_cache;

-- ─── RLS POLICIES ───────────────────────────────────────────
ALTER TABLE manus_knowledge_graph    ENABLE ROW LEVEL SECURITY;
ALTER TABLE manus_domain_metrics     ENABLE ROW LEVEL SECURITY;
ALTER TABLE manus_system_health      ENABLE ROW LEVEL SECURITY;
ALTER TABLE manus_project_context    ENABLE ROW LEVEL SECURITY;
ALTER TABLE manus_patterns           ENABLE ROW LEVEL SECURITY;
ALTER TABLE manus_context_snapshots  ENABLE ROW LEVEL SECURITY;
ALTER TABLE manus_feedback           ENABLE ROW LEVEL SECURITY;

-- Public read (dashboard)
CREATE POLICY "public_read_graph"    ON manus_knowledge_graph    FOR SELECT USING (true);
CREATE POLICY "public_read_metrics"  ON manus_domain_metrics     FOR SELECT USING (true);
CREATE POLICY "public_read_health"   ON manus_system_health      FOR SELECT USING (true);
CREATE POLICY "public_read_projects" ON manus_project_context    FOR SELECT USING (true);
CREATE POLICY "public_read_patterns" ON manus_patterns           FOR SELECT USING (true);
CREATE POLICY "public_read_snapshots" ON manus_context_snapshots FOR SELECT USING (true);
CREATE POLICY "public_read_feedback" ON manus_feedback           FOR SELECT USING (true);

-- Allow insert from service role (learning engine)
CREATE POLICY "service_insert_graph"    ON manus_knowledge_graph    FOR INSERT WITH CHECK (true);
CREATE POLICY "service_insert_metrics"  ON manus_domain_metrics     FOR INSERT WITH CHECK (true);
CREATE POLICY "service_insert_health"   ON manus_system_health      FOR INSERT WITH CHECK (true);
CREATE POLICY "service_insert_projects" ON manus_project_context    FOR ALL USING (true);
CREATE POLICY "service_insert_patterns" ON manus_patterns           FOR ALL USING (true);
CREATE POLICY "service_insert_snapshots" ON manus_context_snapshots FOR INSERT WITH CHECK (true);
CREATE POLICY "service_insert_feedback" ON manus_feedback           FOR ALL USING (true);
