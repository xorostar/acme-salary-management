# How AI was used

The brief asks for intentional use of AI tools. This page records what was delegated, what
was decided by me, how the output was checked, and where the AI was wrong.

**Tool:** Claude Code (Anthropic), run as an agent in the repository with shell access. Every
commit made with it carries a `Co-Authored-By` trailer, so `git log` shows which work it
touched.

## Working method

1. **Requirements before code.** The first session was spent reading the brief and writing
   [requirements.md](requirements.md), [architecture.md](architecture.md), and the decision
   records. No application code existed until those were committed.
2. **I made the product and stack decisions. The AI argued options.** Examples include
   FastAPI over Django (ADR 001), which features to keep or cut, and keeping payroll to a
   record with no payment integration.
3. **Small, verifiable steps.** Each feature landed as one commit with its tests. Tests run
   after every change, and lint plus format checks run before every commit.
4. **Measure, don't assume.** Performance claims come from a benchmark script against the
   seeded 10,000-employee database ([performance.md](performance.md)). One AI "optimization"
   was reverted because the measurement contradicted it.
5. **Drive the real app.** Unit tests cannot show that screens work, so a Playwright
   walkthrough exercises nine journeys against a production build and the real API. The
   same script produced the screenshots and the demo video.

## Prompts

The prompts that started each session, verbatim.

**Session 1, 23 Oct 2026: understanding the brief**

> "C:\Users\devk\Downloads\Salary Management Assessment- Candidates.pdf" If this assessment
> and I want you to carefully understand it, what is the motive, what is the goal, what do
> you want to achieve, and how are we going to achieve it. Look through the assessment very
> carefully, understand everything and gather all the requirements and stuff like that you
> need to be like you are a senior software engineer, which is doing this assessment. So you
> need to be aware of every edge case, everything that comes with this, and all these things
> that you need to understand and plan out the building the assessment and what they are
> requiring and solve this.

**Session 1: scope decisions I made after reading its plan**

> I think we should add the authentication and the role stuff, not the major ones, but just
> the basics. And payroll processing ones is will not need to integrate any payment provider
> for this, but if we can do it with little effort, then I think we can do this. And for the
> multi-tenancy, we can note down that this is left out of scope deliberately, but the
> system should be scalable enough to accommodate this later on. and for the text type, the
> front end is next.js.jsx, it's fine. And for the backend, it is Python. But need to decide
> whether to go with the fast API or the Django or anything other framework. So I leave it up
> to you. Which suits better. And why? So let's start building this

That session produced the requirements, the architecture, seven ADRs, the scaffold and
models, the pure domain layer with tests, and authentication.

**Session 2, 26 Oct 2026: readiness review**

> go thorugh this assesments folder and see if we're ready to submit the assesmnent this is
> the requiremnets for the assesment "C:\Users\devk\Downloads\Salary Management Assessment-
> Candidates.pdf"

The review compared the repository against each requirement in the brief. It found the
frontend, seed script, analytics, CSV, payroll, deployment, video, and two promised docs
missing. It also found an import-time crash in uncommitted code.

**Session 2: build the rest**

> Can you complete this?

## What was checked by hand, and where the AI was wrong

| What happened | How it was caught | Outcome |
|---|---|---|
| A service method named `list` shadowed the builtin, so a later `list[...]` annotation crashed at import. | The readiness review imported every module. | Renamed. API tests added for the endpoints that had none. |
| The same mistake was made again in the payroll repository. | The test run crashed on import. | Added ruff's `A` rules (flake8-builtins). Lint now catches this whole class of bug. |
| The AI replaced a correlated subquery with a grouped join, assuming it was faster. | Benchmark: about 2x slower on SQLite. | Reverted, with the reason recorded in code and in [performance.md](performance.md). |
| The CSV parser returned valid rows even when other rows failed. That leaves "all or nothing" to every caller. | A test written to the requirement ("a partially valid file is never imported") failed. | The parser returns no rows whenever any row fails. |
| Test suite took 17 s, mostly bcrypt at production cost. | Reading `--durations`. | Tests hash at minimum cost; production unchanged. About 2x faster. |
| Next.js 16 differs from older versions: `params` is a promise, and URL hooks need Suspense or the build fails. | The framework ships docs for agents, read before writing pages. The production build failed once on a layout. | Pages wrap URL-reading components in Suspense. The nav highlight streams separately. |
| shadcn/ui's current style uses Base UI, not Radix, so the Select needs a label map. | Read the generated component source before use. | Native `<select>` for filters and forms, which is simpler, accessible, and testable. |
| A walkthrough assertion matched hidden text from a previous page. Next 16 keeps visited routes mounted. | Playwright strict-mode error. | Exact matching in the test. Not an app bug. |
| A shell heredoc mangled `\n` escapes in a test file. | Lint reported a syntax error. | Edited with the file tool instead. |

## What the AI was not trusted with

- **Money arithmetic.** Every conversion and rounding rule has tests against hand-computed
  values, including JPY with no minor unit and half-cent ties.
- **Authorization.** Role checks are enforced in the API. Tests assert that a read-only user
  gets 403 on every write, and the walkthrough asserts that the UI hides those actions.
- **Claims in these docs.** Numbers in performance.md come from runs of the benchmark
  script. Test counts come from the test runners.
