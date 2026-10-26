import { Suspense } from "react";

import { LoginForm } from "@/components/login-form";

export const metadata = { title: "Log in" };

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 p-4">
      <Suspense>
        <LoginForm />
      </Suspense>
    </div>
  );
}
