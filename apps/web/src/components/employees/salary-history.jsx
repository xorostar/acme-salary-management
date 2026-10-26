"use client";

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { formatDate } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatCompact, formatMoney, formatPercent, percentChange } from "@/lib/money";

/** Oldest-first list with the change from the previous entry in the same currency. */
export function withChanges(history) {
  const ascending = [...history].sort((a, b) => a.effective_date.localeCompare(b.effective_date));
  return ascending.map((h, i) => {
    const prev = ascending[i - 1];
    const comparable = prev && prev.currency_code === h.currency_code;
    return {
      ...h,
      change: comparable ? percentChange(prev.annual_amount_minor, h.annual_amount_minor) : null,
    };
  });
}

export function SalaryHistory({ employee, today }) {
  const rows = withChanges(employee.salary_history);
  const sameCurrency = rows.filter((r) => r.currency_code === employee.currency_code);

  return (
    <>
      {sameCurrency.length > 1 && (
        <div className="mb-4 h-40" role="img" aria-label="Salary over time">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sameCurrency} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <XAxis
                dataKey="effective_date"
                tickFormatter={(d) => d.slice(0, 4)}
                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                width={56}
                domain={["auto", "auto"]}
                tickFormatter={(v) => formatCompact(v, employee.currency_code)}
                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--popover)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                labelFormatter={(d) => formatDate(d)}
                formatter={(v) => [formatMoney(v, employee.currency_code), "Salary"]}
              />
              <Line
                type="stepAfter"
                dataKey="annual_amount_minor"
                stroke="var(--chart-1)"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Effective</TableHead>
            <TableHead className="text-right">Annual salary</TableHead>
            <TableHead className="text-right">Change</TableHead>
            <TableHead>Reason</TableHead>
            <TableHead>Recorded by</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {[...rows].reverse().map((h) => (
            <TableRow key={h.id}>
              <TableCell className="whitespace-nowrap">
                {formatDate(h.effective_date)}
                {h.effective_date > today && (
                  <Badge variant="outline" className="ml-2">
                    Scheduled
                  </Badge>
                )}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {formatMoney(h.annual_amount_minor, h.currency_code, { cents: true })}
              </TableCell>
              <TableCell
                className={`text-right tabular-nums ${h.change < 0 ? "text-destructive" : "text-muted-foreground"}`}
              >
                {formatPercent(h.change)}
              </TableCell>
              <TableCell>{h.reason}</TableCell>
              <TableCell className="text-muted-foreground">{h.created_by ?? "Data import"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </>
  );
}
