# Centrum Procedur — Dekalog Projektów Manusa
> **Wersja:** 1.0 | **Data:** 2026-03-04 | **Autor:** Manus AI  
> **Cel:** Żywy dokument zasad obowiązujących we wszystkich projektach. Każdy projekt Manusa MUSI przestrzegać tych reguł.

---

## I. EFEKTYWNOŚĆ KOSZTOWA (Kredyty AI)

**Zasada:** Każde wywołanie AI musi być uzasadnione. Manus nie przepala kredytów na zadania, które można wykonać taniej lub bez AI.

### Hierarchia modeli
| Zadanie | Model | Koszt względny |
|---------|-------|----------------|
| Klasyfikacja, routing, proste pytania | `gpt-4.1-nano` | 1x |
| Synteza, analiza, kod | `gpt-4.1-mini` | 5x |
| Złożone rozumowanie, architektura | `gpt-4.1` | 25x |
| Wizja, multimodal | `gpt-4o` | 30x |

### Obowiązkowe mechanizmy oszczędzania
1. **Semantic cache SHA256** — przed każdym AI call sprawdź cache (TTL 30 dni). Identyczne zapytania = 0 kredytów.
2. **Batch processing** — grupuj minimum 8 elementów w jeden AI call zamiast 8 osobnych.
3. **Delta-only updates** — przetwarzaj TYLKO nowe dane (`processed_at IS NULL`), nigdy całą bazę od nowa.
4. **Budget guard** — każdy projekt ma limit $5/miesiąc. Po przekroczeniu 80% — alert. Po 100% — pauza.
5. **Context compression** — przed wysłaniem do AI kompresuj kontekst do maksimum 2000 tokenów na call.
6. **Model routing** — rutynowe zadania (klasyfikacja, tagowanie) = nano. Tylko złożone = mini lub wyżej.

### Kiedy NIE używać AI
- Formatowanie danych (użyj Python/regex)
- Proste walidacje (użyj Zod/schema)
- Operacje na plikach (użyj rclone/shell)
- Zapytania do bazy (użyj SQL bezpośrednio)

---

## II. BEZPIECZEŃSTWO

**Zasada:** Każdy projekt traktujemy jak gdyby obsługiwał dane prawdziwych klientów.

### Obowiązkowe praktyki
1. **Dexter Vault** — WSZYSTKIE sekrety (API keys, tokeny, hasła) przechowujemy wyłącznie w Dexter Vault. Nigdy w kodzie, nigdy w `.env` commitowanym do repo.
2. **GitHub scan przed push** — przed każdym `git push` skanuj pod kątem wycieków: `grep -rn "sk-\|Bearer \|password\|secret" --include="*.ts" --include="*.py"`.
3. **RLS zawsze włączone** — każda tabela Supabase dostępna publicznie MUSI mieć Row Level Security z odpowiednią policy.
4. **HTTPS only** — żadnych HTTP endpointów w produkcji.
5. **Input validation** — każdy endpoint waliduje input przez Zod (TypeScript) lub Pydantic (Python).
6. **Principle of least privilege** — klucze API mają tylko uprawnienia niezbędne do działania.
7. **Rotacja sekretów** — tokeny API rotujemy co 90 dni lub natychmiast po podejrzeniu wycieku.

### Checklist przed deploymentem
- [ ] Brak hardkodowanych sekretów w kodzie
- [ ] RLS włączone na wszystkich tabelach publicznych
- [ ] Zmienne środowiskowe w Dexter Vault
- [ ] Health check endpoint `/health` zwraca 200 OK
- [ ] CORS skonfigurowany tylko dla dozwolonych domen

---

## III. ARCHITEKTURA I KOD

**Zasada:** Kod ma być czytelny, modularny i łatwy do utrzymania przez kolejnych agentów (Manus, Claude, inne AI).

### Standardy techniczne
1. **TypeScript strict mode** — zawsze. Zero `any` bez komentarza wyjaśniającego dlaczego.
2. **Testy przed deploymentem** — każda nowa funkcja ma test Vitest. `pnpm test` musi przejść.
3. **Schema-first** — najpierw schemat bazy (`drizzle/schema.ts`), potem kod. Nigdy odwrotnie.
4. **tRPC dla API** — wszystkie endpointy przez tRPC. Brak ręcznych REST routes bez uzasadnienia.
5. **S3 dla plików** — pliki binarne nigdy w bazie danych. Zawsze S3 + URL w bazie.
6. **Error boundaries** — każda strona React ma ErrorBoundary.
7. **Loading states** — każde zapytanie ma stan ładowania i obsługę błędu.

### Nazewnictwo
- Pliki: `kebab-case.ts`
- Komponenty React: `PascalCase.tsx`
- Funkcje/zmienne: `camelCase`
- Stałe: `UPPER_SNAKE_CASE`
- Tabele DB: `snake_case`

