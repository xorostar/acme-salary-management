"use client";

import { cn } from "cn";
import { BanknoteIcon, LayoutDashboardIcon, LogOutIcon, UsersIcon } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Suspense, useEffect } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/auth";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboardIcon, exact: true },
  { href: "/employees", label: "Employees", icon: UsersIcon },
  { href: "/payroll", label: "Payroll", icon: BanknoteIcon },
];

export function AppShell({ children }) {
  const { user, ready, isAdmin, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (ready && !user) router.replace("/login");
  }, [ready, user, router]);

  if (!ready || !user) {
    return (
      <div className="mx-auto w-full max-w-7xl space-y-4 p-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-30 border-b bg-background/95 backdrop-blur">
        <div className="mx-auto flex h-14 w-full max-w-7xl items-center gap-4 px-4 sm:px-6">
          <Link href="/" className="font-semibold tracking-tight">
            ACME <span className="text-muted-foreground">Salaries</span>
          </Link>
          <nav className="flex items-center gap-1" aria-label="Main">
            {/* The active-link highlight reads the URL, so it streams in
                inside Suspense instead of blocking prerender of every page. */}
            <Suspense fallback={<NavLinks pathname={null} />}>
              <ActiveNavLinks />
            </Suspense>
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <div className="hidden text-right text-xs leading-tight md:block">
              <div className="font-medium">{user.full_name}</div>
              <div className="text-muted-foreground">{user.email}</div>
            </div>
            <Badge variant={isAdmin ? "default" : "secondary"}>
              {isAdmin ? "HR admin" : "Read only"}
            </Badge>
            <Button variant="ghost" size="icon-sm" onClick={logout} aria-label="Log out">
              <LogOutIcon />
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6">{children}</main>
    </div>
  );
}

function ActiveNavLinks() {
  return <NavLinks pathname={usePathname()} />;
}

function NavLinks({ pathname }) {
  return NAV.map(({ href, label, icon: Icon, exact }) => {
    const active = pathname !== null && (exact ? pathname === href : pathname.startsWith(href));
    return (
      <Link
        key={href}
        href={href}
        aria-current={active ? "page" : undefined}
        className={cn(
          "flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm transition-colors",
          active ? "bg-muted font-medium text-foreground" : "text-muted-foreground hover:text-foreground",
        )}
      >
        <Icon className="size-4" />
        <span className="hidden sm:inline">{label}</span>
      </Link>
    );
  });
}
