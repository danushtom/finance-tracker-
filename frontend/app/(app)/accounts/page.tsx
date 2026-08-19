"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth-context";
import { useState } from "react";
import { api } from "@/lib/api-client";
import { formatCurrency } from "@/lib/format";
import type { Account, AccountType } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { WalletCards, TrendingUp, TrendingDown, DollarSign } from "lucide-react";

interface NetWorthResponse {
  assets_minor: number;
  liabilities_minor: number;
  net_worth_minor: number;
}

export default function AccountsPage() {
  const { user } = useAuth();
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
    <div className="flex flex-col gap-6 font-sans">
      
      {/* Net Worth Summary */}
      {netWorth && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-100/50">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-2 text-blue-600">
                <div className="p-2 bg-blue-100 rounded-full">
                  <DollarSign className="h-5 w-5" />
                </div>
                <h3 className="font-semibold">Net Worth</h3>
              </div>
              <p className="text-3xl font-bold text-gray-900">{formatCurrency(netWorth.net_worth_minor, user?.settings?.currency)}</p>
            </CardContent>
          </Card>

          <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-gradient-to-br from-green-50 to-emerald-50 border border-green-100/50">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-2 text-green-600">
                <div className="p-2 bg-green-100 rounded-full">
                  <TrendingUp className="h-5 w-5" />
                </div>
                <h3 className="font-semibold">Assets</h3>
              </div>
              <p className="text-2xl font-bold text-gray-900">{formatCurrency(netWorth.assets_minor, user?.settings?.currency)}</p>
            </CardContent>
          </Card>

          <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-gradient-to-br from-red-50 to-rose-50 border border-red-100/50">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-2 text-red-600">
                <div className="p-2 bg-red-100 rounded-full">
                  <TrendingDown className="h-5 w-5" />
                </div>
                <h3 className="font-semibold">Liabilities</h3>
              </div>
              <p className="text-2xl font-bold text-gray-900">{formatCurrency(netWorth.liabilities_minor, user?.settings?.currency)}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Add Account Form */}
      <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white">
        <CardHeader className="px-6 pt-6 pb-2">
          <CardTitle className="text-lg font-bold flex items-center gap-2">
            <WalletCards className="h-5 w-5 text-gray-400" /> Add Account
          </CardTitle>
        </CardHeader>
        <CardContent className="px-6 pb-6 pt-2">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (name) createAccount.mutate();
            }}
            className="flex flex-wrap items-end gap-4"
          >
            <label className="flex flex-col gap-1.5 flex-[2] min-w-[200px]">
              <span className="text-sm font-medium text-gray-700">Name</span>
              <input 
                value={name} 
                onChange={(e) => setName(e.target.value)} 
                placeholder="e.g. Chase Checking"
                className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900" 
              />
            </label>
            <label className="flex flex-col gap-1.5 flex-1 min-w-[150px]">
              <span className="text-sm font-medium text-gray-700">Type</span>
              <select 
                value={type} 
                onChange={(e) => setType(e.target.value as AccountType)} 
                className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
              >
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
            <label className="flex flex-col gap-1.5 flex-1 min-w-[150px]">
              <span className="text-sm font-medium text-gray-700">Current balance </span>
              <input
                type="number"
                value={balanceRupees}
                onChange={(e) => setBalanceRupees(e.target.value)}
                placeholder="10000"
                className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
              />
            </label>
            <Button type="submit" disabled={!name} className="rounded-full bg-gray-900 text-white hover:bg-gray-800 px-6 shadow-sm">
              Add account
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Accounts List */}
      <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white overflow-hidden">
        <CardContent className="p-0">
          {isLoading && (
            <div className="p-8 text-center text-gray-500 animate-pulse">Loading accounts...</div>
          )}
          
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm text-left">
              <thead className="bg-gray-50/50">
                <tr className="border-b border-gray-100 text-gray-500">
                  <th className="p-4 px-6 font-medium">Name</th>
                  <th className="p-4 px-6 font-medium">Type</th>
                  <th className="p-4 px-6 font-medium text-right">Balance</th>
                  <th className="p-4 px-6 font-medium text-center">Status</th>
                  <th className="p-4 px-6 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {accounts?.map((a) => (
                  <tr key={a._id} className={`border-b border-gray-50 transition-colors ${a.archived ? "opacity-60 bg-gray-50/30" : "hover:bg-gray-50/50"}`}>
                    <td className="p-4 px-6 font-medium text-gray-900">{a.name}</td>
                    <td className="p-4 px-6 text-gray-500 capitalize">{a.type.replace('_', ' ')}</td>
                    <td className={`p-4 px-6 text-right font-semibold ${a.current_balance_minor < 0 ? "text-red-600" : "text-gray-900"}`}>
                      {formatCurrency(a.current_balance_minor, user?.settings?.currency)}
                    </td>
                    <td className="p-4 px-6 text-center">
                      <span className={`inline-flex items-center justify-center rounded-full px-2.5 py-0.5 text-xs font-medium ${a.archived ? 'bg-gray-100 text-gray-600' : 'bg-green-100 text-green-700'}`}>
                        {a.archived ? "Archived" : "Active"}
                      </span>
                    </td>
                    <td className="p-4 px-6 text-right">
                      {!a.archived && (
                        <button onClick={() => archiveAccount.mutate(a._id)} className="text-gray-400 hover:text-gray-900 text-sm font-medium transition-colors">
                          Archive
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {accounts?.length === 0 && !isLoading && (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-gray-500">No accounts found.</td>
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