### Struktura projektu (standard Manus)
```
server/
  routers/        ← tRPC routery per feature
  db.ts           ← query helpers
  db.*.ts         ← query helpers per feature
client/src/
  pages/          ← widoki
  components/     ← komponenty reużywalne
  hooks/          ← custom hooks
drizzle/schema.ts ← JEDYNE źródło prawdy o strukturze DB
```

---

## IV. PRZEPŁYW DANYCH

**Zasada:** Dane mają jeden kierunek przepływu. Brak duplikacji źródeł prawdy.

### Zasady
1. **Single source of truth** — każdy typ danych ma JEDNO miejsce przechowywania.
2. **Supabase** = baza wiedzy Manusa (doświadczenia, notatki, metryki, projekty).
3. **MySQL/TiDB** = dane aplikacji webowych (użytkownicy, sesje, dane biznesowe).
4. **Google Drive** = dokumentacja, pliki konfiguracyjne, backup wiedzy.
5. **GitHub** = kod źródłowy, SKILL.md, szablony, procedury.
6. **Dexter Vault** = sekrety i poświadczenia.

### Pipeline danych w Manus Brain
```
Rozmowa → manus_conversation_notes
         ↓ (nocny run 02:00)
         manus_experiences (wnioski)
         manus_patterns (wzorce)
         manus_domain_metrics (metryki)
         manus_system_health (zdrowie)
         ↓
         Dashboard (wizualizacja)
         ↓
         Web Push (alerty dla właściciela)
```

---

## V. DEPLOYMENT I CIĄGŁOŚĆ

**Zasada:** Każdy projekt jest zawsze gotowy do deploymentu. Brak "tymczasowych" rozwiązań w produkcji.

### Obowiązkowe elementy każdego projektu
1. **Health check** — `GET /health` → `{ status: "ok", version: "x.x.x", timestamp: "..." }`
2. **Checkpoint przed deploymentem** — `webdev_save_checkpoint` przed każdym Publish.
3. **todo.md** — aktualna lista zadań z checkboxami. Zawsze aktualizowana.
4. **README.md** — opis projektu, jak uruchomić, jak deployować.
5. **Rollback plan** — zawsze wiadomo jak wrócić do poprzedniej wersji.

### Środowiska
| Środowisko | Opis | Gdzie |
|------------|------|-------|
| `development` | Lokalne testy | Sandbox Manus |
| `staging` | Testy przed prod | Manus Space (niepubliczny) |
| `production` | Produkcja | Manus Space (publiczny) |

---

## VI. CLAUDE JAKO WEWNĘTRZNY SUPPORT

**Zasada:** Gdy Manus napotka problem z dostępem do terminala, błędy środowiska lub potrzebuje specjalistycznej pomocy — deleguje do Claude'a.

### Kiedy angażować Claude'a
- Błędy kompilacji których Manus nie może rozwiązać po 3 próbach
- Problemy z dostępem do systemu (uprawnienia, SSH, środowisko)
- Specjalistyczna analiza kodu (security audit, performance review)
- Budowa aplikacji gdy Manus jest zajęty innym zadaniem
- Weryfikacja niezależna (drugi agent sprawdza pracę pierwszego)

### Protokół delegacji do Claude'a
```
1. Opisz problem precyzyjnie (co się dzieje, co próbowałeś)
2. Przekaż kontekst: repo URL, logi błędów, oczekiwany wynik
3. Określ zakres: co Claude ma zrobić, czego NIE ruszać
4. Wskaż gdzie zapisać wynik (Google Drive / GitHub / Supabase)
5. Po zakończeniu: Manus weryfikuje i integruje wynik
```

### Wspólna baza wiedzy dla Claude'a
Claude ma dostęp do:
- `manus-brain-skills` repo na GitHub (SKILL.md, szablony, procedury)
- Tego dokumentu (PROCEDURES.md)
- `CROSS_PROJECT.md` (kontekst projektów)

---

## VII. MONITORING I ALERTY

**Zasada:** Właściciel zawsze wie co się dzieje. Brak cichych awarii.

### Typy alertów (Web Push)
| Typ | Kiedy | Priorytet |
|-----|-------|-----------|
| `learning_complete` | Nocny run zakończony | Low |
| `action_required` | Manus potrzebuje decyzji właściciela | High |
| `health_alert` | Health score < 50 | High |
| `budget_alert` | Budżet AI > 80% | Medium |
| `project_update` | Ważna zmiana w projekcie | Medium |
| `procedure_update` | Aktualizacja Dekaloga | Low |

### Harmonogram monitoringu
- **Co minutę** — dashboard odświeża dane z Supabase
- **Co noc (02:00)** — learning engine przetwarza nowe notatki
- **Co tydzień (niedziela 08:00)** — raport tygodniowy (planowane)
- **Na żądanie** — ręczny run przez dashboard

