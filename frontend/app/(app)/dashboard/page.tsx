"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api-client";
import { currentMonthKey, formatINR } from "@/lib/format";
import type { DashboardPayload } from "@/types/api";

export default function DashboardPage() {
  const [month, setMonth] = useState(currentMonthKey());

  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard", month],
    queryFn: () => api.get<DashboardPayload>(`/dashboard?month=${month}`),
  });

  if (isLoading) return <p>Loading dashboard…</p>;
  if (error || !data) return <p className="text-red-600">Could not load the dashboard.</p>;

  const sts = data.safe_to_spend;

  return (
    <div className="flex flex-col gap-8">
      <header className="flex items-center gap-4">
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <input
          type="month"
          value={month}
          onChange={(e) => setMonth(e.target.value)}
          className="border p-1"
        />
      </header>

      <section className="flex gap-8">
        <div>
          <p className="text-sm text-gray-500">Baseline income</p>
          <p className="text-lg">{formatINR(data.baseline_income_minor)}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Variable income</p>
          <p className="text-lg">{formatINR(data.variable_income_minor)}</p>
        </div>
      </section>

      <section className="grid grid-cols-4 gap-4">
        <Tile label="Spent" value={data.spent_minor} />
        <Tile label="Saved" value={data.saved_minor} />
        <Tile label="Invested" value={data.invested_minor} />
        <Tile label="Available" value={data.available_minor} />
      </section>

      <section className="border p-6">
        <p className="text-sm text-gray-500">Safe to spend</p>
        <p className="text-4xl font-bold">
          {sts.is_over ? `₹0 (over by ${formatINR(sts.over_by_minor)})` : formatINR(sts.amount_minor)}
        </p>
        {sts.per_day_minor != null && (
          <p className="text-sm text-gray-500">
            {formatINR(sts.per_day_minor)}/day for the {sts.days_left} day(s) remaining
          </p>
        )}
        <details className="mt-4">
          <summary className="cursor-pointer text-sm underline">Explain this number</summary>
          <ul className="mt-2 flex flex-col gap-1">
            {sts.lines.map((line) => (
              <li key={line.label} className="flex justify-between border-b py-1 text-sm">
                <span>{line.label}</span>
                <span>
                  {line.sign} {formatINR(line.amount_minor)}
                </span>
              </li>
            ))}
          </ul>
        </details>
      </section>

      {data.isolated.length > 0 && (
        <section>
          <h2 className="mb-2 font-semibold">Isolated categories</h2>
          <div className="flex gap-4">
            {data.isolated.map((row) => (
              <div key={row.category_name} className="border p-3">
                <p className="text-sm text-gray-500">{row.category_name}</p>
                <p>{formatINR(row.total_minor)}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 className="mb-2 font-semibold">Fixed commitments</h2>
        <p className="text-sm text-gray-500">
          {formatINR(data.fixed_paid_minor)} paid of {formatINR(data.fixed_due_minor)} due
        </p>
        <ul className="mt-2 flex flex-col gap-1">
          {data.fixed_commitments.map((c) => (
            <li key={c.id} className="flex justify-between border-b py-1 text-sm">
              <span>{c.display_name}</span>
              <span>{formatINR(c.expected_amount_minor)}</span>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="mb-2 font-semibold">Spending by category</h2>
        <ul className="flex flex-col gap-1">
          {data.category_breakdown.map((row) => (
            <li key={`${row.category_name}-${row.class}`} className="flex justify-between border-b py-1 text-sm">
              <span>{row.category_name}</span>
              <span>{formatINR(row.total_minor)}</span>
            </li>
          ))}
        </ul>
      </section>

      {data.review_queue_count > 0 && (
        <a href="/review" className="border p-3 text-sm underline">
          ⚠️ {data.review_queue_count} transaction(s) need review
        </a>
      )}

      <section className="grid grid-cols-2 gap-4">
        <div>
          <h2 className="mb-2 font-semibold">Top goals</h2>
          <ul className="flex flex-col gap-1">
            {data.top_goals.map((g) => (
              <li key={g.id} className="text-sm">
                {g.name} — {formatINR(g.current_amount_minor)} / {formatINR(g.target_amount_minor)}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h2 className="mb-2 font-semibold">Top wishlist</h2>
          <ul className="flex flex-col gap-1">
            {data.top_wishlist.map((w) => (
              <li key={w.id} className="text-sm">
                {w.name} — {formatINR(w.price_minor)}
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}

function Tile({ label, value }: { label: string; value: number }) {
  return (
    <div className="border p-3">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-lg">{formatINR(value)}</p>
    </div>
  );
}
