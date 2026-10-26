"""Deterministic generator for a realistic 10,000-employee organization.

Pure Python with no database access, so tests can check its output directly.
Every value comes from one `random.Random(seed)` and a fixed anchor date, so
the same seed always produces byte-identical data.

Salaries are modelled as: a USD band per level, scaled by department and by a
country pay factor, with +/-12% individual jitter, then converted to the local
currency with the seeded planning rate and rounded to a sensible step. History
walks backwards from the current salary through annual reviews and the
occasional promotion, so every employee has 1-6 dated events.
"""

import random
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from app.domain.money import exponent
from app.domain.reference import COUNTRIES, DEPARTMENTS, LEVELS

ANCHOR_DATE = date(2026, 10, 1)
DEFAULT_SEED = 20261023
DEFAULT_COUNT = 10_000

# Planning rates: 1 unit of currency = rate USD. Two dated sets so reports can
# show that conversions use the rate in force on the reference date.
RATES: dict[date, dict[str, str]] = {
    date(2025, 1, 1): {
        "USD": "1", "GBP": "1.25", "EUR": "1.04", "INR": "0.0117", "JPY": "0.0064",
        "CAD": "0.70", "AUD": "0.62", "SGD": "0.73", "BRL": "0.165",
    },
    date(2026, 1, 1): {
        "USD": "1", "GBP": "1.27", "EUR": "1.08", "INR": "0.0114", "JPY": "0.0067",
        "CAD": "0.73", "AUD": "0.66", "SGD": "0.75", "BRL": "0.18",
    },
}  # fmt: skip

COUNTRY_WEIGHTS: dict[str, int] = {
    "US": 30, "IN": 20, "GB": 12, "DE": 9, "CA": 7, "BR": 7, "JP": 6, "AU": 5, "SG": 4,
}  # fmt: skip

# Market pay relative to the US for the same role.
COUNTRY_PAY_FACTOR: dict[str, Decimal] = {
    "US": Decimal("1.00"), "GB": Decimal("0.78"), "DE": Decimal("0.80"), "IN": Decimal("0.32"),
    "JP": Decimal("0.68"), "CA": Decimal("0.80"), "AU": Decimal("0.84"), "SG": Decimal("0.86"),
    "BR": Decimal("0.38"),
}  # fmt: skip

DEPARTMENT_WEIGHTS: dict[str, int] = {
    "Engineering": 30, "Product": 6, "Design": 4, "Sales": 16, "Marketing": 7, "Finance": 5,
    "Human Resources": 4, "Operations": 10, "Customer Support": 15, "Legal": 3,
}  # fmt: skip

DEPARTMENT_PAY_FACTOR: dict[str, Decimal] = {
    "Engineering": Decimal("1.10"), "Product": Decimal("1.08"), "Design": Decimal("1.00"),
    "Sales": Decimal("1.00"), "Marketing": Decimal("0.95"), "Finance": Decimal("1.00"),
    "Human Resources": Decimal("0.90"), "Operations": Decimal("0.88"),
    "Customer Support": Decimal("0.75"), "Legal": Decimal("1.12"),
}  # fmt: skip

# Pyramid: many juniors, few executives.
LEVEL_WEIGHTS: dict[str, float] = {
    "L1": 12, "L2": 20, "L3": 22, "L4": 16, "L5": 9, "L6": 3,
    "M1": 8, "M2": 5, "M3": 2, "D1": 1.5, "D2": 0.8, "VP": 0.4,
}  # fmt: skip

LEVEL_BASE_USD: dict[str, int] = {
    "L1": 58_000, "L2": 72_000, "L3": 92_000, "L4": 118_000, "L5": 148_000, "L6": 185_000,
    "M1": 140_000, "M2": 172_000, "M3": 210_000, "D1": 250_000, "D2": 300_000, "VP": 380_000,
}  # fmt: skip

DEPARTMENT_ROLE: dict[str, str] = {
    "Engineering": "Software Engineer", "Product": "Product Manager", "Design": "Product Designer",
    "Sales": "Account Executive", "Marketing": "Marketing Specialist",
    "Finance": "Financial Analyst", "Human Resources": "HR Business Partner",
    "Operations": "Operations Analyst", "Customer Support": "Support Specialist",
    "Legal": "Counsel",
}  # fmt: skip

IC_PREFIX = {"L1": "Associate ", "L2": "", "L3": "", "L4": "Senior ", "L5": "Staff ",
             "L6": "Principal "}  # fmt: skip
IC_SUFFIX = {"L2": " I", "L3": " II"}

