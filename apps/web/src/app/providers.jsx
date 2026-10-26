"use client";

import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/lib/auth";

export function Providers({ children }) {
  return (
    <AuthProvider>
      <TooltipProvider>{children}</TooltipProvider>
      <Toaster richColors position="top-right" />
    </AuthProvider>
  );
}
