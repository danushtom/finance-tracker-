"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  ArrowDownRight,
  ArrowUpRight,
  Plus,
  AlertCircle,
  TrendingUp,
  Target,
  Gift,
  ChevronRight,
} from "lucide-react";

import { api } from "@/lib/api-client";
import { currentMonthKey, formatINR } from "@/lib/format";
import type { DashboardPayload } from "@/types/api";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";

// Mock data for the historical chart as the current API only returns single-month data
const mockChartData = [
  { name: "Jan", income: 28000, expense: 24000 },
  { name: "Feb", income: 30000, expense: 13980 },
  { name: "Mar", income: 20000, expense: 38000 },
  { name: "Apr", income: 27800, expense: 39080 },
  { name: "May", income: 33800, expense: 32600 },
  { name: "Jun", income: 23900, expense: 38000 },
  { name: "Jul", income: 34900, expense: 4300 },
];

export default function DashboardPage() {
  const [month, setMonth] = useState(currentMonthKey());

  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard", month],
    queryFn: () => api.get<DashboardPayload>(`/dashboard?month=${month}`),
  });

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center p-8 bg-background text-foreground">
        <p className="animate-pulse text-lg font-medium">Loading dashboard...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex min-h-screen items-center justify-center p-8 bg-background text-red-600">
        <p>Could not load the dashboard.</p>
      </div>
    );
  }

  const sts = data.safe_to_spend;

  return (
    <div className="min-h-screen bg-background p-6 md:p-10 font-sans text-card-foreground">
      {/* Header */}
      <header className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Good Morning, William</h1>
          <p className="text-muted-foreground mt-1">Here's your financial overview for {month}</p>
        </div>
        <div className="flex items-center gap-4">
          <input
            type="month"
            value={month}
            onChange={(e) => setMonth(e.target.value)}
            className="rounded-full border border-border/50 bg-surface px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary shadow-sm"
          />
          <Button variant="default" className="gap-2">
            <Plus className="h-4 w-4" /> Add Transaction
          </Button>
        </div>
      </header>

      {/* Review Alert */}
      {data.review_queue_count > 0 && (
        <a href="/review" className="block mb-6">
          <div className="glass-card flex items-center justify-between p-4 bg-orange-50/50 border-orange-200">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-accent" />
              <span className="font-medium text-orange-900">
                You have {data.review_queue_count} transaction(s) that need review
              </span>
            </div>
            <Button variant="outline" size="sm" className="border-orange-200 bg-white">
              Review Now
            </Button>
          </div>
        </a>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column (Spans 2) */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Financial Analytics Chart */}
          <Card className="glass-card overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle>Financial analytics</CardTitle>
              <div className="flex space-x-2 text-sm font-medium text-muted-foreground">
                <span className="text-primary cursor-pointer border-b-2 border-primary pb-1">Summary</span>
                <span className="cursor-pointer hover:text-card-foreground pb-1">Balance</span>
                <span className="cursor-pointer hover:text-card-foreground pb-1">Net Worth</span>
              </div>
            </CardHeader>
            <CardContent>
              <div className="h-[300px] w-full mt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={mockChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                    <XAxis 
                      dataKey="name" 
                      axisLine={false} 
                      tickLine={false} 
                      tick={{ fill: '#6B7280', fontSize: 12 }} 
                      dy={10}
                    />
                    <YAxis 
                      axisLine={false} 
                      tickLine={false} 
                      tick={{ fill: '#6B7280', fontSize: 12 }}
                      tickFormatter={(value) => `₹${value / 1000}k`}
                    />
                    <Tooltip 
                      cursor={{ fill: '#F3F4F6' }}
                      contentStyle={{ borderRadius: '1rem', border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.08)' }}
                    />
                    <Bar dataKey="income" fill="#1E5FF5" radius={[4, 4, 0, 0]} barSize={32} />
                    <Bar dataKey="expense" fill="#FF6B4A" radius={[4, 4, 0, 0]} barSize={32} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Quick Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatsCard label="Spent" value={data.spent_minor} icon={<TrendingUp className="text-accent" />} />
            <StatsCard label="Saved" value={data.saved_minor} icon={<PiggyBank className="text-green-500" />} />
            <StatsCard label="Invested" value={data.invested_minor} icon={<ArrowUpRight className="text-primary" />} />
            <StatsCard label="Available" value={data.available_minor} icon={<Wallet className="text-purple-500" />} />
          </div>

          {/* Safe to Spend Banner */}
          <Card className="glass-card bg-gradient-to-r from-primary/5 to-transparent border-primary/20">
            <CardContent className="flex items-center justify-between p-6">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">Safe to spend</p>
                <h2 className="text-4xl font-bold text-card-foreground">
                  {sts.is_over ? `₹0` : formatINR(sts.amount_minor)}
                </h2>
                {sts.is_over && (
                  <Badge variant="danger" className="mt-2">Over by {formatINR(sts.over_by_minor)}</Badge>
                )}
                {sts.per_day_minor != null && !sts.is_over && (
                  <p className="text-sm text-primary font-medium mt-2">
                    {formatINR(sts.per_day_minor)} / day for {sts.days_left} days left
                  </p>
                )}
              </div>
              <div className="hidden md:block">
                <details className="group">
                  <summary className="cursor-pointer text-sm font-medium text-muted-foreground hover:text-primary transition-colors flex items-center gap-1 list-none">
                    Explain this <ChevronRight className="h-4 w-4 group-open:rotate-90 transition-transform" />
                  </summary>
                  <div className="absolute right-10 mt-2 w-64 glass-card p-4 z-10 text-sm">
                    {sts.lines.map((line) => (
                      <div key={line.label} className="flex justify-between py-1 border-b border-border/50 last:border-0">
                        <span className="text-muted-foreground">{line.label}</span>
                        <span className="font-medium">{line.sign} {formatINR(line.amount_minor)}</span>
                      </div>
                    ))}
                  </div>
                </details>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          
          {/* Top Spending Categories */}
          <Card className="glass-card">
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
              <CardTitle>Top Spending</CardTitle>
              <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full">
                <ChevronRight className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent>
              <div className="mb-6">
                <p className="text-sm text-muted-foreground">Spent This Month</p>
                <p className="text-3xl font-bold mt-1">{formatINR(data.spent_minor)}</p>
              </div>
              <div className="space-y-4">
                {data.category_breakdown.slice(0, 4).map((row, i) => (
                  <div key={`${row.category_name}-${row.class}`}>
                    <div className="flex justify-between text-sm mb-1.5">
                      <div className="flex items-center gap-2">
                        <div className={`h-2 w-2 rounded-full ${i === 0 ? 'bg-primary' : i === 1 ? 'bg-accent' : 'bg-green-500'}`} />
                        <span className="font-medium">{row.category_name}</span>
                      </div>
                      <span className="font-semibold">{formatINR(row.total_minor)}</span>
                    </div>
                    <Progress value={(row.total_minor / Math.max(data.spent_minor, 1)) * 100} 
                              indicatorClassName={i === 0 ? 'bg-primary' : i === 1 ? 'bg-accent' : 'bg-green-500'} />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Goals */}
          {data.top_goals.length > 0 && (
            <Card className="glass-card">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2">
                  <Target className="h-5 w-5 text-primary" /> Goals
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {data.top_goals.map((g) => {
                  const percent = Math.min(100, (g.current_amount_minor / g.target_amount_minor) * 100);
                  return (
                    <div key={g.id}>
                      <div className="flex justify-between text-sm mb-1.5">
                        <span className="font-medium">{g.name}</span>
                        <span className="text-muted-foreground text-xs">
                          {formatINR(g.current_amount_minor)} / {formatINR(g.target_amount_minor)}
                        </span>
                      </div>
                      <Progress value={percent} className="h-1.5" />
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}

          {/* Wishlist */}
          {data.top_wishlist.length > 0 && (
            <Card className="glass-card bg-primary text-white border-none shadow-lg">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-white">
                  <Gift className="h-5 w-5" /> Wishlist
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {data.top_wishlist.slice(0, 3).map((w) => (
                  <div key={w.id} className="flex justify-between items-center py-2 border-b border-white/20 last:border-0">
                    <span className="font-medium">{w.name}</span>
                    <span className="font-semibold">{formatINR(w.price_minor)}</span>
                  </div>
                ))}
                <Button variant="secondary" className="w-full mt-2 bg-white/20 text-white hover:bg-white/30 border-none">
                  View All
                </Button>
              </CardContent>
            </Card>
          )}

        </div>
      </div>
    </div>
  );
}

function StatsCard({ label, value, icon }: { label: string; value: number; icon: React.ReactNode }) {
  return (
    <Card className="glass-card border-none shadow-sm hover:shadow-md transition-shadow">
      <CardContent className="p-5 flex flex-col justify-between h-full">
        <div className="flex justify-between items-start mb-4">
          <p className="text-sm font-medium text-muted-foreground">{label}</p>
          <div className="p-2 bg-muted rounded-full">
            {icon}
          </div>
        </div>
        <div>
          <p className="text-xl md:text-2xl font-bold">{formatINR(value)}</p>
        </div>
      </CardContent>
    </Card>
  );
}
