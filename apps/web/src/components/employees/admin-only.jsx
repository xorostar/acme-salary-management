"use client";

import { ShieldIcon } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useAuth } from "@/lib/auth";

/** Hides write screens from read-only users. The API enforces the same rule;
 * this only spares them a form they cannot submit. */
export function AdminOnly({ children }) {
  const { isAdmin } = useAuth();
  if (isAdmin) return children;
  return (
    <Alert>
      <ShieldIcon />
      <AlertTitle>Read-only access</AlertTitle>
      <AlertDescription>Only HR admins can make changes. Ask an admin for help.</AlertDescription>
    </Alert>
  );
}
