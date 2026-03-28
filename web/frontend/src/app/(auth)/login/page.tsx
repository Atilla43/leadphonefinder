"use client";

import { Suspense } from "react";
import { LoginForm } from "@/components/auth/login-form";

function LoginContent() {
  return <LoginForm />;
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginContent />
    </Suspense>
  );
}
