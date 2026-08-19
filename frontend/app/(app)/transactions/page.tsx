"use client";

import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth-context";
import { useState } from "react";
import { api } from "@/lib/api-client";
import { confidenceBand, currentMonthKey, formatDate, formatCurrency } from "@/lib/format";
import type { Category, Transaction } from "@/types/api";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export default function TransactionsPage() {
  const { user } = useAuth();
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
    <div className="flex flex-col gap-6 font-sans">
      <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white overflow-hidden">
        <CardHeader className="flex flex-row items-center justify-between px-6 pt-6 pb-4 border-b border-gray-100">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium text-gray-500">Filter by month:</span>
            <input 
              type="month" 
              value={month} 
              onChange={(e) => setMonth(e.target.value)} 
              className="rounded-full border border-gray-200 bg-gray-50 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 transition-shadow" 
            />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading && (
            <div className="p-8 text-center text-gray-500 animate-pulse">Loading transactions...</div>
          )}
          
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm text-left">
              <thead className="bg-gray-50/50">
                <tr className="border-b border-gray-100 text-gray-500">
                  <th className="p-4 px-6 font-medium whitespace-nowrap">Date</th>
                  <th className="p-4 px-6 font-medium">Description</th>
                  <th className="p-4 px-6 font-medium text-right">Amount</th>
                  <th className="p-4 px-6 font-medium">Category</th>
                  <th className="p-4 px-6 font-medium text-center">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {transactions?.map((t) => (
                  <tr key={t._id} className={`border-b border-gray-50 hover:bg-gray-50/50 transition-colors ${t.needs_review ? "bg-orange-50/30 hover:bg-orange-50/50" : ""}`}>
                    <td className="p-4 px-6 whitespace-nowrap text-gray-500">{formatDate(t.date)}</td>
                    <td className="p-4 px-6 font-medium text-gray-900">{t.description_raw}</td>
                    <td className="p-4 px-6 text-right font-semibold text-gray-900">{formatCurrency(t.amount_minor, user?.settings?.currency)}</td>
                    <td className="p-4 px-6">
                      <select
                        value={t.category_id ?? ""}
                        onChange={(e) => updateCategory.mutate({ id: t._id, categoryId: e.target.value })}
                        className="rounded-lg border border-gray-200 bg-transparent px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 min-w-[140px]"
                      >
                        <option value="">Uncategorised</option>
                        {categories?.map((c) => (
                          <option key={c._id} value={c._id}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="p-4 px-6 text-center">
                      <span className={`inline-flex items-center justify-center rounded-full px-2.5 py-0.5 text-xs font-medium ${confidenceBand(t.confidence) === 'high' ? 'bg-green-100 text-green-700' : confidenceBand(t.confidence) === 'medium' ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-600'}`}>
                        {t.confidence}
                      </span>
                    </td>
                  </tr>
                ))}
                {transactions?.length === 0 && (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-gray-500">No transactions found for this month.</td>
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
