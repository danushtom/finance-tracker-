"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api-client";
import { formatINR } from "@/lib/format";
import type { Investment } from "@/types/api";

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

  if (isLoading) return <p>Loading…</p>;

  return (
    <div className="flex flex-col gap-8">
      <h1 className="text-xl font-semibold">Investments</h1>

      {data && (
        <section className="border p-4">
          <p className="text-sm text-gray-500">Current stage</p>
          <p className="font-medium">{data.stage.replace(/_/g, " ")}</p>
          <p className="mt-1 text-sm">{data.stage_guidance}</p>
          <p className="mt-2 text-xs text-gray-500">
            General information only — never a recommendation to buy a specific fund or stock.
          </p>
        </section>
      )}

      <section className="flex gap-8">
        <div>
          <p className="text-sm text-gray-500">Total invested</p>
          <p>{formatINR(data?.total_invested_minor ?? 0)}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Current value</p>
          <p>{formatINR(data?.total_current_value_minor ?? 0)}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Gain / loss</p>
          <p>{formatINR(data?.gain_loss_minor ?? 0)}</p>
        </div>
      </section>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (name && investedRupees && currentRupees) createInvestment.mutate();
        }}
        className="flex flex-wrap items-end gap-2 border p-4"
      >
        <label className="flex flex-col gap-1">
          <span className="text-sm">Name</span>
          <input value={name} onChange={(e) => setName(e.target.value)} className="border p-1" />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm">Type</span>
          <select value={type} onChange={(e) => setType(e.target.value)} className="border p-1">
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
        <label className="flex flex-col gap-1">
          <span className="text-sm">Invested (₹)</span>
          <input
            type="number"
            value={investedRupees}
            onChange={(e) => setInvestedRupees(e.target.value)}
            className="border p-1"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm">Current value (₹)</span>
          <input
            type="number"
            value={currentRupees}
            onChange={(e) => setCurrentRupees(e.target.value)}
            className="border p-1"
          />
        </label>
        <button type="submit" className="border p-2">
          Add holding
        </button>
      </form>

      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b text-left">
            <th className="p-2">Name</th>
            <th className="p-2">Type</th>
            <th className="p-2">Invested</th>
            <th className="p-2">Current value</th>
          </tr>
        </thead>
        <tbody>
          {data?.investments.map((inv) => (
            <tr key={inv._id} className="border-b">
              <td className="p-2">{inv.name}</td>
              <td className="p-2">{inv.type}</td>
              <td className="p-2">{formatINR(inv.invested_minor)}</td>
              <td className="p-2">{formatINR(inv.current_value_minor)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