FIRST_NAMES: dict[str, tuple[str, ...]] = {
    "en": ("James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
           "David", "Elizabeth", "William", "Susan", "Richard", "Jessica", "Joseph", "Sarah",
           "Thomas", "Karen", "Chris", "Emily", "Daniel", "Olivia", "Matthew", "Sophie",
           "Andrew", "Grace", "Ryan", "Chloe", "Noah", "Ava", "Liam", "Mia", "Ethan", "Zoe"),
    "de": ("Lukas", "Anna", "Leon", "Lea", "Finn", "Hannah", "Jonas", "Lena", "Paul", "Marie",
           "Felix", "Laura", "Max", "Julia", "Tim", "Sophia", "Jan", "Katharina"),
    "in": ("Aarav", "Ananya", "Vivaan", "Diya", "Aditya", "Isha", "Arjun", "Priya", "Rohan",
           "Kavya", "Rahul", "Sneha", "Vikram", "Pooja", "Karan", "Neha", "Amit", "Divya",
           "Sanjay", "Meera", "Rajesh", "Lakshmi"),
    "jp": ("Haruto", "Yui", "Sota", "Hina", "Yuto", "Aoi", "Ren", "Sakura", "Takumi", "Yuna",
           "Kenji", "Mei", "Hiroshi", "Akari", "Daiki", "Rin"),
    "br": ("Miguel", "Alice", "Arthur", "Helena", "Davi", "Valentina", "Gabriel", "Laura",
           "Pedro", "Beatriz", "Lucas", "Mariana", "Matheus", "Julia", "Rafael", "Camila"),
    "sg": ("Wei", "Hui Min", "Jun", "Xin Yi", "Kai", "Mei Ling", "Ming", "Li Ting", "Ravi",
           "Siti", "Daniel", "Nur", "Ethan", "Rachel"),
}  # fmt: skip

LAST_NAMES: dict[str, tuple[str, ...]] = {
    "en": ("Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson",
           "Taylor", "Anderson", "Thomas", "Moore", "Martin", "Jackson", "Thompson", "White",
           "Harris", "Clark", "Lewis", "Walker", "Hall", "Young", "King", "Wright", "Scott",
           "Green", "Baker", "Adams", "Nelson", "Campbell", "Mitchell", "Roberts", "Evans",
           "Turner", "Parker", "Collins", "Edwards", "Murphy", "Cook", "Morgan"),
    "de": ("Muller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer", "Wagner", "Becker",
           "Schulz", "Hoffmann", "Koch", "Richter", "Klein", "Wolf", "Neumann", "Schwarz"),
    "in": ("Sharma", "Verma", "Patel", "Gupta", "Singh", "Kumar", "Reddy", "Iyer", "Nair",
           "Rao", "Mehta", "Joshi", "Desai", "Chopra", "Banerjee", "Kapoor", "Menon", "Pillai"),
    "jp": ("Sato", "Suzuki", "Takahashi", "Tanaka", "Watanabe", "Ito", "Yamamoto", "Nakamura",
           "Kobayashi", "Kato", "Yoshida", "Yamada", "Sasaki", "Matsumoto"),
    "br": ("Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Ferreira", "Alves", "Pereira",
           "Lima", "Gomes", "Costa", "Ribeiro", "Martins", "Carvalho"),
    "sg": ("Tan", "Lim", "Lee", "Ng", "Ong", "Wong", "Goh", "Chua", "Chan", "Koh", "Teo",
           "Ang", "Yeo", "Kumar", "Rahman"),
}  # fmt: skip

NAME_POOL = {"US": "en", "GB": "en", "CA": "en", "AU": "en", "DE": "de", "IN": "in",
             "JP": "jp", "BR": "br", "SG": "sg"}  # fmt: skip


@dataclass(frozen=True)
class SeedSalaryEvent:
    effective_date: date
    annual_amount_minor: int
    reason: str


@dataclass(frozen=True)
class SeedEmployee:
    employee_number: str
    first_name: str
    last_name: str
    email: str
    country_code: str
    currency_code: str
    department: str
    job_title: str
    level: str
    hire_date: date
    termination_date: date | None
    salary_events: tuple[SeedSalaryEvent, ...] = field(default_factory=tuple)


def job_title(department: str, level: str) -> str:
    role = DEPARTMENT_ROLE[department]
    if level in IC_PREFIX:
        return f"{IC_PREFIX[level]}{role}{IC_SUFFIX.get(level, '')}"
    if level == "M1":
        return f"{department} Manager"
    if level == "M2":
        return f"Senior {department} Manager"
    if level == "M3":
        return f"Head of {department}"
    if level in ("D1", "D2"):
        return f"{'Senior ' if level == 'D2' else ''}Director, {department}"
    return f"VP, {department}"


