"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api-client";
import type { Category, MatchType, Rule } from "@/types/api";

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
    <div className="flex flex-col gap-8">
      <h1 className="text-xl font-semibold">Rules</h1>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (pattern && categoryId) createRule.mutate();
        }}
        className="flex flex-wrap items-end gap-2 border p-4"
      >
        <label className="flex flex-col gap-1">
          <span className="text-sm">Match type</span>
          <select value={matchType} onChange={(e) => setMatchType(e.target.value as MatchType)} className="border p-1">
            <option value="exact">Exact</option>
            <option value="contains">Contains</option>
            <option value="starts_with">Starts with</option>
            <option value="regex">Regex</option>
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm">Pattern</span>
          <input value={pattern} onChange={(e) => setPattern(e.target.value)} className="border p-1" />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm">Category</span>
          <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)} className="border p-1">
            <option value="">Select…</option>
            {categories?.map((c) => (
              <option key={c._id} value={c._id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-1 text-sm">
          <input type="checkbox" checked={backfill} onChange={(e) => setBackfill(e.target.checked)} />
          Backfill past transactions
        </label>
        <button type="submit" className="border p-2">
          Create rule
        </button>
      </form>

      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b text-left">
            <th className="p-2">Pattern</th>
            <th className="p-2">Match</th>
            <th className="p-2">Category</th>
            <th className="p-2">Priority</th>
            <th className="p-2">Source</th>
            <th className="p-2">Enabled</th>
            <th className="p-2"></th>
          </tr>
        </thead>
        <tbody>
          {rules?.map((r) => (
            <tr key={r._id} className="border-b">
              <td className="p-2">{r.pattern}</td>
              <td className="p-2">{r.match_type}</td>
              <td className="p-2">{categoryName(r.category_id)}</td>
              <td className="p-2">{r.priority}</td>
              <td className="p-2">{r.source}</td>
              <td className="p-2">
                <input
                  type="checkbox"
                  checked={r.enabled}
                  onChange={(e) => toggleRule.mutate({ id: r._id, enabled: e.target.checked })}
                />
              </td>
              <td className="p-2">
                <button onClick={() => deleteRule.mutate(r._id)} className="underline">
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
