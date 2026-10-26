# Testing guide

A feature-by-feature script for testing the app by hand before submitting or after deploying.
Each section says what the feature is, why it exists, the steps, and what you should see.
Automated tests are at the end.

Allow about 45 minutes for the full manual pass, or about 10 minutes for the smoke test in
section 15.

## 0. Setup

**Local**

```bash
# Terminal 1: API on http://localhost:8000
cd apps/api
python -m venv .venv && .venv/Scripts/activate
pip install -e ".[dev]"
alembic upgrade head
python -m app.seed --reset          # fresh 10,000 employees; rerun any time to reset
uvicorn app.main:app --reload

# Terminal 2: web on http://localhost:3000
cd apps/web
npm install
cp .env.example .env.local
npm run dev
```

**Logins** (password `acme-demo-2026` for both)

| Email | Role | Can |
|---|---|---|
| `admin@acme.example` | HR admin | Everything |
| `viewer@acme.example` | HR viewer | Read and export only |

**Known facts about the seed data** (useful for checking numbers)

| Fact | Value |
|---|---|
| Employees | 10,000 (`AC00001` to `AC10000`) |
| Active today | 9,321 |
| Terminated | 679 |
| Countries | 9 (US largest, then India, UK, Germany, Canada, Brazil, Japan, Australia, Singapore) |
| Salary events | 43,024 |
| Planning rates | Two sets, effective 1 Jan 2025 and 1 Jan 2026 |

Tip: keep the browser dev tools Network tab open. Every action should return 2xx, or 422
with a clear message when you entered something invalid.

---

## 1. Login and session

**What:** email and password login, with a signed token kept for the browser tab's lifetime.

| # | Steps | Expected |
|---|---|---|
| 1.1 | Open the app while logged out | Redirected to the login page |
| 1.2 | Log in as admin with a wrong password | "Email or password is incorrect." |
| 1.3 | Log in with an unknown email | The same message, so the app never reveals which emails exist |
| 1.4 | Log in as admin correctly | Dashboard; header shows "Hana Admin" and an **HR admin** badge |
| 1.5 | Reload the page | Still logged in |
| 1.6 | Close the tab, open the app in a new tab | Asked to log in again; the session lasts only for the tab |
| 1.7 | In dev tools → Application → Session Storage, change `acme.token` to `garbage`, then click Employees | Back on login with "Your session expired. Please sign in again." |
| 1.8 | Click the log-out icon (top right) | Back on the login page |

---

## 2. Dashboard: "how does the org pay people?"

**What:** company-wide pay figures in USD at dated planning rates, filterable and sliceable.

| # | Steps | Expected |
|---|---|---|
| 2.1 | Open the Dashboard | Tiles show **9,321** headcount, about $745.6M payroll, median about $69,400, and the 10th to 90th percentile range |
| 2.2 | Look at the subtitle | "Active employees on {today}". Terminated people are excluded. |
| 2.3 | Hover "Planning rates effective 1 Jan 2026" under the histogram | Tooltip lists each rate, e.g. 1 GBP = 1.27 USD |
| 2.4 | Breakdown, **Country** (default) | 9 rows, largest first. A "Median (local)" column appears, e.g. India in ₹, Japan in ¥. |
| 2.5 | Click **Department**, then **Level** | Table regroups. The local-currency column disappears because groups mix currencies. |
| 2.6 | Choose Country = **India** | Every tile, chart and table updates; headcount about 1,862. The URL gains `?country_code=IN`. |
| 2.7 | Copy the URL into a new tab | The same filtered view opens; views can be shared |
| 2.8 | Add Level = **L4**, then click **Clear filters** | Narrows further, then returns to the full org |
| 2.9 | Scroll to the heatmap | Level rows by country columns. Darker cells pay more. Hovering a cell shows the median and headcount. |
| 2.10 | Filter to a combination with nobody, e.g. Legal + VP + Singapore | "Nobody matches these filters", not an error |

**Cross-check:** after recording a raise in section 4, the median for that person's country
may move slightly. A raise dated in the future must not change anything until its date.

---

## 3. Employee directory

**What:** server-side search, filter, sort and paging over 10,000 people.