def _ascii(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def _rounding_step(currency_code: str) -> int:
    """Salaries are agreed in round numbers: 100 USD, 1,000 INR, 10,000 JPY."""
    return {"JPY": 10_000, "INR": 1_000}.get(currency_code, 100)


def _to_local_minor(usd: Decimal, currency_code: str, rate_to_usd: Decimal) -> int:
    step = _rounding_step(currency_code)
    local_major = usd / rate_to_usd
    rounded_major = int((local_major / step).to_integral_value()) * step
    return max(rounded_major, step) * (10 ** exponent(currency_code))


def _weighted(rng: random.Random, weights: dict[str, float]) -> str:
    keys = list(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys], k=1)[0]


def _history(
    rng: random.Random, current_minor: int, hire: date, anchor: date, step_minor: int
) -> tuple[SeedSalaryEvent, ...]:
    """Walk back from today's salary to the hire salary, one review per ~year."""
    events: list[SeedSalaryEvent] = []
    amount = current_minor
    # Review dates: every April 1st after the hire year, at most five of them.
    review_years = [y for y in range(hire.year + 1, anchor.year + 1) if date(y, 4, 1) <= anchor]
    review_years = review_years[-5:]
    for year in reversed(review_years):
        promoted = rng.random() < 0.15
        raise_pct = Decimal(str(rng.uniform(0.10, 0.16) if promoted else rng.uniform(0.02, 0.06)))
        events.append(
            SeedSalaryEvent(date(year, 4, 1), amount, "Promotion" if promoted else "Annual review")
        )
        previous = Decimal(amount) / (1 + raise_pct)
        amount = max(int(previous / step_minor) * step_minor, step_minor)
    events.append(SeedSalaryEvent(hire, amount, "Hire"))
    return tuple(sorted(events, key=lambda e: e.effective_date))


def generate_employees(
    count: int = DEFAULT_COUNT, *, seed: int = DEFAULT_SEED, anchor: date = ANCHOR_DATE
) -> list[SeedEmployee]:
    rng = random.Random(seed)
    rates = {c: Decimal(r) for c, r in RATES[max(d for d in RATES if d <= anchor)].items()}
    used_emails: set[str] = set()
    employees: list[SeedEmployee] = []

    for n in range(1, count + 1):
        country = _weighted(rng, COUNTRY_WEIGHTS)
        currency = COUNTRIES[country].currency_code
        department = _weighted(rng, DEPARTMENT_WEIGHTS)
        level = _weighted(rng, LEVEL_WEIGHTS)
        pool = NAME_POOL[country]
        first = rng.choice(FIRST_NAMES[pool])
        last = rng.choice(LAST_NAMES[pool])

        base = f"{_ascii(first).replace(' ', '')}.{_ascii(last)}"
        email = f"{base}@acme.example"
        if email in used_emails:
            email = f"{base}{n}@acme.example"
        used_emails.add(email)

        # Seniority correlates with tenure: senior people were hired earlier on average.
        max_years = 14 if level not in ("L1", "L2") else 4
        hire = anchor - timedelta(days=rng.randint(30, int(365 * max_years)))

        jitter = Decimal(str(rng.uniform(0.88, 1.12)))
        usd = (
            Decimal(LEVEL_BASE_USD[level])
            * DEPARTMENT_PAY_FACTOR[department]
            * COUNTRY_PAY_FACTOR[country]
            * jitter
        )
        current = _to_local_minor(usd, currency, rates[currency])
        step_minor = _rounding_step(currency) * (10 ** exponent(currency))
        history = _history(rng, current, hire, anchor, step_minor)

        # About 7% have left; some leavers left recently so the "terminated" view is lively.
        termination = None
        if rng.random() < 0.07:
            last_event = history[-1].effective_date
            earliest = max(hire, last_event) + timedelta(days=1)
            if earliest < anchor:
                termination = earliest + timedelta(days=rng.randint(0, (anchor - earliest).days))

        employees.append(
            SeedEmployee(
                employee_number=f"AC{n:05d}",
                first_name=first,
                last_name=last,
                email=email,
                country_code=country,
                currency_code=currency,
                department=department,
                job_title=job_title(department, level),
                level=level,
                hire_date=hire,
                termination_date=termination,
                salary_events=history,
            )
        )
    return employees


def _sanity() -> None:  # pragma: no cover - documentation aid
    assert set(LEVEL_WEIGHTS) == set(LEVELS)
    assert set(DEPARTMENT_WEIGHTS) == set(DEPARTMENTS)
    assert set(COUNTRY_WEIGHTS) == set(COUNTRIES)


_sanity()
