"use client";

import { ArrowDownIcon, ArrowUpDownIcon, ArrowUpIcon } from "lucide-react";
import Link from "next/link";

import { EmptyState, formatDate } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatMoney } from "@/lib/money";

const COLUMNS = [
  { key: "last_name", label: "Name" },
  { key: "employee_number", label: "Number" },
  { key: "department", label: "Department" },
  { key: "level", label: "Level" },
  { key: "country_code", label: "Country" },
  { key: "hire_date", label: "Hired" },
  { key: "current_salary", label: "Annual salary", align: "right" },
];

export function SortHeader({ column, sort, order, onSort }) {
  const active = sort === column.key;
  const Icon = !active ? ArrowUpDownIcon : order === "asc" ? ArrowUpIcon : ArrowDownIcon;
  return (
    <TableHead
      className={column.align === "right" ? "text-right" : undefined}
      aria-sort={active ? (order === "asc" ? "ascending" : "descending") : "none"}
    >
      <button
        type="button"
        onClick={() => onSort(column.key)}
        className="inline-flex items-center gap-1 font-medium hover:text-foreground"
      >
        {column.label}
        <Icon className={active ? "size-3.5" : "size-3.5 opacity-40"} />
      </button>
    </TableHead>
  );
}

export function EmployeeTable({ items, sort, order, onSort }) {
  if (!items.length) {
    return <EmptyState title="No employees match">Try clearing a filter or the search.</EmptyState>;
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {COLUMNS.map((c) => (
            <SortHeader key={c.key} column={c} sort={sort} order={order} onSort={onSort} />
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((e) => (
          <TableRow key={e.id}>
            <TableCell>
              <Link
                href={`/employees/${e.id}`}
                className="font-medium underline-offset-2 hover:underline"
              >
                {e.last_name}, {e.first_name}
              </Link>
              <div className="text-xs text-muted-foreground">{e.job_title}</div>
            </TableCell>
            <TableCell className="font-mono text-xs">{e.employee_number}</TableCell>
            <TableCell>{e.department}</TableCell>
            <TableCell>{e.level}</TableCell>
            <TableCell title={e.country_name}>{e.country_code}</TableCell>
            <TableCell className="whitespace-nowrap">
              {formatDate(e.hire_date)}
              {!e.is_active && (
                <Badge variant="destructive" className="ml-2">
                  Left
                </Badge>
              )}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {e.current_salary
                ? formatMoney(e.current_salary.annual_amount_minor, e.currency_code)
                : "—"}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
