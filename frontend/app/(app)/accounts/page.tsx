"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api-client";
import { formatINR } from "@/lib/format";
import type { Account, AccountType } from "@/types/api";

interface NetWorthResponse {
  assets_minor: number;
  liabilities_minor: number;
  net_worth_minor: number;
}

export default function AccountsPage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [type, setType] = useState<AccountType>("bank");
  const [balanceRupees, setBalanceRupees] = useState("");

  const { data: accounts, isLoading } = useQuery({
    queryKey: ["accounts", { includeArchived: true }],
    queryFn: () => api.get<Account[]>("/accounts?include_archived=true"),
  });

  const { data: netWorth } = useQuery({
    queryKey: ["net-worth"],
    queryFn: () => api.get<NetWorthResponse>("/net-worth"),
  });

  const createAccount = useMutation({
    mutationFn: () =>
      api.post("/accounts", {
        name,
        type,
        current_balance_minor: Math.round((parseFloat(balanceRupees) || 0) * 100),
      }),
    onSuccess: () => {
      setName("");
      setBalanceRupees("");
      void queryClient.invalidateQueries({ queryKey: ["accounts"] });
      void queryClient.invalidateQueries({ queryKey: ["net-worth"] });
    },
  });

  const archiveAccount = useMutation({
    mutationFn: (id: string) => api.delete(`/accounts/${id}`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["accounts"] }),
  });

  return (
    <div className="flex flex-col gap-8">
      <h1 className="text-xl font-semibold">Accounts</h1>

      {netWorth && (
        <section className="flex gap-8">
          <div>
            <p className="text-sm text-gray-500">Assets</p>
            <p>{formatINR(netWorth.assets_minor)}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Liabilities</p>
            <p>{formatINR(netWorth.liabilities_minor)}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Net worth</p>
            <p>{formatINR(netWorth.net_worth_minor)}</p>
          </div>
        </section>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (name) createAccount.mutate();
        }}
        className="flex flex-wrap items-end gap-2 border p-4"
      >
        <label className="flex flex-col gap-1">
          <span className="text-sm">Name</span>
          <input value={name} onChange={(e) => setName(e.target.value)} className="border p-1" />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm">Type</span>
          <select value={type} onChange={(e) => setType(e.target.value as AccountType)} className="border p-1">
            <option value="bank">Bank</option>
            <option value="cash">Cash</option>
            <option value="credit_card">Credit card</option>
            <option value="brokerage">Brokerage</option>
            <option value="mf_folio">MF folio</option>
            <option value="ppf_epf">PPF/EPF</option>
            <option value="asset">Other asset</option>
            <option value="liability">Other liability</option>
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm">Current balance (₹)</span>
          <input
            type="number"
            value={balanceRupees}
            onChange={(e) => setBalanceRupees(e.target.value)}
            className="border p-1"
          />
        </label>
        <button type="submit" className="border p-2">
          Add account
        </button>
      </form>

      {isLoading && <p>Loading…</p>}

      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b text-left">
            <th className="p-2">Name</th>
            <th className="p-2">Type</th>
            <th className="p-2">Balance</th>
            <th className="p-2">Status</th>
            <th className="p-2"></th>
          </tr>
        </thead>
        <tbody>
          {accounts?.map((a) => (
            <tr key={a._id} className="border-b">
              <td className="p-2">{a.name}</td>
              <td className="p-2">{a.type}</td>
              <td className="p-2">{formatINR(a.current_balance_minor)}</td>
              <td className="p-2">{a.archived ? "Archived" : "Active"}</td>
              <td className="p-2">
                {!a.archived && (
                  <button onClick={() => archiveAccount.mutate(a._id)} className="underline">
                    Archive
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
