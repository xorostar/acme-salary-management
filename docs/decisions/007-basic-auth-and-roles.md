# ADR 007: Basic authentication with two roles

**Status:** Accepted

## Context

Salary data is sensitive. The brief names one persona, but shipping an open endpoint that lists 10,000 salaries is not acceptable even for a demo. Full identity management (SSO, MFA, password reset) is out of scope.

## Decision

- Email and password login. Passwords hashed with `bcrypt`.
- On login the API issues a signed JWT (HS256, 12-hour expiry) carrying `user_id`, `organization_id`, and `role`. The frontend stores it in memory and an `httpOnly`-less cookie is deliberately not used, to keep the API stateless and the frontend simple.
- Two roles:
  - `hr_admin`: everything, including create/edit employees, salary changes, CSV import, payroll runs.
  - `hr_viewer`: read-only on directory, history, analytics, and export.
- Role checks are a FastAPI dependency (`require_role`) applied per router, so a route cannot forget it.
- The seed creates one user of each role with known demo credentials printed in the README.

## Reasoning

- Two roles are the minimum that demonstrates the authorization boundary and makes the "viewer can't edit" test meaningful.
- JWT keeps the API stateless, which suits a single small deployment and makes tests simple (mint a token, call the endpoint).
- Keeping the user table tenant-scoped (ADR 004) means roles are already per-organization.

## Trade-offs accepted

- No refresh tokens or revocation. A leaked token is valid until expiry. Acceptable for the scope, documented as the first thing to harden.
- Token in frontend memory means a page refresh requires re-login. Mitigated by storing it in `sessionStorage` for the demo, with the trade-off noted in the frontend README.
- No rate limiting on login.
