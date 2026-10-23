# ADR 004: Tenancy designed in, not exposed

**Status:** Accepted

## Context

ACME is the only customer. Multi-tenancy is deliberately out of scope (see `requirements.md`), but the product should not need a rewrite if a second organization appears.

## Decision

- An `organizations` table exists from the first migration and the seed creates exactly one row (ACME).
- Every tenant-owned table (`users`, `employees`, `salary_events`, `payroll_runs`) carries a non-null `organization_id`.
- Repositories receive `organization_id` from the authenticated user and add it to every query. No endpoint accepts an organization from the client.
- Unique constraints that are per-tenant (`employee_number`, employee `email`) are composite with `organization_id`.

## What is **not** built

- No organization management UI or API.
- No sign-up flow, no per-organization settings beyond `base_currency`.
- No row-level security or separate databases per tenant.

## Reasoning

Adding a column later to 10,000 rows is cheap. Retrofitting scoping into every query and every unique constraint after the fact is where tenancy bugs come from. Doing the scoping now costs one parameter per repository method.

## Trade-offs accepted

- Slightly more verbose repositories and tests (every call passes an organization).
- One extra join key in indexes. Negligible at this scale.
