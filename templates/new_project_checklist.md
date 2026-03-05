# ✅ Checklist nowego projektu Manus

## Faza 1: Inicjalizacja
- [ ] `webdev_init_project` z odpowiednią nazwą
- [ ] Utwórz `todo.md` z listą wszystkich funkcji
- [ ] Zdecyduj: potrzebujesz DB/auth? → `webdev_add_feature web-db-user`
- [ ] `webdev_request_secrets` dla wszystkich kluczy API

## Faza 2: Backend
- [ ] Zdefiniuj schema w `drizzle/schema.ts`
- [ ] `pnpm db:push` — migracja do bazy
- [ ] Query helpers w `server/db.ts`
- [ ] Procedury tRPC w `server/routers.ts`
- [ ] `npx tsc --noEmit` — zero błędów

## Faza 3: Frontend
- [ ] Design tokens w `client/src/index.css` (OKLCH kolory)
- [ ] Fonty Google w `client/index.html`
- [ ] Layout w `client/src/App.tsx`
- [ ] Strony w `client/src/pages/`
- [ ] Komponenty w `client/src/components/`
- [ ] `npx tsc --noEmit` — zero błędów

## Faza 4: Jakość
- [ ] Testy Vitest w `server/*.test.ts`
- [ ] `pnpm test` — wszystkie testy przechodzą
- [ ] Sprawdź loading/error/empty states
- [ ] Sprawdź responsywność (mobile)

## Faza 5: Deployment
- [ ] `webdev_save_checkpoint` z opisem
- [ ] Kliknij Publish w UI
- [ ] Sprawdź czy działa na produkcji

## Faza 6: Wiedza
- [ ] Dodaj projekt do `manus_projects` w Supabase
- [ ] Zapisz kluczowe doświadczenia do `manus_experiences`
- [ ] Zaktualizuj `todo.md` — wszystkie ukończone pozycje jako [x]

## Bezpieczeństwo (obowiązkowe)
- [ ] Żadnych hardkodowanych sekretów
- [ ] RLS włączone na tabelach z danymi użytkowników
- [ ] `.env` w `.gitignore`
- [ ] Scan przed push: `grep -r "sk-\|password\|secret" --include="*.ts" --include="*.py"`

## Multi-AI Router (opcjonalne)
- [ ] Skopiuj `server/routers/ai.ts` z manus-brain-skills
- [ ] Dodaj `ANTHROPIC_API_KEY`, `MOONSHOT_API_KEY`, `DEEPSEEK_API_KEY` przez Secrets
- [ ] Zarejestruj w `server/routers.ts`: `ai: aiRouter`

## Web Push (opcjonalne)
- [ ] Skopiuj `server/routers/push.ts` z manus-brain-skills
- [ ] `webdev_request_secrets` dla VAPID keys
- [ ] Skopiuj `client/public/sw.js` Service Worker
- [ ] Skopiuj `client/src/hooks/usePushNotifications.ts`