---

## VIII. ZARZĄDZANIE WIEDZĄ

**Zasada:** Każda rozmowa z Manusem to potencjalna wiedza. Nic nie ginie.

### Cykl życia wiedzy
1. **Rozmowa** → notatka w `manus_conversation_notes` (ręcznie lub automatycznie)
2. **Nocny run** → AI wyciąga wnioski → `manus_experiences`
3. **Wzorce** → powtarzające się problemy → `manus_patterns`
4. **Deprecacja** → przestarzała wiedza → status `deprecated` (nie usuwamy)
5. **GitHub** → najważniejsze wnioski → SKILL.md (dla przyszłych sesji)

### Priorytety wiedzy (importance 1-10)
| Poziom | Opis | Przykład |
|--------|------|---------|
| 9-10 | Krytyczne — wpływa na bezpieczeństwo lub koszty | "RLS blokuje bez policy" |
| 7-8 | Ważne — oszczędza czas przy kolejnych projektach | "Batch 8 notatek = 1 call" |
| 5-6 | Przydatne — dobre praktyki | "Tailwind 4 wymaga OKLCH" |
| 1-4 | Kontekstowe — specyficzne dla projektu | "Projekt X używa portu 3001" |

---

## IX. CROSS-PROJECT KNOWLEDGE SHARING

**Zasada:** Wiedza zdobyta w jednym projekcie automatycznie trafia do wszystkich.

### Mechanizm
1. Nocny run analizuje notatki ze WSZYSTKICH projektów
2. Wnioski są tagowane domeną (`vercel`, `supabase`, `react`, etc.)
3. Przed startem nowego projektu Manus pobiera relevantne doświadczenia
4. `experience_query.py` — skrypt do zapytań semantycznych do bazy

### Jak Manus korzysta z bazy przed projektem
```python
# Przykład użycia w nowym projekcie
from skills.templates.experience_query import query_experiences

# Pobierz top 5 doświadczeń dla domeny "vercel"
experiences = query_experiences(domain="vercel", limit=5)
# → Automatycznie unika znanych pułapek
```

### Rejestr projektów
Każdy projekt MUSI być zarejestrowany w `manus_project_context`:
- Nazwa, tech stack, status
- Otwarte kwestie i postępy
- Powiązane domeny wiedzy
- URL i link do repo

---

## X. CIĄGŁE DOSKONALENIE

**Zasada:** System uczy się i poprawia. Każdy błąd to lekcja, nie porażka.

### Pętla doskonalenia
```
Błąd/Problem → Notatka (importance 8+) → Nocny run → Nowe doświadczenie
                                                      ↓
                                            Aktualizacja PROCEDURES.md
                                                      ↓
                                            Push na GitHub → Dostępne dla wszystkich
```

### Metryki sukcesu systemu
| Metryka | Cel | Jak mierzyć |
|---------|-----|-------------|
| Health Score | > 70/100 | `manus_system_health.overall_health` |
| Cache hit rate | > 70% | `manus_learning_runs.cache_hit_rate` |
| Koszt miesięczny | < $5 | `manus_credit_budget.spent_usd` |
| Notatki przetworzone | 100% w 24h | `manus_conversation_notes.processed_at` |
| Confidence avg | > 0.80 | `manus_experiences.confidence` |

### Aktualizacja Dekaloga
Ten dokument jest żywy. Aktualizowany gdy:
- Pojawi się nowy wzorzec powtarzający się 3+ razy
- Zmieni się stack technologiczny
- Właściciel zgłosi nowe wymagania
- Nocny run wykryje systemowy problem

**Każda aktualizacja jest commitowana na GitHub i pushowana na Google Drive.**

---

## Szybka ściągawka (Quick Reference)

```
PRZED KAŻDYM PROJEKTEM:
  1. query_experiences(domain=...) → pobierz wiedzę
  2. Sprawdź manus_project_context → czy projekt już istnieje
  3. Przeczytaj PROCEDURES.md → odśwież zasady

PODCZAS PROJEKTU:
  4. Używaj modeli hierarchicznie (nano → mini → full)
  5. Cache przed każdym AI call
  6. Sekrety → Dexter Vault, nigdy w kodzie
  7. Testy przed deploymentem

PO PROJEKCIE:
  8. Dodaj notatkę do manus_conversation_notes
  9. Zaktualizuj manus_project_context
  10. Commit na GitHub jeśli nowe wzorce
```

---

*Centrum Procedur v1.0 — Manus AI | Ostatnia aktualizacja: 2026-03-04*  
*Dostępne: Google Drive → Manus Brain/PROCEDURES.md | GitHub → szachmacik/manus-brain-skills*
