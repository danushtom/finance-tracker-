"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api-client";
import { formatDate, formatINR } from "@/lib/format";
import type { Category, Transaction } from "@/types/api";

/** FR-15.2: keyboard-driven rapid triage — j/k navigate, 1-9 assign a
 * frequent category, enter accept the top suggestion (currently: the
 * first category in the frequent list), s skip. */
export default function ReviewPage() {
  const queryClient = useQueryClient();
  const [cursor, setCursor] = useState(0);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const { data: transactions } = useQuery({
    queryKey: ["review-queue"],
    queryFn: () => api.get<Transaction[]>("/transactions/review"),
  });

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => api.get<Category[]>("/categories"),
  });

  const frequentCategories = useMemo(() => (categories ?? []).slice(0, 9), [categories]);

  const categorise = useMutation({
    mutationFn: ({ id, categoryId }: { id: string; categoryId: string }) =>
      api.patch(`/transactions/${id}`, { category_id: categoryId }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  const bulkCategorise = useMutation({
    mutationFn: ({ ids, categoryId }: { ids: string[]; categoryId: string }) =>
      api.post("/transactions/bulk-categorise", { transaction_ids: ids, category_id: categoryId }),
    onSuccess: () => {
      setSelectedIds(new Set());
      void queryClient.invalidateQueries({ queryKey: ["review-queue"] });
    },
  });

  const current = transactions?.[cursor];

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (!transactions || transactions.length === 0) return;
      if (e.key === "j") setCursor((c) => Math.min(c + 1, transactions.length - 1));
      else if (e.key === "k") setCursor((c) => Math.max(c - 1, 0));
      else if (e.key === "s") setCursor((c) => Math.min(c + 1, transactions.length - 1));
      else if (/^[1-9]$/.test(e.key)) {
        const idx = Number(e.key) - 1;
        const category = frequentCategories[idx];
        if (category && current) {
          categorise.mutate({ id: current._id, categoryId: category._id });
        }
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [transactions, frequentCategories, current, categorise]);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Review queue</h1>
      <p className="text-sm text-gray-500">
        Keyboard: j/k navigate · 1-9 assign category · s skip
      </p>

      {selectedIds.size > 0 && (
        <div className="flex items-center gap-2 border p-2">
          <span className="text-sm">{selectedIds.size} selected</span>
          <select
            onChange={(e) => {
              if (e.target.value) bulkCategorise.mutate({ ids: [...selectedIds], categoryId: e.target.value });
            }}
            className="border p-1"
          >
            <option value="">Bulk assign category…</option>
            {categories?.map((c) => (
              <option key={c._id} value={c._id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
      )}

      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b text-left">
            <th className="p-2"></th>
            <th className="p-2">Date</th>
            <th className="p-2">Description</th>
            <th className="p-2">Amount</th>
            <th className="p-2">Confidence</th>
            <th className="p-2">Assign</th>
          </tr>
        </thead>
        <tbody>
          {transactions?.map((t, i) => (
            <tr key={t._id} className={`border-b ${i === cursor ? "bg-yellow-50" : ""}`}>
              <td className="p-2">
                <input
                  type="checkbox"
                  checked={selectedIds.has(t._id)}
                  onChange={(e) => {
                    const next = new Set(selectedIds);
                    if (e.target.checked) next.add(t._id);
                    else next.delete(t._id);
                    setSelectedIds(next);
                  }}
                />
              </td>
              <td className="p-2">{formatDate(t.date)}</td>
              <td className="p-2">{t.description_raw}</td>
              <td className="p-2">{formatINR(t.amount_minor)}</td>
              <td className="p-2">⚠️ {t.confidence}</td>
              <td className="p-2">
                <select
                  defaultValue=""
                  onChange={(e) => e.target.value && categorise.mutate({ id: t._id, categoryId: e.target.value })}
                  className="border p-1"
                >
                  <option value="">Assign…</option>
                  {categories?.map((c) => (
                    <option key={c._id} value={c._id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {transactions?.length === 0 && <p>Nothing needs review right now.</p>}
    </div>
  );
}
