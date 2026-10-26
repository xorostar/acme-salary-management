// End-to-end walkthrough of the HR manager's main journeys, against a running
// API and web app. It doubles as:
//   - a smoke test: every step asserts what should be on screen, and the run
//     fails on any browser console error or failed API call;
//   - the demo recording: with --video it records a captioned walkthrough;
//   - the README screenshots (--screenshots <dir>).
//
// Playwright is not a project dependency (it downloads browsers). Run from any
// folder where it is installed:
//   npm i playwright && npx playwright install chromium
//   node <repo>/apps/web/e2e/walkthrough.mjs --web http://localhost:3000 \
//        --video out/ --screenshots out/ [--slow]

import { createRequire } from "node:module";
import { writeFileSync } from "node:fs";
import { join } from "node:path";

const require = createRequire(join(process.cwd(), "noop.js"));
const { chromium } = require("playwright");

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, a, i, all) => {
    if (a.startsWith("--")) acc.push([a.slice(2), all[i + 1]?.startsWith("--") ? true : (all[i + 1] ?? true)]);
    return acc;
  }, []),
);
const WEB = args.web || "http://localhost:3000";
const PASSWORD = process.env.ACME_DEMO_PASSWORD || "acme-demo-2026";
const SLOW = Boolean(args.slow);
const pause = (ms) => new Promise((r) => setTimeout(r, SLOW ? ms : Math.min(ms, 150)));
const stamp = Date.now().toString().slice(-5);

const problems = [];
const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  acceptDownloads: true,
  ...(args.video ? { recordVideo: { dir: args.video, size: { width: 1440, height: 900 } } } : {}),
});
const page = await context.newPage();
page.on("console", (m) => {
  // The browser logs every non-2xx as "Failed to load resource"; responses are
  // checked precisely below, so only other console errors count here.
  if (m.type() === "error" && !m.text().startsWith("Failed to load resource")) {
    problems.push(`console: ${m.text()}`);
  }
});
page.on("response", (r) => {
  // 422 is the expected answer to the invalid inputs this script submits on
  // purpose. Any other 4xx or a 5xx is a bug.
  if (r.status() >= 400 && r.status() !== 422) problems.push(`HTTP ${r.status()} ${r.url()}`);
});

async function caption(text, ms = 2200) {
  await page.evaluate((t) => {
    let el = document.getElementById("__caption");
    if (!el) {
      el = document.createElement("div");
      el.id = "__caption";
      el.style.cssText =
        "position:fixed;left:50%;bottom:28px;transform:translateX(-50%);z-index:99999;" +
        "background:rgba(15,23,42,.92);color:#fff;padding:12px 20px;border-radius:12px;" +
        "font:500 18px/1.4 system-ui,sans-serif;max-width:80%;text-align:center;" +
        "box-shadow:0 8px 24px rgba(0,0,0,.25);pointer-events:none";
      document.body.appendChild(el);
    }
    el.textContent = t;
  }, text);
  await pause(ms);
}

async function shot(name) {
  if (!args.screenshots) return;
  await page.evaluate(() => document.getElementById("__caption")?.remove());
  await page.screenshot({ path: join(args.screenshots, `${name}.png`) });
}

async function step(name, fn) {
  const started = Date.now();
  try {
    await fn();
    console.log(`ok   ${name} (${Date.now() - started}ms)`);
  } catch (e) {
    console.log(`FAIL ${name}: ${e.message.split("\n")[0]}`);
    await page.screenshot({ path: `failure-${name.replace(/\W+/g, "-")}.png` });
    throw e;
  }
}

async function login(email) {
  await page.goto(`${WEB}/login`);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "How ACME pays people" }).waitFor();
}

