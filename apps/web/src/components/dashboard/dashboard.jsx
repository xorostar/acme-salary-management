"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

import {
  ErrorState,
  formatDate,
  LoadingRows,
  PageHeader,
  StatCard,
} from "@/components/common";
import { BreakdownTable } from "@/components/dashboard/breakdown-table";
import { MedianHeatmap } from "@/components/dashboard/median-heatmap";
import { SalaryHistogram } from "@/components/dashboard/salary-histogram";
import { OrgFilters } from "@/components/filters";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { api } from "@/lib/api";
import { formatCompact, formatMoney } from "@/lib/money";
import { parseAnalyticsFilters, toQueryString } from "@/lib/query";
import { useReference } from "@/lib/reference";
import { useApi } from "@/lib/use-api";

export function Dashboard() {
  const reference = useReference();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const filters = parseAnalyticsFilters(searchParams);
  const by = ["country_code", "department", "level"].includes(searchParams.get("by"))
    ? searchParams.get("by")
    : "country_code";
  const key = toQueryString(filters);

  const overview = useApi(() => api.overview(filters), key);
  const breakdown = useApi(() => api.breakdown({ ...filters, by }), key + by);
  const matrix = useApi(() => api.matrix(filters), key);

  const navigate = (changes) =>
    router.replace(
      `${pathname}${toQueryString({ ...filters, by, ...changes }, { by: "country_code" })}`,
      { scroll: false },
    );
  const filtered = Object.values(filters).some(Boolean);
  const o = overview.data;
  const usd = o?.annual_payroll_usd;

  return (
    <>
      <PageHeader
        title="How ACME pays people"
        description={
          o
            ? `Active employees on ${formatDate(o.as_of)}. Cross-country figures in USD at planning rates.`
            : "Active employees, converted to USD at planning rates."
        }
      />

      <div className="mb-6 flex flex-wrap items-center gap-2">
        <OrgFilters reference={reference} value={filters} onChange={navigate} />
        {filtered && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate({ country_code: "", department: "", level: "" })}
          >
            Clear filters
          </Button>
        )}
      </div>

      {overview.error ? (
        <ErrorState error={overview.error} onRetry={overview.reload} />
      ) : !o ? (
        <LoadingRows rows={4} />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard label="Active headcount" value={o.headcount.toLocaleString("en-US")} />
            <StatCard
              label="Annual payroll"
              value={formatCompact(usd?.total)}
              hint={usd ? `${formatMoney(usd.total, "USD")} per year` : "No data"}
            />
            <StatCard
              label="Median salary"
              value={formatMoney(usd?.p50, "USD")}
              hint={usd ? `Mean ${formatMoney(usd.mean, "USD")}` : undefined}
            />
            <StatCard
              label="Middle 80% earn"
              value={usd ? `${formatCompact(usd.p10)} – ${formatCompact(usd.p90)}` : "—"}
              hint="10th to 90th percentile"
            />
          </div>
          {o.missing_rates.length > 0 && (
            <p className="mt-2 text-sm text-destructive">
              Excluded: no planning rate for {o.missing_rates.join(", ")}.
            </p>
          )}
        </>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Salary distribution</CardTitle>
            <CardDescription>Annual salary in USD, number of people per band.</CardDescription>
          </CardHeader>
          <CardContent>
            {o ? <SalaryHistogram buckets={o.histogram} /> : <LoadingRows rows={5} />}
            {o && <RatesNote rates={o.rates} />}
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-2">
            <div>
              <CardTitle>Breakdown</CardTitle>
              <CardDescription>Medians and spread per group, largest group first.</CardDescription>
            </div>
            <div className="flex rounded-lg border p-0.5" role="group" aria-label="Group by">
              {[
                ["country_code", "Country"],
                ["department", "Department"],
                ["level", "Level"],
              ].map(([value, label]) => (
                <Button
                  key={value}
                  size="sm"
                  variant={by === value ? "secondary" : "ghost"}
                  aria-pressed={by === value}
                  onClick={() => navigate({ by: value })}
                >
                  {label}
                </Button>
              ))}
            </div>
          </CardHeader>
          <CardContent>
            {breakdown.error ? (
              <ErrorState error={breakdown.error} onRetry={breakdown.reload} />
            ) : breakdown.data ? (
              <BreakdownTable data={breakdown.data} />
            ) : (
              <LoadingRows rows={6} />
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Median salary by level and country</CardTitle>
          <CardDescription>
            USD. Darker cells pay more. Hover a cell for headcount. Empty cells have nobody.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {matrix.error ? (
            <ErrorState error={matrix.error} onRetry={matrix.reload} />
          ) : matrix.data && reference ? (
            <MedianHeatmap data={matrix.data} reference={reference} />
          ) : (
            <LoadingRows rows={6} />
          )}
        </CardContent>
      </Card>
    </>
  );
}

function RatesNote({ rates }) {
  if (!rates?.length) return null;
  const asOf = rates.reduce((d, r) => (r.effective_date > d ? r.effective_date : d), "");
  return (
    <Tooltip>
      <TooltipTrigger className="mt-3 text-xs text-muted-foreground underline decoration-dotted underline-offset-2">
        Planning rates effective {formatDate(asOf)}
      </TooltipTrigger>
      <TooltipContent>
        <div className="grid grid-cols-2 gap-x-4 text-xs tabular-nums">
          {rates
            .filter((r) => r.currency_code !== "USD")
            .map((r) => (
              <span key={r.currency_code}>
                1 {r.currency_code} = {r.rate_to_usd} USD
              </span>
            ))}
        </div>
      </TooltipContent>
    </Tooltip>
  );
}
