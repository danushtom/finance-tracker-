"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth-context";
import { useState } from "react";
import { api } from "@/lib/api-client";
import { formatCurrency } from "@/lib/format";
import type { GoalWithProgress } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Target, Zap } from "lucide-react";

export default function GoalsPage() {
  const { user } = useAuth();
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
    <div className="flex flex-col gap-6 font-sans">
      
      <div className="flex flex-col sm:flex-row gap-4">
        <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white flex-1">
          <CardHeader className="px-6 pt-6 pb-2">
            <CardTitle className="text-lg font-bold flex items-center gap-2">
              <Target className="h-5 w-5 text-gray-400" /> Create Goal
            </CardTitle>
          </CardHeader>
          <CardContent className="px-6 pb-6 pt-2">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (name && targetRupees) createGoal.mutate();
              }}
              className="flex flex-wrap items-end gap-4"
            >
              <label className="flex flex-col gap-1.5 flex-[2] min-w-[200px]">
                <span className="text-sm font-medium text-gray-700">Goal name</span>
                <input 
                  value={name} 
                  onChange={(e) => setName(e.target.value)} 
                  placeholder="e.g. New Car"
                  className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900" 
                />
              </label>
              <label className="flex flex-col gap-1.5 flex-1 min-w-[150px]">
                <span className="text-sm font-medium text-gray-700">Target </span>
                <input
                  type="number"
                  value={targetRupees}
                  onChange={(e) => setTargetRupees(e.target.value)}
                  placeholder="500000"
                  className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
                />
              </label>
              <Button type="submit" disabled={!name || !targetRupees} className="rounded-full bg-gray-900 text-white hover:bg-gray-800 px-6 shadow-sm">
                Add goal
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-100/50 flex flex-col justify-center">
          <CardContent className="p-6 text-center h-full flex flex-col justify-center items-center">
            <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center mb-3">
              <Zap className="h-5 w-5 text-blue-600" />
            </div>
            <p className="text-sm text-gray-700 font-medium mb-4 max-w-[200px] leading-relaxed">
              Auto-calculate your 6-month emergency fund
            </p>
            <Button 
              onClick={() => ensureEmergencyFund.mutate()} 
              variant="outline"
              className="rounded-full bg-white border-blue-200 text-blue-700 hover:bg-blue-50 w-full"
            >
              Update Fund
            </Button>
          </CardContent>
        </Card>
      </div>

      {isLoading && (
        <div className="p-8 text-center text-gray-500 animate-pulse">Loading goals...</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {goals?.map(({ goal, progress }) => (
          <Card key={goal._id} className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white overflow-hidden flex flex-col">
            <CardHeader className="px-6 pt-6 pb-2">
              <CardTitle className="text-lg font-bold">{goal.name}</CardTitle>
            </CardHeader>
            <CardContent className="px-6 pb-6 pt-2 flex flex-col flex-1 justify-between gap-6">
              <div>
                <div className="flex items-center justify-between mb-3 text-sm font-medium">
                  <span className="text-gray-500">Progress</span>
                  <span className="text-gray-900 font-bold">
                    {formatCurrency(goal.current_amount_minor, user?.settings?.currency)} <span className="text-gray-400 font-normal">/ {formatCurrency(goal.target_amount_minor, user?.settings?.currency)}</span>
                  </span>
                </div>
                <Progress value={Math.min(100, progress.percentage)} className="h-2.5 mb-2" />
                <div className="flex justify-between items-center text-xs">
                  <span className="text-gray-500">{progress.percentage.toFixed(0)}%</span>
                  {progress.on_track && (
                    <span className="text-blue-600 font-medium">{progress.on_track}</span>
                  )}
                </div>
              </div>

              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const form = new FormData(e.currentTarget);
                  const amount = parseFloat(String(form.get("amount") ?? "0"));
                  if (amount > 0) contribute.mutate({ id: goal._id, amountMinor: Math.round(amount * 100) });
                  e.currentTarget.reset();
                }}
                className="flex gap-2 pt-4 border-t border-gray-100"
              >
                <div className="relative flex-1">
                  {/* removed hardcoded currency */}
                  <input 
                    name="amount" 
                    type="number" 
                    placeholder="Amount" 
                    className="w-full rounded-full border border-gray-200 bg-gray-50 pl-8 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900" 
                  />
                </div>
                <Button type="submit" variant="outline" className="rounded-full border-gray-200 hover:bg-gray-50 px-4">
                  Add
                </Button>
              </form>
            </CardContent>
          </Card>
        ))}
        {goals?.length === 0 && !isLoading && (
          <div className="col-span-full p-12 text-center text-gray-500 bg-gray-50/50 rounded-3xl border border-dashed border-gray-200">
            No goals created yet. Start planning for your future!
          </div>
        )}
      </div>
    </div>
  );
}