| # | Steps | Expected |
|---|---|---|
| 3.1 | Open **Employees** | 25 rows, "9,321 matching employees", Active tab selected |
| 3.2 | Type `sharma` in search | Results update about 0.3 s after you stop typing; the URL gets `q=sharma` |
| 3.3 | Search an employee number, e.g. `AC00042` | That person |
| 3.4 | Search an email fragment, e.g. `tanaka` | People with that name or email |
| 3.5 | Set Department and Level filters | The count drops; the filters combine |
| 3.6 | Click **Terminated**, then **All** | 679, then 10,000 (with filters cleared). Leavers show a red "Left" badge. |
| 3.7 | Click **Annual salary** header | Highest paid first; the arrow shows direction. Click again for ascending. |
| 3.8 | Click **Name**, **Hired**, **Level** headers | Each sorts; the URL keeps `sort` and `order` |
| 3.9 | Next and previous page, then rows per page = 100 | The range text updates ("26–50 of …"); changing a filter jumps back to page 1 |
| 3.10 | Go to a far page, e.g. `?page=300` | Loads as fast as page 1 |
| 3.11 | Search nonsense, e.g. `zzzz` | "No employees match" with a hint |

Note: salaries in the directory show in each person's own currency (₹, ¥, £…). The
dashboard is where everything is converted to USD.

---

## 4. Employee profile and salary history

**What:** one person's record, current pay, and an append-only salary history.

| # | Steps | Expected |
|---|---|---|
| 4.1 | Click any name in the directory | Name, status badge, title · level · department · country |
| 4.2 | Check "Current annual salary" | Matches the directory value, with "Since {date}" |
| 4.3 | Check Salary history | Newest first: date, amount, % change from the previous entry, reason, recorded by. Seed entries say "Data import". |
| 4.4 | Check the step chart | Salary over time, rising at each event |
| 4.5 | Open `/employees/999999` | "This employee does not exist." |

---

## 5. Record a salary change (admin)

**What:** a new dated history entry. Nothing is overwritten, and future dates schedule a raise.

| # | Steps | Expected |
|---|---|---|
| 5.1 | Profile → **Record salary change**, type an amount 8% above current | Live hint "+8.0% vs today" |
| 5.2 | Reason **Promotion**, effective today, save | Toast "Salary change recorded"; new top row says Promotion, recorded by Hana Admin; current salary updated |
| 5.3 | Record again with the **same date** | Error on the date field: "a salary event already exists on this date; record a correction on a new date" |
| 5.4 | Enter `9999999999999999` | "exceeds the maximum supported amount" |
| 5.5 | Effective date before the hire date | "cannot be before hire date …" |
| 5.6 | Pick a **Japan** employee and enter `5000000.50` | "JPY allows at most 0 decimal places" (yen has no cents) |
| 5.7 | A UK employee, `65000.505` | "GBP allows at most 2 decimal places" |
| 5.8 | Effective date **next month** | Toast "Change scheduled for …". Current salary unchanged. A "Scheduled" note on the card and a "Scheduled" badge in history. |
| 5.9 | Reason **Other** | A text box appears for the description, which is saved as the reason |
| 5.10 | Cancel or press Esc mid-way | Nothing saved |

---

## 6. Add an employee (admin)

**What:** a new hire with a starting salary, which becomes the first history entry.

| # | Steps | Expected |
|---|---|---|
| 6.1 | Employees → **Add employee**; choose Country = United Kingdom | Pay currency fills in GBP |
| 6.2 | Fill everything validly, salary `98000`, save | Toast; you land on the new profile with £98,000.00 and one "Hire" history row dated the hire date |
| 6.3 | Add another person with the **same employee number** | "is already in use" under Employee number |
| 6.4 | Same email as an existing person | "is already in use" under Work email |
| 6.5 | Email `not-an-email`, no job title, no department | All errors shown at once, each under its field |
| 6.6 | Employee number with a space, e.g. `AB 12` | Error explaining the allowed format |
| 6.7 | Lower-case number `ab123`, email in capitals | Saved as `AB123` and lower-case email (normalized) |

---

## 7. Edit an employee (admin)

**What:** change details. It is protected against two people editing at once, and a
relocation needs a salary in the new currency.

