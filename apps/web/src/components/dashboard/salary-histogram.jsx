"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EmptyState } from "@/components/common";
import { formatCompact, formatMoney } from "@/lib/money";

export function SalaryHistogram({ buckets }) {
  if (!buckets?.length) return <EmptyState title="Nobody matches these filters" />;
  const data = buckets.map((b) => ({ ...b, label: formatCompact(b.start) }));
  return (
    <div className="h-64" role="img" aria-label="Histogram of annual salaries in USD">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -16 }}>
          <CartesianGrid vertical={false} stroke="var(--border)" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
            interval="preserveStartEnd"
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            cursor={{ fill: "var(--muted)" }}
            contentStyle={{
              background: "var(--popover)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 12,
            }}
            labelFormatter={(_, payload) => {
              const b = payload?.[0]?.payload;
              return b ? `${formatMoney(b.start, "USD")} – ${formatMoney(b.end, "USD")}` : "";
            }}
            formatter={(value) => [value.toLocaleString("en-US"), "People"]}
          />
          <Bar dataKey="count" fill="var(--chart-1)" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
