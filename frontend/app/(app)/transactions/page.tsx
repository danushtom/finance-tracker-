"use client";

import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api-client";
import { currentMonthKey, formatDate, formatINR } from "@/lib/format";
import type { Category, Transaction } from "@/types/api";

export default function TransactionsPage() {
  const [month, setMonth] = useState(currentMonthKey());
  const queryClient = useQueryClient();

  const { data: transactions, isLoading } = useQuery({
    queryKey: ["transactions", { month }],
    queryFn: () => api.get<Transaction[]>(`/transactions?month=${month}&limit=200`),
  });

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => api.get<Category[]>("/categories"),
  });

  const updateCategory = useMutation({
    mutationFn: ({ id, categoryId }: { id: string; categoryId: string }) =>
      api.patch(`/transactions/${id}`, { category_id: categoryId }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["transactions"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  return (
    <div className="flex flex-col gap-4">
      <header className="flex items-center gap-4">
        <h1 className="text-xl font-semibold">Transactions</h1>
        <input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="border p-1" />
      </header>

      {isLoading && <p>Loading…</p>}

      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b text-left">
            <th className="p-2">Date</th>
            <th className="p-2">Description</th>
            <th className="p-2">Amount</th>
            <th className="p-2">Category</th>
            <th className="p-2">Confidence</th>
          </tr>
        </thead>
        <tbody>
          {transactions?.map((t) => (
            <tr key={t._id} className={`border-b ${t.needs_review ? "bg-yellow-50" : ""}`}>
              <td className="p-2">{formatDate(t.date)}</td>
              <td className="p-2">{t.description_raw}</td>
              <td className="p-2">{formatINR(t.amount_minor)}</td>
              <td className="p-2">
                <select
                  value={t.category_id ?? ""}
                  onChange={(e) => updateCategory.mutate({ id: t._id, categoryId: e.target.value })}
                  className="border p-1"
                >
                  <option value="">Uncategorised</option>
                  {categories?.map((c) => (
                    <option key={c._id} value={c._id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </td>
              <td className="p-2">{t.confidence}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
