"use client";

import { EmptyState } from "@/components/common";
import { formatCompact, formatMoney } from "@/lib/money";

/** Level x country grid of median USD salary. Colour intensity scales with
 * the median so "where do we pay more for the same level" jumps out. */
export function MedianHeatmap({ data, reference }) {
  if (!data.cells.length) return <EmptyState title="Nobody matches these filters" />;
  const cells = new Map(data.cells.map((c) => [`${c.row}|${c.col}`, c]));
  const rows = reference.levels.filter((l) => data.cells.some((c) => c.row === l));
  const cols = reference.countries.filter((c) => data.cells.some((x) => x.col === c.code));
  const max = Math.max(...data.cells.map((c) => c.median_usd));

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-separate border-spacing-1 text-xs">
        <thead>
          <tr>
            <th className="w-12 text-left font-medium text-muted-foreground">Level</th>
            {cols.map((c) => (
              <th key={c.code} className="font-medium text-muted-foreground" title={c.name}>
                {c.code}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((level) => (
            <tr key={level}>
              <th className="text-left font-medium">{level}</th>
              {cols.map((c) => {
                const cell = cells.get(`${level}|${c.code}`);
                if (!cell) return <td key={c.code} className="rounded bg-muted/40" />;
                const strength = Math.round(15 + (cell.median_usd / max) * 85);
                return (
                  <td
                    key={c.code}
                    title={`${level} in ${c.name}: median ${formatMoney(cell.median_usd, "USD")}, ${cell.count} people`}
                    className="rounded px-1 py-1.5 text-center tabular-nums"
                    style={{
                      background: `color-mix(in oklch, var(--chart-1) ${strength}%, transparent)`,
                      color: strength > 60 ? "white" : undefined,
                    }}
                  >
                    {formatCompact(cell.median_usd)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
