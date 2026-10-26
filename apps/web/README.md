# ACME Salaries web app

Next.js 16 (App Router, JavaScript), Tailwind CSS 4, shadcn/ui components on Base UI, Recharts.
It is a thin client: every rule, aggregate and permission check lives in the API (`../api`).

## Run locally

```bash
npm install
cp .env.example .env.local      # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                     # http://localhost:3000
```

The API must be running and seeded (see `../api/README.md`). Demo logins are in the root README.

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Development server |
| `npm run build` | Production build (fails on prerender problems, so run it before pushing) |
| `npm test` | Vitest unit and component tests, jsdom, no network |
| `npm run lint` | ESLint with the Next.js and React hooks rules |

## Structure

```
src/app/                 routes; (app)/ holds everything behind login
src/components/          screens and shared pieces, grouped by feature
src/components/ui/       shadcn/ui primitives (generated, lightly edited) + NativeSelect
src/lib/api.js           the only place that talks to the API
src/lib/query.js         URL <-> list state (filters, sort, page)
src/lib/money.js         formatting of integer minor units
src/lib/use-api.js       data loading that drops stale responses
```

## Decisions worth knowing

- **URL is the state.** Directory and dashboard filters, sort and page live in the query string,
  so a view can be bookmarked or shared and the back button works.
- **Native selects for filters and forms.** Accessible and testable for free; the custom listbox
  added nothing for a list of nine countries.
- **Token in `sessionStorage`** (ADR 007). It survives a reload but not a closed tab. A 401 from
  any call clears it and returns to the login page.
- **Money is never parsed from floats.** The API returns integers in minor units; the UI only
  formats them. Users type major units ("85000.50") and the API converts and validates.
