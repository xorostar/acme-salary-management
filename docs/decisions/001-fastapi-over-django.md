# ADR 001: FastAPI over Django for the backend

**Status:** Accepted

## Context

The role is Python. The UI is a separate Next.js app, so the backend is API-only. The two realistic choices were Django (with Django REST Framework) and FastAPI.

## Decision

FastAPI with SQLAlchemy 2.0, Alembic, and Pydantic v2.

## Reasoning

- **The backend is an API, not a website.** Django's biggest wins are templates, forms, the admin, and its auth views. None of those are used behind a Next.js frontend. What remains is the ORM and migrations, which SQLAlchemy and Alembic cover.
- **Validation is the core of this product.** Salary changes, CSV rows, and filters all need precise validation with field-level errors. Pydantic models are the request contract, the validation layer, and the OpenAPI docs in one place. DRF serializers do the same job with more ceremony.
- **Domain logic stays framework-free.** FastAPI imposes nothing on how services and domain code are structured, so the `domain` package is plain Python and tests are plain function calls. Django's model-centric design pulls logic toward models and managers.
- **Analytics queries need SQL freedom.** Correlated subqueries for current salary, filtered aggregates and bulk inserts are natural in SQLAlchemy Core. The Django ORM can do them but fights you on subqueries.
- **Test speed.** A FastAPI app with an in-memory SQLite engine boots in milliseconds per test with no settings module or test database creation step.
- **Automatic OpenAPI docs** are a useful artifact for reviewers and for the frontend.

## Trade-offs accepted

- Django ships authentication, sessions, and password hashing. Here those are about 80 lines with `bcrypt` and `PyJWT`, which is acceptable for two roles.
- Django's admin would give a free data browser. The product's own UI replaces it.
- Django's ecosystem is larger for things like audit logging. Not needed at this scope.
