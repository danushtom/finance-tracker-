"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { useAuth } from "@/lib/auth-context";
import {
  LayoutDashboard,
  ArrowRightLeft,
  Upload,
  CheckSquare,
  ClipboardList,
  Gift,
  Target,
  TrendingUp,
  WalletCards,
  Settings,
  Hexagon,
  Bell,
} from "lucide-react";
import { Button } from "@/components/ui/button";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/transactions", label: "Transactions", icon: ArrowRightLeft },
  { href: "/import", label: "Import", icon: Upload },
  { href: "/review", label: "Review", icon: CheckSquare },
  { href: "/rules", label: "Rules", icon: ClipboardList },
  { href: "/wishlist", label: "Wishlist", icon: Gift },
  { href: "/goals", label: "Goals", icon: Target },
  { href: "/investments", label: "Investments", icon: TrendingUp },
  { href: "/accounts", label: "Accounts", icon: WalletCards },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function AppLayout({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
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

  const isDashboard = pathname === "/dashboard";
  const activeNavItem = NAV_ITEMS.find((item) => pathname?.startsWith(item.href));
  const pageTitle = isDashboard
    ? `Good Morning, ${user?.display_name || user?.email?.split("@")[0] || "William"}`
    : activeNavItem?.label || "App";

  return (
    <div className="flex h-screen overflow-hidden bg-[#f8f9fc]">
      {/* Sidebar */}
      <nav className="flex w-64 flex-col border-r border-gray-100 bg-white px-4 py-6">
        {/* Logo */}
        <div className="mb-16 flex items-center gap-3 px-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-white">
            <Hexagon className="h-5 w-5 fill-current" />
          </div>
          <span className="text-xl font-bold tracking-tight text-gray-900">Bright AI</span>
        </div>

        {/* Navigation */}
        <div className="flex flex-1 flex-col gap-1">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname?.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 rounded-full px-4 py-3 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-gray-900 text-white"
                    : "text-gray-500 hover:bg-gray-100 hover:text-gray-900"
                }`}
              >
                <item.icon className={`h-5 w-5 ${isActive ? "text-white" : "text-gray-400"}`} />
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-1 overflow-auto bg-[#f8f9fc] flex flex-col">
        {/* Global Top Header */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 md:px-10 md:pt-10 pb-2">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900">{pageTitle}</h1>
          </div>
          <div className="flex items-center gap-4">
            {isDashboard && (
              <Button variant="default" className="rounded-full bg-gray-900 text-white hover:bg-gray-800 px-6 h-11 shadow-sm">
                <Gift className="mr-2 h-4 w-4" /> Get $25
              </Button>
            )}
            {isDashboard && (
              <Button variant="outline" className="rounded-full bg-white px-6 h-11 shadow-sm border-gray-200 text-gray-700 hover:bg-gray-50">
                + Account
              </Button>
            )}
            <div className="relative h-11 w-11 flex items-center justify-center rounded-full bg-white shadow-sm border border-gray-100 cursor-pointer hover:bg-gray-50 transition-colors">
              <Bell className="h-5 w-5 text-gray-600" />
              <div className="absolute top-3 right-3 h-2 w-2 rounded-full bg-orange-500 border-2 border-white"></div>
            </div>
            <div className="h-11 w-11 overflow-hidden rounded-full border border-gray-200 cursor-pointer shadow-sm">
              <img src="https://i.pravatar.cc/150?u=william" alt="Profile" className="h-full w-full object-cover" />
            </div>
          </div>
        </header>

        <div className="flex-1 p-6 md:px-10">
          {children}
        </div>
        <div className="px-6 md:px-10 pb-6">
          <p className="mt-8 border-t border-gray-200 pt-4 text-xs text-gray-400">
            Informational tool only — not regulated financial, investment, or tax advice.
          </p>
        </div>
      </main>
    </div>
  );
}
