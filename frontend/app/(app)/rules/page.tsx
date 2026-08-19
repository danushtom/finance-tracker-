"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api-client";
import type { Category, MatchType, Rule } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function RulesPage() {
  const queryClient = useQueryClient();
  const [pattern, setPattern] = useState("");
  const [matchType, setMatchType] = useState<MatchType>("contains");
  const [categoryId, setCategoryId] = useState("");
  const [backfill, setBackfill] = useState(true);

  const { data: rules } = useQuery({
    queryKey: ["rules"],
    queryFn: () => api.get<Rule[]>("/rules"),
  });

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => api.get<Category[]>("/categories"),
  });

  const createRule = useMutation({
    mutationFn: () =>
      api.post("/rules", { match_type: matchType, pattern, category_id: categoryId, backfill }),
    onSuccess: () => {
      setPattern("");
      void queryClient.invalidateQueries({ queryKey: ["rules"] });
    },
  });

  const toggleRule = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => api.patch(`/rules/${id}`, { enabled }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["rules"] }),
  });

  const deleteRule = useMutation({
    mutationFn: (id: string) => api.delete(`/rules/${id}`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["rules"] }),
  });

  const categoryName = (id: string) => categories?.find((c) => c._id === id)?.name ?? id;

  return (
    <div className="flex flex-col gap-6 font-sans">
      
      <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white">
        <CardHeader className="px-6 pt-6 pb-2">
          <CardTitle className="text-lg font-bold">Create Rule</CardTitle>
        </CardHeader>
        <CardContent className="px-6 pb-6 pt-2">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (pattern && categoryId) createRule.mutate();
            }}
            className="flex flex-wrap items-end gap-4"
          >
            <label className="flex flex-col gap-1.5 flex-1 min-w-[150px]">
              <span className="text-sm font-medium text-gray-700">Match type</span>
              <select 
                value={matchType} 
                onChange={(e) => setMatchType(e.target.value as MatchType)} 
                className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
              >
                <option value="exact">Exact</option>
                <option value="contains">Contains</option>
                <option value="starts_with">Starts with</option>
                <option value="regex">Regex</option>
              </select>
            </label>
            <label className="flex flex-col gap-1.5 flex-[2] min-w-[200px]">
              <span className="text-sm font-medium text-gray-700">Pattern</span>
              <input 
                value={pattern} 
                onChange={(e) => setPattern(e.target.value)} 
                placeholder="e.g. STARBUCKS"
                className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900" 
              />
            </label>
            <label className="flex flex-col gap-1.5 flex-1 min-w-[150px]">
              <span className="text-sm font-medium text-gray-700">Category</span>
              <select 
                value={categoryId} 
                onChange={(e) => setCategoryId(e.target.value)} 
                className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
              >
                <option value="">Select…</option>
                {categories?.map((c) => (
                  <option key={c._id} value={c._id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700 pb-2">
              <input 
                type="checkbox" 
                checked={backfill} 
                onChange={(e) => setBackfill(e.target.checked)} 
                className="rounded border-gray-300 text-gray-900 focus:ring-gray-900 h-4 w-4"
              />
              Backfill past
            </label>
            <Button type="submit" disabled={!pattern || !categoryId} className="rounded-full bg-gray-900 text-white hover:bg-gray-800 px-6 shadow-sm">
              Create rule
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white overflow-hidden">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm text-left">
              <thead className="bg-gray-50/50">
                <tr className="border-b border-gray-100 text-gray-500">
                  <th className="p-4 px-6 font-medium">Pattern</th>
                  <th className="p-4 px-6 font-medium">Match</th>
                  <th className="p-4 px-6 font-medium">Category</th>
                  <th className="p-4 px-6 font-medium text-center">Priority</th>
                  <th className="p-4 px-6 font-medium">Source</th>
                  <th className="p-4 px-6 font-medium text-center">Enabled</th>
                  <th className="p-4 px-6 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {rules?.map((r) => (
                  <tr key={r._id} className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
                    <td className="p-4 px-6 font-semibold text-gray-900">{r.pattern}</td>
                    <td className="p-4 px-6 text-gray-500">{r.match_type}</td>
                    <td className="p-4 px-6 text-gray-900">
                      <span className="inline-flex items-center justify-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700">
                        {categoryName(r.category_id)}
                      </span>
                    </td>
                    <td className="p-4 px-6 text-center text-gray-500">{r.priority}</td>
                    <td className="p-4 px-6 text-gray-500">{r.source}</td>
                    <td className="p-4 px-6 text-center">
                      <input
                        type="checkbox"
                        checked={r.enabled}
                        onChange={(e) => toggleRule.mutate({ id: r._id, enabled: e.target.checked })}
                        className="rounded border-gray-300 text-gray-900 focus:ring-gray-900"
                      />
                    </td>
                    <td className="p-4 px-6 text-right">
                      <button onClick={() => deleteRule.mutate(r._id)} className="text-red-500 hover:text-red-700 text-sm font-medium transition-colors">
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
                {rules?.length === 0 && (
                  <tr>
                    <td colSpan={7} className="p-8 text-center text-gray-500">No rules configured yet.</td>
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
