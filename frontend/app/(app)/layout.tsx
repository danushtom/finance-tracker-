"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { useAuth } from "@/lib/auth-context";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/transactions", label: "Transactions" },
  { href: "/import", label: "Import" },
  { href: "/review", label: "Review" },
  { href: "/rules", label: "Rules" },
  { href: "/wishlist", label: "Wishlist" },
  { href: "/goals", label: "Goals" },
  { href: "/investments", label: "Investments" },
  { href: "/accounts", label: "Accounts" },
  { href: "/settings", label: "Settings" },
];

export default function AppLayout({ children }: { children: ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading) {
    return <p className="p-8">Loading…</p>;
  }
  if (!user) {
    return null;
  }

  return (
    <div className="flex min-h-screen">
      <nav className="flex w-48 flex-col gap-1 border-r p-4">
        <p className="mb-4 text-sm text-gray-500">{user.display_name || user.email}</p>
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`px-2 py-1 ${pathname?.startsWith(item.href) ? "font-semibold underline" : ""}`}
          >
            {item.label}
          </Link>
        ))}
        <button
          onClick={() => {
            void logout().then(() => router.push("/login"));
          }}
          className="mt-4 border p-2 text-left"
        >
          Log out
        </button>
      </nav>
      <main className="flex-1 p-6">
        {children}
        <p className="mt-12 border-t pt-4 text-xs text-gray-500">
          Informational tool only — not regulated financial, investment, or tax advice.
        </p>
      </main>
    </div>
  );
}
