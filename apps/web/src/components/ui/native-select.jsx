import { cn } from "cn";
import { ChevronDownIcon } from "lucide-react";

/**
 * A styled native <select>. Used for filters and forms instead of a custom
 * listbox: keyboard, screen reader and mobile behavior come for free, and
 * it is trivially testable.
 */
export function NativeSelect({ className, children, ...props }) {
  return (
    <div className={cn("relative", className)}>
      <select
        data-slot="native-select"
        className="h-8 w-full appearance-none rounded-lg border border-input bg-transparent py-1 pr-8 pl-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-50 aria-invalid:border-destructive dark:bg-input/30"
        {...props}
      >
        {children}
      </select>
      <ChevronDownIcon className="pointer-events-none absolute top-1/2 right-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
    </div>
  );
}
