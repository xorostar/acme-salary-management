"use client";

import { EmptyState } from "@/components/common";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatCompact, formatMoney } from "@/lib/money";

const LABELS = { country_code: "Country", department: "Department", level: "Level" };

export function BreakdownTable({ data }) {
  if (!data.groups.length) return <EmptyState title="Nobody matches these filters" />;
  const maxMedian = Math.max(...data.groups.map((g) => g.usd.p50));
  const showLocal = data.dimension === "country_code";

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{LABELS[data.dimension]}</TableHead>
          <TableHead className="text-right">People</TableHead>
          <TableHead className="w-[30%]">Median (USD)</TableHead>
          <TableHead className="text-right">Middle 50%</TableHead>
          {showLocal && <TableHead className="text-right">Median (local)</TableHead>}
          <TableHead className="text-right">Payroll</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.groups.map((g) => (
          <TableRow key={g.key}>
            <TableCell className="font-medium">{g.label}</TableCell>
            <TableCell className="text-right tabular-nums">
              {g.usd.count.toLocaleString("en-US")}
            </TableCell>
            <TableCell>
              <div className="flex items-center gap-2">
                <div className="h-2 flex-1 rounded-full bg-muted">
                  <div
                    className="h-2 rounded-full bg-chart-1"
                    style={{ width: `${(g.usd.p50 / maxMedian) * 100}%` }}
                  />
                </div>
                <span className="w-20 text-right tabular-nums">{formatMoney(g.usd.p50, "USD")}</span>
              </div>
            </TableCell>
            <TableCell className="text-right text-muted-foreground tabular-nums">
              {formatCompact(g.usd.p25)} – {formatCompact(g.usd.p75)}
            </TableCell>
            {showLocal && (
              <TableCell className="text-right tabular-nums">
                {g.local ? formatMoney(g.local.p50, g.local_currency) : "—"}
              </TableCell>
            )}
            <TableCell className="text-right tabular-nums">{formatCompact(g.usd.total)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
