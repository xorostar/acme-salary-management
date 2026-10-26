"use client";

import { CheckCircle2Icon, DownloadIcon, FileUpIcon } from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/common";
import { AdminOnly } from "@/components/employees/admin-only";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";

/** Validate first, then import: the HR manager sees every problem before
 * anything is written, and a file is imported entirely or not at all. */
export function ImportEmployees() {
  const input = useRef(null);
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null); // body of the last validate/import call
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(null);

  async function run(dryRun) {
    setBusy(true);
    try {
      const body = await api.importEmployees(file, dryRun);
      setResult(body);
      if (!dryRun) {
        setDone(body.imported);
        toast.success(`${body.imported} employees imported`);
      }
    } catch (err) {
      if (err.status === 422 && err.body?.errors && "total_rows" in err.body) {
        setResult(err.body);
      } else {
        setResult({ errors: err.fieldErrors.map((e) => ({ row: "—", ...e })), error_count: 1 });
        if (!err.fieldErrors.length) toast.error(err.message);
      }
    } finally {
      setBusy(false);
    }
  }

  function choose(e) {
    setFile(e.target.files?.[0] ?? null);
    setResult(null);
    setDone(null);
  }

  const valid = result && result.errors.length === 0 && result.dry_run;

  return (
    <AdminOnly>
      <PageHeader
        title="Import new hires"
        description="Upload a CSV of new employees. Every row is checked first; nothing is saved unless the whole file is valid."
        actions={
          <Button variant="outline" onClick={() => api.importTemplate()}>
            <DownloadIcon /> Download template
          </Button>
        }
      />

      {done !== null ? (
        <Alert>
          <CheckCircle2Icon />
          <AlertTitle>{done.toLocaleString("en-US")} employees imported</AlertTitle>
          <AlertDescription>
            <p>Each has a starting salary effective on their hire date.</p>
            <Link href="/employees?sort=hire_date&order=desc" className="mt-1 underline">
              View newest hires
            </Link>
          </AlertDescription>
        </Alert>
      ) : (
        <Card className="max-w-3xl">
          <CardHeader>
            <CardTitle>1. Choose a file</CardTitle>
            <CardDescription>
              UTF-8 CSV with the template&apos;s columns, up to 4 MB. Amounts in major units (85000.00).
              Dates as YYYY-MM-DD.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <input
                ref={input}
                type="file"
                accept=".csv,text/csv"
                onChange={choose}
                className="sr-only"
                id="csv-file"
              />
              <label htmlFor="csv-file" className={buttonVariants({ variant: "outline" })}>
                <FileUpIcon /> {file ? "Choose another file" : "Choose CSV file"}
              </label>
              {file && (
                <span className="text-sm text-muted-foreground">
                  {file.name} · {(file.size / 1024).toFixed(0)} KB
                </span>
              )}
            </div>
            <div className="flex gap-2">
              <Button onClick={() => run(true)} disabled={!file || busy}>
                {busy && !valid ? "Checking…" : "2. Check file"}
              </Button>
              <Button onClick={() => run(false)} disabled={!valid || busy} variant="default">
                {busy && valid
                  ? "Importing…"
                  : `3. Import${valid ? ` ${result.imported.toLocaleString("en-US")} employees` : ""}`}
              </Button>
            </div>

            {valid && (
              <Alert>
                <CheckCircle2Icon />
                <AlertTitle>
                  All {result.total_rows.toLocaleString("en-US")} rows are valid
                </AlertTitle>
                <AlertDescription>Nothing has been saved yet. Import when ready.</AlertDescription>
              </Alert>
            )}
            {result && result.errors.length > 0 && <ImportErrors result={result} />}
          </CardContent>
        </Card>
      )}
    </AdminOnly>
  );
}

export function ImportErrors({ result }) {
  const shown = result.errors.length;
  const total = result.error_count ?? shown;
  return (
    <div>
      <Alert variant="destructive" className="mb-3">
        <AlertTitle>
          {total.toLocaleString("en-US")} problem{total === 1 ? "" : "s"} found. Nothing was
          imported.
        </AlertTitle>
        <AlertDescription>
          Fix these rows in your spreadsheet and check the file again.
          {total > shown && ` Showing the first ${shown}.`}
        </AlertDescription>
      </Alert>
      <div className="max-h-96 overflow-y-auto rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-16">Row</TableHead>
              <TableHead className="w-40">Column</TableHead>
              <TableHead>Problem</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {result.errors.map((e, i) => (
              <TableRow key={i}>
                <TableCell className="tabular-nums">{e.row}</TableCell>
                <TableCell className="font-mono text-xs">{e.field}</TableCell>
                <TableCell>{e.message}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
