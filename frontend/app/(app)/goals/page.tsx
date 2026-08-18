"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api-client";
import { formatINR } from "@/lib/format";
import type { GoalWithProgress } from "@/types/api";

export default function GoalsPage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [targetRupees, setTargetRupees] = useState("");

  const { data: goals, isLoading } = useQuery({
    queryKey: ["goals"],
    queryFn: () => api.get<GoalWithProgress[]>("/goals"),
  });

  const createGoal = useMutation({
    mutationFn: () => api.post("/goals", { name, target_amount_minor: Math.round(parseFloat(targetRupees) * 100) }),
    onSuccess: () => {
      setName("");
      setTargetRupees("");
      void queryClient.invalidateQueries({ queryKey: ["goals"] });
    },
  });

  const ensureEmergencyFund = useMutation({
    mutationFn: () => api.post("/goals/ensure-emergency-fund"),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["goals"] }),
  });

  const contribute = useMutation({
    mutationFn: ({ id, amountMinor }: { id: string; amountMinor: number }) =>
      api.post(`/goals/${id}/contribute`, { amount_minor: amountMinor }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["goals"] }),
  });

  return (
    <div className="flex flex-col gap-8">
      <h1 className="text-xl font-semibold">Goals</h1>

      <button onClick={() => ensureEmergencyFund.mutate()} className="w-fit border p-2 text-sm">
        Create / update Emergency Fund goal (6× median essential expenses)
      </button>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (name && targetRupees) createGoal.mutate();
        }}
        className="flex flex-wrap items-end gap-2 border p-4"
      >
        <label className="flex flex-col gap-1">
          <span className="text-sm">Goal name</span>
          <input value={name} onChange={(e) => setName(e.target.value)} className="border p-1" />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm">Target (₹)</span>
          <input
            type="number"
            value={targetRupees}
            onChange={(e) => setTargetRupees(e.target.value)}
            className="border p-1"
          />
        </label>
        <button type="submit" className="border p-2">
          Add goal
        </button>
      </form>

      {isLoading && <p>Loading…</p>}

      <ul className="flex flex-col gap-4">
        {goals?.map(({ goal, progress }) => (
          <li key={goal._id} className="border p-4">
            <div className="flex items-center justify-between">
              <span className="font-medium">{goal.name}</span>
              <span>
                {formatINR(goal.current_amount_minor)} / {formatINR(goal.target_amount_minor)} (
                {progress.percentage.toFixed(0)}%)
              </span>
            </div>
            <div className="mt-2 h-2 w-full bg-gray-100">
              <div className="h-2 bg-gray-500" style={{ width: `${Math.min(100, progress.percentage)}%` }} />
            </div>
            {progress.on_track && <p className="mt-1 text-sm">{progress.on_track}</p>}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const form = new FormData(e.currentTarget);
                const amount = parseFloat(String(form.get("amount") ?? "0"));
                if (amount > 0) contribute.mutate({ id: goal._id, amountMinor: Math.round(amount * 100) });
                e.currentTarget.reset();
              }}
              className="mt-2 flex gap-2"
            >
              <input name="amount" type="number" placeholder="₹ contribution" className="border p-1" />
              <button type="submit" className="border p-1 text-sm">
                Contribute
              </button>
            </form>
          </li>
        ))}
      </ul>
    </div>
  );
}
