"use client";

import { NativeSelect } from "@/components/ui/native-select";

/** Country / department / level filters shared by the directory and dashboard. */
export function OrgFilters({ reference, value, onChange }) {
  const set = (key) => (e) => onChange({ [key]: e.target.value });
  return (
    <>
      <NativeSelect
        aria-label="Country"
        value={value.country_code}
        onChange={set("country_code")}
        className="w-40"
      >
        <option value="">All countries</option>
        {reference?.countries.map((c) => (
          <option key={c.code} value={c.code}>
            {c.name}
          </option>
        ))}
      </NativeSelect>
      <NativeSelect
        aria-label="Department"
        value={value.department}
        onChange={set("department")}
        className="w-44"
      >
        <option value="">All departments</option>
        {reference?.departments.map((d) => (
          <option key={d} value={d}>
            {d}
          </option>
        ))}
      </NativeSelect>
      <NativeSelect
        aria-label="Level"
        value={value.level}
        onChange={set("level")}
        className="w-32"
      >
        <option value="">All levels</option>
        {reference?.levels.map((l) => (
          <option key={l} value={l}>
            {l}
          </option>
        ))}
      </NativeSelect>
    </>
  );
}
