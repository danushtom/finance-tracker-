"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { UserSettingsOut } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Settings2, DownloadCloud, BrainCircuit, ShieldAlert, AlertCircle, Save } from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export default function SettingsPage() {
  const { logout, refreshUser } = useAuth();
  const queryClient = useQueryClient();
  const router = useRouter();

  const { data: settings, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.get<UserSettingsOut>("/settings"),
  });

  const [bufferRupees, setBufferRupees] = useState("");
  const [savingsRupees, setSavingsRupees] = useState("");
  const [investmentRupees, setInvestmentRupees] = useState("");
  const [threshold, setThreshold] = useState("70");
  const [investPct, setInvestPct] = useState(50);
  const [goalsPct, setGoalsPct] = useState(30);
  const [discretionaryPct, setDiscretionaryPct] = useState(20);
  const [currency, setCurrency] = useState("INR");

  const [llmProvider, setLlmProvider] = useState<"gemini" | "claude" | "none">("gemini");
  const [geminiKey, setGeminiKey] = useState("");
  const [claudeKey, setClaudeKey] = useState("");

  useEffect(() => {
    if (!settings) return;
    setBufferRupees(String(settings.buffer_minor / 100));
    setSavingsRupees(String(settings.monthly_savings_target_minor / 100));
    setInvestmentRupees(String(settings.monthly_investment_target_minor / 100));
    setThreshold(String(settings.low_confidence_threshold));
    setInvestPct(settings.variable_split.invest_pct);
    setGoalsPct(settings.variable_split.goals_pct);
    setDiscretionaryPct(settings.variable_split.discretionary_pct);
    setLlmProvider(settings.llm.provider);
    setCurrency(settings.currency || "INR");
  }, [settings]);

  const saveGeneral = useMutation({
    mutationFn: () =>
      api.patch("/settings", {
        buffer_minor: Math.round(parseFloat(bufferRupees) * 100),
        monthly_savings_target_minor: Math.round(parseFloat(savingsRupees) * 100),
        monthly_investment_target_minor: Math.round(parseFloat(investmentRupees) * 100),
        low_confidence_threshold: parseInt(threshold, 10),
        variable_split: { invest_pct: investPct, goals_pct: goalsPct, discretionary_pct: discretionaryPct },
        currency,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["settings"] });
      void refreshUser();
    },
  });

  const saveLlm = useMutation({
    mutationFn: () =>
      api.patch("/settings", {
        llm: {
          provider: llmProvider,
          ...(geminiKey ? { gemini_api_key: geminiKey } : {}),
          ...(claudeKey ? { claude_api_key: claudeKey } : {}),
        },
      }),
    onSuccess: () => {
      setGeminiKey("");
      setClaudeKey("");
      void queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
  });

  const splitSum = investPct + goalsPct + discretionaryPct;

  if (isLoading || !settings) return (
    <div className="flex items-center justify-center h-64">
      <div className="text-gray-500 animate-pulse text-lg font-medium">Loading settings...</div>
    </div>
  );

  return (
    <div className="flex flex-col gap-6 font-sans max-w-4xl">
      
      {/* LLM Settings */}
      <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white">
        <CardHeader className="px-6 pt-6 pb-2">
          <CardTitle className="text-lg font-bold flex items-center gap-2">
            <BrainCircuit className="h-5 w-5 text-purple-500" /> Categorisation Engine
          </CardTitle>
          <CardDescription className="text-sm text-gray-500 mt-1">
            Choose which AI model classifies unknown merchants, or turn it off entirely to run on rules only.
            Only the normalised merchant name is ever sent — never amounts, account numbers, or your identity.
          </CardDescription>
        </CardHeader>
        <CardContent className="px-6 pb-6 pt-4 flex flex-col gap-5">
          <label className="flex flex-col gap-1.5 max-w-md">
            <span className="text-sm font-medium text-gray-700">Provider</span>
            <select
              value={llmProvider}
              onChange={(e) => setLlmProvider(e.target.value as typeof llmProvider)}
              className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="gemini">Google Gemini</option>
              <option value="claude">Anthropic Claude</option>
              <option value="none">Off (rules only)</option>
            </select>
          </label>
          
          {llmProvider === "gemini" && (
            <label className="flex flex-col gap-1.5 max-w-md">
              <span className="text-sm font-medium text-gray-700 flex justify-between">
                Gemini API Key
                {settings.llm.gemini_api_key_set && (
                  <span className="text-green-600 text-xs bg-green-50 px-2 py-0.5 rounded-full border border-green-100">Set: {settings.llm.gemini_api_key_masked}</span>
                )}
              </span>
              <input
                type="password"
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                placeholder={settings.llm.gemini_api_key_set ? "Leave blank to keep current key" : "Enter your Gemini API key"}
                className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </label>
          )}
          
          {llmProvider === "claude" && (
            <label className="flex flex-col gap-1.5 max-w-md">
              <span className="text-sm font-medium text-gray-700 flex justify-between">
                Claude API Key
                {settings.llm.claude_api_key_set && (
                  <span className="text-green-600 text-xs bg-green-50 px-2 py-0.5 rounded-full border border-green-100">Set: {settings.llm.claude_api_key_masked}</span>
                )}
              </span>
              <input
                type="password"
                value={claudeKey}
                onChange={(e) => setClaudeKey(e.target.value)}
                placeholder={settings.llm.claude_api_key_set ? "Leave blank to keep current key" : "Enter your Claude API key"}
                className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </label>
          )}
          
          <Button onClick={() => saveLlm.mutate()} disabled={saveLlm.isPending} className="w-fit rounded-full bg-purple-600 text-white hover:bg-purple-700 px-6 shadow-sm mt-2">
            <Save className="h-4 w-4 mr-2" /> Save AI settings
          </Button>
        </CardContent>
      </Card>

      {/* General Settings */}
      <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white">
        <CardHeader className="px-6 pt-6 pb-2">
          <CardTitle className="text-lg font-bold flex items-center gap-2">
            <Settings2 className="h-5 w-5 text-blue-500" /> Safe-to-Spend Rules
          </CardTitle>
          <CardDescription className="text-sm text-gray-500 mt-1">
            Configure your financial goals and automatic budgeting thresholds.
          </CardDescription>
        </CardHeader>
        <CardContent className="px-6 pb-6 pt-4 flex flex-col gap-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-gray-700">Currency</span>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="INR">Indian Rupee (INR)</option>
                <option value="USD">US Dollar (USD)</option>
              </select>
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-gray-700">Buffer (minor units)</span>
              <input 
                type="number"
                value={bufferRupees} 
                onChange={(e) => setBufferRupees(e.target.value)} 
                className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" 
              />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-gray-700">Low-confidence review threshold (0-100)</span>
              <input 
                type="number"
                value={threshold} 
                onChange={(e) => setThreshold(e.target.value)} 
                className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" 
              />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-gray-700">Monthly savings target (minor units)</span>
              <input 
                type="number"
                value={savingsRupees} 
                onChange={(e) => setSavingsRupees(e.target.value)} 
                className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" 
              />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-gray-700">Monthly investment target (minor units)</span>
              <input
                type="number"
                value={investmentRupees}
                onChange={(e) => setInvestmentRupees(e.target.value)}
                className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </label>
          </div>

          <div className="border-t border-gray-100 pt-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-gray-900">Variable-income split</h3>
              <span className={`text-sm font-bold px-2 py-0.5 rounded-full ${splitSum === 100 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                {splitSum}% / 100%
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <label className="flex flex-col gap-1.5">
                <span className="text-sm font-medium text-gray-700">Invest %</span>
                <input
                  type="number"
                  value={investPct}
                  onChange={(e) => setInvestPct(Number(e.target.value))}
                  className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="text-sm font-medium text-gray-700">Goals %</span>
                <input
                  type="number"
                  value={goalsPct}
                  onChange={(e) => setGoalsPct(Number(e.target.value))}
                  className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="text-sm font-medium text-gray-700">Discretionary %</span>
                <input
                  type="number"
                  value={discretionaryPct}
                  onChange={(e) => setDiscretionaryPct(Number(e.target.value))}
                  className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </label>
            </div>
            
            {splitSum !== 100 && (
              <p className="text-sm text-red-500 mt-2 flex items-center gap-1">
                <AlertCircle className="h-4 w-4" /> The split must sum to exactly 100.
              </p>
            )}
          </div>

          <Button 
            onClick={() => saveGeneral.mutate()} 
            disabled={splitSum !== 100 || saveGeneral.isPending} 
            className="w-fit rounded-full bg-blue-600 text-white hover:bg-blue-700 px-6 shadow-sm"
          >
            <Save className="h-4 w-4 mr-2" /> Save Rules
          </Button>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Export Data */}
        <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white">
          <CardHeader className="px-6 pt-6 pb-2">
            <CardTitle className="text-lg font-bold flex items-center gap-2">
              <DownloadCloud className="h-5 w-5 text-gray-400" /> Export Data
            </CardTitle>
          </CardHeader>
          <CardContent className="px-6 pb-6 pt-4 flex flex-col gap-3">
            <Button asChild variant="outline" className="w-full justify-start h-11 rounded-xl border-gray-200">
              <a href={`${API_BASE_URL}/export/transactions.csv`}>
                Export transactions (CSV)
              </a>
            </Button>
            <Button asChild variant="outline" className="w-full justify-start h-11 rounded-xl border-gray-200">
              <a href={`${API_BASE_URL}/export/all.json`}>
                Export all data (JSON)
              </a>
            </Button>
          </CardContent>
        </Card>

        {/* Danger Zone */}
        <Card className="rounded-3xl border border-red-100 shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-red-50/30">
          <CardHeader className="px-6 pt-6 pb-2">
            <CardTitle className="text-lg font-bold flex items-center gap-2 text-red-700">
              <ShieldAlert className="h-5 w-5 text-red-500" /> Danger Zone
            </CardTitle>
          </CardHeader>
          <CardContent className="px-6 pb-6 pt-4 flex flex-col justify-between h-full">
            <p className="text-sm text-red-800/70 mb-4 leading-relaxed">
              Permanently delete your account and all associated data. This action cannot be undone.
            </p>
            <Button
              onClick={async () => {
                if (!confirm("This permanently deletes your account and all data. Continue?")) return;
                await apiFetch("/auth/me", { method: "DELETE" });
                await logout();
                router.replace("/login");
              }}
              variant="destructive"
              className="w-full rounded-xl bg-red-600 hover:bg-red-700 text-white h-11 font-medium"
            >
              Delete Account
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
