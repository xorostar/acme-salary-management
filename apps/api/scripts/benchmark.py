"""Time the main read paths against a running, seeded API.

Usage:
    uvicorn app.main:app --port 8000          # in another terminal
    python scripts/benchmark.py [base_url]    # default http://127.0.0.1:8000

Logs in as the demo admin and prints the median wall-clock time of 15 runs per
request, measured over real HTTP (routing, auth, validation, serialization).
"""

import os
import statistics
import sys
import time

import httpx

RUNS = 15

REQUESTS = [
    ("Directory, page 1", "/employees?page=1&page_size=25"),
    ("Directory, page 200", "/employees?page=200&page_size=25"),
    ("Directory, sort by salary desc", "/employees?sort=current_salary&order=desc"),
    ("Directory, search 'patel'", "/employees?q=patel"),
    ("Directory, filter IN + L4", "/employees?country_code=IN&level=L4"),
    ("Employee detail", "/employees/4242"),
    ("Analytics overview (all active)", "/analytics/overview"),
    ("Breakdown by country", "/analytics/breakdown?by=country_code"),
    ("Level x country matrix", "/analytics/matrix"),
    ("CSV export, all active", "/employees/export.csv"),
]


def main() -> None:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    password = os.environ.get("ACME_DEMO_PASSWORD", "acme-demo-2026")
    with httpx.Client(base_url=base, timeout=30) as client:
        login = client.post("/auth/login", json={"email": "admin@acme.example",
                                                 "password": password})  # fmt: skip
        login.raise_for_status()
        client.headers["Authorization"] = f"Bearer {login.json()['token']}"

        print("| Request | Median (ms) |\n|---|---|")
        for label, url in REQUESTS:
            client.get(url)  # warm up
            samples = []
            for _ in range(RUNS):
                t = time.perf_counter()
                r = client.get(url)
                samples.append((time.perf_counter() - t) * 1000)
                r.raise_for_status()
            print(f"| {label} | {statistics.median(samples):.0f} |")


if __name__ == "__main__":
    main()