try {
  await step("login as HR admin", async () => {
    await page.goto(`${WEB}/login`);
    await caption("ACME Salaries: salary management for an HR team with 10,000 employees in 9 countries.", 3500);
    await login("admin@acme.example");
    await page.getByText("Active headcount").waitFor();
  });

  await step("dashboard answers pay questions", async () => {
    await page.getByRole("cell", { name: "United States" }).waitFor();
    await caption("The dashboard answers “how do we pay people?” in one currency, from live data.", 3200);
    await shot("01-dashboard");
    await caption("Breakdown by department, with medians and the middle 50% of pay.");
    await page.getByRole("button", { name: "Department", exact: true }).click();
    await page.getByRole("cell", { name: "Engineering" }).waitFor();
    await caption("Filter to India: figures are converted with dated planning rates, so reports are reproducible.", 3200);
    await page.getByRole("combobox", { name: "Country" }).first().selectOption("IN");
    await page.waitForURL(/country_code=IN/);
    await page.getByText("Median salary by level and country").scrollIntoViewIfNeeded();
    await caption("Same level, different countries: the heatmap shows where we pay more for the same job.", 3200);
    await shot("02-dashboard-india");
  });

  let employeeName;
  await step("directory: search, filter, sort", async () => {
    await page.getByRole("link", { name: "Employees" }).click();
    await page.getByRole("heading", { name: "Employees" }).waitFor();
    await caption("The directory: 10,000 people, paginated and sorted on the server.");
    await page.getByLabel("Search by name, email or employee number").fill("sharma");
    await page.waitForURL(/q=sharma/);
    await page.getByRole("combobox", { name: "Level" }).selectOption("L4");
    await page.waitForURL(/level=L4/);
    await caption("Search, filter and sort by current salary. The URL keeps the view, so it can be shared.");
    await page.getByRole("button", { name: /Annual salary/ }).click();
    await page.waitForURL(/sort=current_salary/);
    await page.locator("tbody tr").first().waitFor();
    await shot("03-directory");
    const link = page.locator("tbody tr").first().getByRole("link");
    employeeName = await link.textContent();
    await link.click();
  });

  await step("profile: history and a salary change", async () => {
    await page.getByText("Salary history").waitFor();
    await caption("Salary history is append-only: every change keeps its date, reason and who recorded it.", 3200);
    await shot("04-profile");
    await page.getByRole("button", { name: "Record salary change" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel(/New annual salary/).fill("9999999999999999");
    await dialog.getByRole("button", { name: "Record change" }).click();
    await dialog.getByText("exceeds the maximum supported amount").waitFor();
    await caption("Validation comes from the API and appears next to the field.");
    const current = await page.locator("[data-slot=card-title]").first().textContent();
    const amount = Number(current.replace(/[^\d.]/g, "")) || 1000000;
    await dialog.getByLabel(/New annual salary/).fill(String(Math.round(amount * 1.08)));
    await dialog.getByLabel("Reason").selectOption("Promotion");
    await caption("An 8% promotion, effective today.");
    await dialog.getByRole("button", { name: "Record change" }).click();
    await page.getByText("Salary change recorded").waitFor();
    await page.getByRole("cell", { name: "Promotion" }).first().waitFor();
    await page.getByRole("cell", { name: "Hana Admin" }).first().waitFor();
    await caption(`Recorded for ${employeeName?.trim()}. The previous salary is still in the history.`, 2800);
  });

  await step("add a new hire", async () => {
    await page.goto(`${WEB}/employees/new`);
    await caption("Adding a new hire: their starting salary becomes the first history entry.");
    await page.getByLabel("First name").fill("Grace");
    await page.getByLabel("Last name").fill("Hopper");
    await page.getByLabel("Work email").fill(`grace.hopper.${stamp}@acme.example`);
    await page.getByLabel("Employee number").fill(`GH${stamp}`);
    await page.getByLabel("Job title").fill("Staff Software Engineer");
    await page.getByLabel("Department").selectOption("Engineering");
    await page.getByLabel("Level").selectOption("L5");
    await page.getByLabel("Hire date").fill("2026-10-01");
    await page.getByLabel("Country").selectOption("GB");
    await page.getByLabel(/Starting annual salary/).fill("98000");
    await caption("Choosing the United Kingdom sets the pay currency to GBP.");
    await page.getByRole("button", { name: "Add employee" }).click();
    await page.getByRole("heading", { name: "Grace Hopper" }).waitFor();
    await page.getByText("£98,000.00").first().waitFor();
  });

  await step("CSV import: errors first, then all or nothing", async () => {
    await page.goto(`${WEB}/employees/import`);
    const header =
      "employee_number,first_name,last_name,email,country_code,currency_code,department,job_title,level,hire_date,annual_salary";
    const good = (n) =>
      `IMP${stamp}${n},New,Hire${n},new.hire${n}.${stamp}@acme.example,DE,EUR,Sales,Account Executive,L3,2026-09-01,72000`;
    const bad = `IMP${stamp}9,Bad,Row,not-an-email,ZZ,EUR,Sales,Account Executive,L3,2026-13-01,72000`;
    const badFile = { name: "new-hires.csv", mimeType: "text/csv", buffer: Buffer.from([header, good(1), good(2), bad].join("\n")) };
    const goodFile = { name: "new-hires-fixed.csv", mimeType: "text/csv", buffer: Buffer.from([header, good(1), good(2), good(3)].join("\n")) };

    await caption("Bulk import of new hires. The file is checked before anything is saved.");
    await page.locator("#csv-file").setInputFiles(badFile);
    await page.getByRole("button", { name: "2. Check file" }).click();
    await page.getByText(/problems? found\. Nothing was imported/).waitFor();
    await caption("Every problem, with its spreadsheet row. One bad row means nothing is imported.", 3200);
    await shot("05-import-errors");
    await page.locator("#csv-file").setInputFiles(goodFile);
    await page.getByRole("button", { name: "2. Check file" }).click();
    await page.getByText("All 3 rows are valid").waitFor();
    await page.getByRole("button", { name: "3. Import 3 employees" }).click();
    await page.getByText("3 employees imported").first().waitFor();
    await caption("Fixed file: all three imported in one transaction.");
  });

  await step("export the filtered directory", async () => {
    await page.goto(`${WEB}/employees?country_code=JP`);
    await page.locator("tbody tr").first().waitFor();
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "Export CSV" }).click(),
    ]);
    const path = await download.path();
    const text = (await import("node:fs")).readFileSync(path, "utf8");
    if (!text.startsWith("employee_number,") || !text.includes(",JP,JPY,")) {
      throw new Error("export did not contain Japanese employees");
    }
    await caption("Export any filtered view to CSV, with current salaries.");
  });

  await step("payroll run", async () => {
    await page.getByRole("link", { name: "Payroll" }).click();
    await page.getByRole("heading", { name: "Payroll runs" }).waitFor();
    await caption("A payroll run freezes what everyone is owed for a month. It records; it does not pay.", 3200);
    const runButton = page.getByRole("button", { name: /^Run / });
    if (await runButton.isDisabled()) {
      await page.getByRole("combobox", { name: "Payroll period" }).selectOption({ index: 1 });
    }
    await runButton.click();
    await page.getByRole("heading", { name: /^Payroll · / }).waitFor();
    await page.getByRole("cell", { name: "United States" }).waitFor();
    await caption("Totals per country in local currency and USD, and every line, exportable for finance.", 3200);
    await shot("06-payroll");
  });

  await step("read-only user cannot change anything", async () => {
    await page.getByRole("button", { name: "Log out" }).click();
    await page.getByLabel("Email").waitFor();
    await login("viewer@acme.example");
    await page.getByText("Read only", { exact: true }).waitFor();
    await page.getByRole("link", { name: "Employees" }).click();
    await page.locator("tbody tr").first().waitFor();
    if (await page.getByRole("link", { name: "Add employee" }).count()) {
      throw new Error("viewer can see Add employee");
    }
    await page.locator("tbody tr").first().getByRole("link").click();
    await page.getByText("Salary history").waitFor();
    if (await page.getByRole("button", { name: "Record salary change" }).count()) {
      throw new Error("viewer can see salary change");
    }
    await caption("A read-only HR viewer sees everything but can change nothing. The API enforces the same rule.", 3500);
  });
} finally {
  await context.close(); // flushes the video file
  await browser.close();
}

if (problems.length) {
  writeFileSync("walkthrough-problems.txt", problems.join("\n"));
  console.log(`\n${problems.length} browser problem(s):\n${problems.join("\n")}`);
  process.exit(1);
}
console.log("\nWalkthrough passed with no console errors or server errors.");