| # | Steps | Expected |
|---|---|---|
| 7.1 | Profile → **Edit details**, change Job title, save | Profile shows the new title |
| 7.2 | **Two-tab conflict:** open the same Edit page in two tabs. Save a change in tab A, then save a different change in tab B. | Tab B: "This employee was changed by someone else. Reload and try again." Tab A's change is kept. |
| 7.3 | **Relocation:** change Country US → Germany | Pay currency becomes EUR and a "Relocation: salary in EUR" box appears |
| 7.4 | Save with the relocation salary empty | Error; nothing changes |
| 7.5 | Enter `70000` and a date, save | History shows the new EUR entry with reason "Relocation". The change column is blank because % across currencies is meaningless. |
| 7.6 | Set hire date after the first salary event | Error on hire date |

---

## 8. Terminate and reactivate (admin)

**What:** leavers drop out of headcount and payroll, but their record and history stay.

| # | Steps | Expected |
|---|---|---|
| 8.1 | Profile → **Terminate**, last day = yesterday | Badge "Left {date}"; the button changes to **Reactivate** |
| 8.2 | Directory Active tab, search the name | Not found. Terminated tab: found. |
| 8.3 | Dashboard headcount | One fewer than before |
| 8.4 | **Reactivate** | Active again; history unchanged |
| 8.5 | Terminate with a **future** date | Badge "Leaving {date}"; still counts as active today |
| 8.6 | Termination date before hire date | "cannot be before hire date" |

---

## 9. CSV import of new hires (admin)

**What:** bulk onboarding from a spreadsheet. The file is checked first, then imported all
or nothing.

Prepare `bad.csv`:

```csv
employee_number,first_name,last_name,email,country_code,currency_code,department,job_title,level,hire_date,annual_salary
NH001,Ana,Silva,ana.silva.nh@acme.example,BR,BRL,Sales,Account Executive,L3,2026-09-01,120000
NH002,Ben,Ng,ben.ng.nh@acme.example,SG,SGD,Engineering,Software Engineer II,L3,2026-09-15,98000
NH003,Bad,Row,not-an-email,ZZ,EUR,Sales,Account Executive,L3,2026-13-01,72000
NH001,Dup,Number,dup.nh@acme.example,US,USD,Sales,Account Executive,L2,2026-09-01,60000
```

| # | Steps | Expected |
|---|---|---|
| 9.1 | Employees → **Import CSV** → **Download template** | A CSV with the header and one example row |
| 9.2 | Choose `bad.csv` → **2. Check file** | "N problems found. Nothing was imported." Table: row 4 has hire_date, email and country_code errors; row 5 has "employee_number duplicate of row 2". **3. Import** stays disabled. |
| 9.3 | Check the directory for `NH001` | Not there; nothing was written |
| 9.4 | Delete rows 4 and 5, choose the file again, **Check file** | "All 2 rows are valid. Nothing has been saved yet." |
| 9.5 | **3. Import 2 employees** | "2 employees imported" with a link; both profiles have a Hire entry recorded by Hana Admin |
| 9.6 | Import the same file again | Every row: "already exists" |
| 9.7 | Save a CSV from Excel as "CSV UTF-8" | Accepted; Excel's byte-order mark is handled |
| 9.8 | Upload a non-UTF-8 or binary file | "must be UTF-8 encoded CSV" |
| 9.9 | Remove a column from the header | One error listing the missing columns |
| 9.10 | **Big file:** export all (section 10), change every `AC` to `ZZ` and every `@acme.example` to `@new.example`, import | 10,000 rows validated in about 1 s and imported in a few seconds |

---

## 10. CSV export

**What:** take any filtered view back to a spreadsheet.

| # | Steps | Expected |
|---|---|---|
| 10.1 | Directory, filter Japan, **Export CSV** | Downloads `acme-employees-{date}.csv` with only Japanese employees, salaries in yen, status and salary effective date |
| 10.2 | Export with a search plus the Terminated tab | The file matches what is on screen, all pages included |
| 10.3 | Add an employee whose last name is `=1+1` (section 6), export, open in Excel | The cell shows `'=1+1` as text, not 2. This is formula-injection protection. |
| 10.4 | Log in as viewer and export | Allowed; export is read-only |

---

## 11. Payroll runs (admin)

**What:** a frozen monthly record of what everyone is owed. It records amounts; it does not
pay anyone.

