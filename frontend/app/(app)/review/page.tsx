"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth-context";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api-client";
import { confidenceBand, formatDate, formatCurrency } from "@/lib/format";
import type { Category, Transaction } from "@/types/api";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { AlertCircle } from "lucide-react";

/** FR-15.2: keyboard-driven rapid triage — j/k navigate, 1-9 assign a
 * frequent category, enter accept the top suggestion (currently: the
 * first category in the frequent list), s skip. */
export default function ReviewPage() {
  const { user } = useAuth();
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
    <div className="flex flex-col gap-6 font-sans">
      <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white overflow-hidden">
        <CardHeader className="flex flex-col md:flex-row md:items-center justify-between px-6 pt-6 pb-4 border-b border-gray-100 gap-4">
          <p className="text-sm text-gray-500 font-medium">
            Keyboard: <kbd className="px-1.5 py-0.5 rounded border border-gray-200 bg-gray-50 text-xs">j</kbd>/<kbd className="px-1.5 py-0.5 rounded border border-gray-200 bg-gray-50 text-xs">k</kbd> navigate · <kbd className="px-1.5 py-0.5 rounded border border-gray-200 bg-gray-50 text-xs">1-9</kbd> assign category · <kbd className="px-1.5 py-0.5 rounded border border-gray-200 bg-gray-50 text-xs">s</kbd> skip
          </p>

          {selectedIds.size > 0 && (
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-blue-600 bg-blue-50 px-3 py-1 rounded-full">{selectedIds.size} selected</span>
              <select
                onChange={(e) => {
                  if (e.target.value) bulkCategorise.mutate({ ids: [...selectedIds], categoryId: e.target.value });
                }}
                className="rounded-full border border-gray-200 bg-gray-50 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 transition-shadow"
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
        </CardHeader>
        
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm text-left">
              <thead className="bg-gray-50/50">
                <tr className="border-b border-gray-100 text-gray-500">
                  <th className="p-4 px-6 w-12 text-center">
                    <input
                      type="checkbox"
                      className="rounded border-gray-300 text-gray-900 focus:ring-gray-900"
                      onChange={(e) => {
                        if (e.target.checked && transactions) {
                          setSelectedIds(new Set(transactions.map(t => t._id)));
                        } else {
                          setSelectedIds(new Set());
                        }
                      }}
                      checked={transactions && transactions.length > 0 && selectedIds.size === transactions.length}
                    />
                  </th>
                  <th className="p-4 px-6 font-medium whitespace-nowrap">Date</th>
                  <th className="p-4 px-6 font-medium">Description</th>
                  <th className="p-4 px-6 font-medium text-right">Amount</th>
                  <th className="p-4 px-6 font-medium text-center">Confidence</th>
                  <th className="p-4 px-6 font-medium">Assign</th>
                </tr>
              </thead>
              <tbody>
                {transactions?.map((t, i) => (
                  <tr key={t._id} className={`border-b border-gray-50 transition-colors ${i === cursor ? "bg-orange-50/50 ring-1 ring-inset ring-orange-200" : "hover:bg-gray-50/50"}`}>
                    <td className="p-4 px-6 text-center">
                      <input
                        type="checkbox"
                        className="rounded border-gray-300 text-gray-900 focus:ring-gray-900"
                        checked={selectedIds.has(t._id)}
                        onChange={(e) => {
                          const next = new Set(selectedIds);
                          if (e.target.checked) next.add(t._id);
                          else next.delete(t._id);
                          setSelectedIds(next);
                        }}
                      />
                    </td>
                    <td className="p-4 px-6 whitespace-nowrap text-gray-500">{formatDate(t.date)}</td>
                    <td className="p-4 px-6 font-medium text-gray-900">{t.description_raw}</td>
                    <td className="p-4 px-6 text-right font-semibold text-gray-900">{formatCurrency(t.amount_minor, user?.settings?.currency)}</td>
                    <td className="p-4 px-6 text-center">
                      <span className={`inline-flex items-center gap-1.5 justify-center rounded-full px-2.5 py-0.5 text-xs font-medium ${confidenceBand(t.confidence) === 'high' ? 'bg-green-100 text-green-700' : confidenceBand(t.confidence) === 'medium' ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-600'}`}>
                        {confidenceBand(t.confidence) !== 'high' && <AlertCircle className="h-3 w-3" />}
                        {t.confidence}
                      </span>
                    </td>
                    <td className="p-4 px-6">
                      <select
                        defaultValue=""
                        onChange={(e) => e.target.value && categorise.mutate({ id: t._id, categoryId: e.target.value })}
                        className="rounded-lg border border-gray-200 bg-transparent px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 min-w-[140px]"
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
                {transactions?.length === 0 && (
                  <tr>
                    <td colSpan={6} className="p-12 text-center text-gray-500">
                      <div className="flex flex-col items-center justify-center gap-2">
                        <span className="text-4xl">✨</span>
                        <p className="font-medium text-gray-900">All caught up!</p>
                        <p className="text-sm">Nothing needs review right now.</p>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
