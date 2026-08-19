"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth-context";
import { useState } from "react";
import { api } from "@/lib/api-client";
import { formatCurrency } from "@/lib/format";
import type { Investment } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { TrendingUp, PieChart, Activity, PlusCircle, AlertCircle } from "lucide-react";

interface InvestmentsResponse {
  investments: Investment[];
  allocation_by_type: Record<string, number>;
  total_invested_minor: number;
  total_current_value_minor: number;
  gain_loss_minor: number;
  stage: string;
  stage_guidance: string;
}

export default function InvestmentsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [type, setType] = useState("index_fund");
  const [investedRupees, setInvestedRupees] = useState("");
  const [currentRupees, setCurrentRupees] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["investments"],
    queryFn: () => api.get<InvestmentsResponse>("/investments"),
  });

  const createInvestment = useMutation({
    mutationFn: () =>
      api.post("/investments", {
        name,
        type,
        invested_minor: Math.round(parseFloat(investedRupees) * 100),
        current_value_minor: Math.round(parseFloat(currentRupees) * 100),
      }),
    onSuccess: () => {
      setName("");
      setInvestedRupees("");
      setCurrentRupees("");
      void queryClient.invalidateQueries({ queryKey: ["investments"] });
    },
  });

  if (isLoading) return (
    <div className="flex items-center justify-center h-64">
      <div className="text-gray-500 animate-pulse text-lg font-medium">Loading investments...</div>
    </div>
  );

  return (
    <div className="flex flex-col gap-6 font-sans">
      
      {data && (
        <>
          <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-gradient-to-br from-indigo-50 to-purple-50 border border-indigo-100/50">
            <CardContent className="p-6">
              <div className="flex gap-4">
                <div className="flex-shrink-0 mt-1">
                  <div className="p-2 bg-indigo-100 rounded-full text-indigo-600">
                    <Activity className="h-5 w-5" />
                  </div>
                </div>
                <div>
                  <h3 className="font-bold text-gray-900 mb-1 capitalize text-lg">{data.stage.replace(/_/g, " ")}</h3>
                  <p className="text-gray-700 leading-relaxed mb-3">{data.stage_guidance}</p>
                  <p className="text-xs text-indigo-600/80 font-medium flex items-center gap-1.5">
                    <AlertCircle className="h-3 w-3" /> General information only — not financial advice.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white">
              <CardContent className="p-6">
                <div className="flex items-center gap-3 mb-2 text-gray-500">
                  <div className="p-2 bg-gray-50 rounded-full">
                    <PieChart className="h-4 w-4" />
                  </div>
                  <h3 className="font-medium text-sm">Total Invested</h3>
                </div>
                <p className="text-2xl font-bold text-gray-900">{formatCurrency(data.total_invested_minor, user?.settings?.currency)}</p>
              </CardContent>
            </Card>

            <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white">
              <CardContent className="p-6">
                <div className="flex items-center gap-3 mb-2 text-blue-600">
                  <div className="p-2 bg-blue-50 rounded-full">
                    <TrendingUp className="h-4 w-4" />
                  </div>
                  <h3 className="font-medium text-sm">Current Value</h3>
                </div>
                <p className="text-2xl font-bold text-gray-900">{formatCurrency(data.total_current_value_minor, user?.settings?.currency)}</p>
              </CardContent>
            </Card>

            <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white">
              <CardContent className="p-6">
                <div className={`flex items-center gap-3 mb-2 ${data.gain_loss_minor >= 0 ? "text-green-600" : "text-red-600"}`}>
                  <div className={`p-2 rounded-full ${data.gain_loss_minor >= 0 ? "bg-green-50" : "bg-red-50"}`}>
                    <TrendingUp className={`h-4 w-4 ${data.gain_loss_minor < 0 && "rotate-180"}`} />
                  </div>
                  <h3 className="font-medium text-sm">Gain / Loss</h3>
                </div>
                <p className={`text-2xl font-bold ${data.gain_loss_minor >= 0 ? "text-green-600" : "text-red-600"}`}>
                  {data.gain_loss_minor > 0 ? "+" : ""}{formatCurrency(data.gain_loss_minor, user?.settings?.currency)}
                </p>
              </CardContent>
            </Card>
          </div>
        </>
      )}

      <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white">
        <CardHeader className="px-6 pt-6 pb-2">
          <CardTitle className="text-lg font-bold flex items-center gap-2">
            <PlusCircle className="h-5 w-5 text-gray-400" /> Add Holding
          </CardTitle>
        </CardHeader>
        <CardContent className="px-6 pb-6 pt-2">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (name && investedRupees && currentRupees) createInvestment.mutate();
            }}
            className="flex flex-wrap items-end gap-4"
          >
            <label className="flex flex-col gap-1.5 flex-[1.5] min-w-[200px]">
              <span className="text-sm font-medium text-gray-700">Name</span>
              <input 
                value={name} 
                onChange={(e) => setName(e.target.value)} 
                placeholder="e.g. S&P 500 ETF"
                className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900" 
              />
            </label>
            <label className="flex flex-col gap-1.5 flex-1 min-w-[150px]">
              <span className="text-sm font-medium text-gray-700">Type</span>
              <select 
                value={type} 
                onChange={(e) => setType(e.target.value)} 
                className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
              >
                <option value="index_fund">Index fund</option>
                <option value="active_fund">Active fund</option>
                <option value="debt">Debt</option>
                <option value="stock">Stock</option>
                <option value="gold">Gold</option>
                <option value="fd">Fixed deposit</option>
                <option value="epf_ppf">EPF/PPF</option>
                <option value="other">Other</option>
              </select>
            </label>
            <label className="flex flex-col gap-1.5 flex-1 min-w-[150px]">
              <span className="text-sm font-medium text-gray-700">Invested </span>
              <input
                type="number"
                value={investedRupees}
                onChange={(e) => setInvestedRupees(e.target.value)}
                placeholder="0"
                className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
              />
            </label>
            <label className="flex flex-col gap-1.5 flex-1 min-w-[150px]">
              <span className="text-sm font-medium text-gray-700">Current value </span>
              <input
                type="number"
                value={currentRupees}
                onChange={(e) => setCurrentRupees(e.target.value)}
                placeholder="0"
                className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
              />
            </label>
            <Button type="submit" disabled={!name || !investedRupees || !currentRupees} className="rounded-full bg-gray-900 text-white hover:bg-gray-800 px-6 shadow-sm">
              Add holding
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
                  <th className="p-4 px-6 font-medium">Name</th>
                  <th className="p-4 px-6 font-medium">Type</th>
                  <th className="p-4 px-6 font-medium text-right">Invested</th>
                  <th className="p-4 px-6 font-medium text-right">Current value</th>
                </tr>
              </thead>
              <tbody>
                {data?.investments.map((inv) => (
                  <tr key={inv._id} className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
                    <td className="p-4 px-6 font-medium text-gray-900">{inv.name}</td>
                    <td className="p-4 px-6 text-gray-500 capitalize">{inv.type.replace(/_/g, ' ')}</td>
                    <td className="p-4 px-6 text-right font-medium text-gray-600">{formatCurrency(inv.invested_minor, user?.settings?.currency)}</td>
                    <td className="p-4 px-6 text-right font-semibold text-gray-900">{formatCurrency(inv.current_value_minor, user?.settings?.currency)}</td>
                  </tr>
                ))}
                {data?.investments.length === 0 && (
                  <tr>
                    <td colSpan={4} className="p-8 text-center text-gray-500">No holdings found. Add one above!</td>
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