| # | Steps | Expected |
|---|---|---|
| 11.1 | **Payroll** | Explanation of the rules; the period picker defaults to the current month |
| 11.2 | **Run {current month}** | Detail page: about 9,300 employees paid, a USD total, 9 countries, totals by country in local currency and USD |
| 11.3 | Lines: filter **Japan**, page through | Annual, monthly (annual ÷ 12), rate, monthly USD per person |
| 11.4 | Spot-check one line | Monthly = annual ÷ 12, rounded to the cent (whole yen for JPY); monthly USD = monthly × rate |
| 11.5 | Back to Payroll | The run is listed; the month shows "(done)" and its Run button is disabled |
| 11.6 | **Frozen check:** note one employee's monthly amount, give them a raise effective at the start of the month, reopen the run | The run's amount is unchanged |
| 11.7 | Run **next** month (first option) | Allowed, to prepare ahead. The raise from 11.6 is included. |
| 11.8 | **Export CSV** on a run | `acme-payroll-YYYY-MM.csv` with one line per employee |
| 11.9 | Someone terminated on the 10th of the month | Not in that month's run (rule: employed on the last day) |

API-only check for "too far ahead", from `/docs`:
`POST /payroll-runs {"year": <this year + 1>, "month": 12}` returns 422 "can be at most
one month ahead of the current month".

---

## 12. Read-only HR viewer

**What:** the authorization boundary. Viewers can see and export everything but change
nothing.

| # | Steps | Expected |
|---|---|---|
| 12.1 | Log in as `viewer@acme.example` | **Read only** badge |
| 12.2 | Employees | No Add or Import buttons; Export is present |
| 12.3 | A profile | No Record salary change, Edit, or Terminate buttons |
| 12.4 | Open `/employees/new` or `/employees/import` directly | "Read-only access. Only HR admins can make changes." |
| 12.5 | Payroll | Runs visible; no "Run payroll" card |
| 12.6 | **API enforcement:** at `/docs`, Authorize with the viewer's token (from Session Storage `acme.token`), call `POST /employees` | 403. Hiding buttons is a convenience; the API is the real guard. |

---

## 13. API directly (optional, impresses reviewers)

Open `http://localhost:8000/docs`, the interactive OpenAPI page.

1. `POST /auth/login` with the admin credentials and copy `token`.
2. Click **Authorize**, paste the token.
3. Try `GET /analytics/breakdown?by=level`, `GET /analytics/matrix`, and
   `GET /employees?q=patel&sort=current_salary&order=desc`.
4. Send nonsense, e.g. `GET /employees?sort=password`. You get a 422, not a crash.

---

## 14. Automated tests

```bash
cd apps/api
pytest                                   # 220 tests, a few seconds
ruff check app tests scripts             # lint
alembic check                            # models and migrations agree

cd apps/web
npm test                                 # 28 tests
npm run lint
npm run build                            # production build must pass

# End-to-end: 9 journeys in a real browser against running servers.
# Use a freshly seeded database; it creates data.
# Run from any empty folder outside the repo:
npm init -y && npm i playwright && npx playwright install chromium
node <repo>/apps/web/e2e/walkthrough.mjs --web http://localhost:3000
#   ...add  --screenshots shots  --video video --slow  to regenerate media
```

| Suite | What it proves |
|---|---|
| `tests/domain` | Money, rounding, salary-history rules, statistics, CSV parsing, payroll rules. Pure functions with hand-computed answers. |
| `tests/api` | Every endpoint: status codes, validation messages, roles, tenant isolation, optimistic locking |
| `tests/test_seed.py` | The generator is deterministic and every generated row passes the same validation as user input |
| Web tests | Money formatting, URL state, API error mapping, stale-response handling, sort headers, import error table |
| Walkthrough | The screens work together against the real API with no console or server errors |

---

## 15. Ten-minute smoke test (run after every deploy)

- [ ] `https://<api>/health` returns `{"status":"ok"}`
- [ ] Log in as admin; dashboard shows 9,321
- [ ] Filter the dashboard by a country; numbers change
- [ ] Directory: search `sharma`, sort by salary, open a profile
- [ ] Record a salary change with a valid amount
- [ ] Import the 2-row CSV from section 9 (after removing the bad rows)
- [ ] Export the directory
- [ ] Run payroll for the current month
- [ ] Log in as viewer; no edit buttons
- [ ] No red errors in the browser console
- [ ] Reset the demo data afterwards (see deployment.md) so reviewers start clean
