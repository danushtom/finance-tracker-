"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(10, "At least 10 characters"),
  displayName: z.string().min(1, "Required"),
  inviteCode: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export default function RegisterPage() {
  const { register: registerUser } = useAuth();
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      await registerUser(values.email, values.password, values.displayName, values.inviteCode);
      router.push("/dashboard");
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Registration failed");
    }
  }

  return (
    <main className="mx-auto max-w-sm p-8">
      <h1 className="mb-6 text-xl font-semibold">Register</h1>
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-3">
        <label className="flex flex-col gap-1">
          <span>Display name</span>
          <input className="border p-2" {...register("displayName")} />
          {errors.displayName && <span className="text-sm text-red-600">{errors.displayName.message}</span>}
        </label>
        <label className="flex flex-col gap-1">
          <span>Email</span>
          <input type="email" className="border p-2" {...register("email")} />
          {errors.email && <span className="text-sm text-red-600">{errors.email.message}</span>}
        </label>
        <label className="flex flex-col gap-1">
          <span>Password</span>
          <input type="password" className="border p-2" {...register("password")} />
          {errors.password && <span className="text-sm text-red-600">{errors.password.message}</span>}
        </label>
        <label className="flex flex-col gap-1">
          <span>Invite code (if required by this instance)</span>
          <input className="border p-2" {...register("inviteCode")} />
        </label>
        {serverError && <p className="text-sm text-red-600">{serverError}</p>}
        <button type="submit" disabled={isSubmitting} className="border p-2">
          {isSubmitting ? "Creating account…" : "Create account"}
        </button>
      </form>
      <p className="mt-4 text-sm">
        Already have an account? <Link href="/login" className="underline">Log in</Link>
      </p>
    </main>
  );
}
