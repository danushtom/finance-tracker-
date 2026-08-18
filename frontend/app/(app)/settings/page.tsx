"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { UserSettingsOut } from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export default function SettingsPage() {
  const { logout } = useAuth();
  const queryClient = useQueryClient();

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
  }, [settings]);

  const saveGeneral = useMutation({
    mutationFn: () =>
      api.patch("/settings", {
        buffer_minor: Math.round(parseFloat(bufferRupees) * 100),
        monthly_savings_target_minor: Math.round(parseFloat(savingsRupees) * 100),
        monthly_investment_target_minor: Math.round(parseFloat(investmentRupees) * 100),
        low_confidence_threshold: parseInt(threshold, 10),
        variable_split: { invest_pct: investPct, goals_pct: goalsPct, discretionary_pct: discretionaryPct },
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["settings"] }),
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

  if (isLoading || !settings) return <p>Loading…</p>;

  return (
    <div className="flex flex-col gap-10">
      <h1 className="text-xl font-semibold">Settings</h1>

      <section className="flex flex-col gap-3 border p-4">
        <h2 className="font-semibold">Categorisation — LLM provider</h2>
        <p className="text-sm text-gray-500">
          Choose which model classifies unknown merchants, or turn it off entirely to run on rules only
          (FR-4.12, NFR-11). Only the normalised merchant name is ever sent — never amounts, account
          numbers, or your identity (NFR-10).
        </p>
        <label className="flex flex-col gap-1">
          <span className="text-sm">Provider</span>
          <select
            value={llmProvider}
            onChange={(e) => setLlmProvider(e.target.value as typeof llmProvider)}
            className="border p-1"
          >
            <option value="gemini">Gemini</option>
            <option value="claude">Claude</option>
            <option value="none">Off (rules only)</option>
          </select>
        </label>
        {llmProvider === "gemini" && (
          <label className="flex flex-col gap-1">
            <span className="text-sm">
              Gemini API key {settings.llm.gemini_api_key_set && `(currently set: ${settings.llm.gemini_api_key_masked})`}
            </span>
            <input
              type="password"
              value={geminiKey}
              onChange={(e) => setGeminiKey(e.target.value)}
              placeholder={settings.llm.gemini_api_key_set ? "Leave blank to keep current key" : "Enter your Gemini API key"}
              className="border p-1"
            />
          </label>
        )}
        {llmProvider === "claude" && (
          <label className="flex flex-col gap-1">
            <span className="text-sm">
              Claude API key {settings.llm.claude_api_key_set && `(currently set: ${settings.llm.claude_api_key_masked})`}
            </span>
            <input
              type="password"
              value={claudeKey}
              onChange={(e) => setClaudeKey(e.target.value)}
              placeholder={settings.llm.claude_api_key_set ? "Leave blank to keep current key" : "Enter your Claude API key"}
              className="border p-1"
            />
          </label>
        )}
        <button onClick={() => saveLlm.mutate()} className="w-fit border p-2">
          Save LLM settings
        </button>
      </section>

      <section className="flex flex-col gap-3 border p-4">
        <h2 className="font-semibold">Safe-to-Spend rules</h2>
        <label className="flex flex-col gap-1">
          <span className="text-sm">Buffer (₹)</span>
          <input value={bufferRupees} onChange={(e) => setBufferRupees(e.target.value)} className="border p-1" />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm">Monthly savings target (₹)</span>
          <input value={savingsRupees} onChange={(e) => setSavingsRupees(e.target.value)} className="border p-1" />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm">Monthly investment target (₹)</span>
          <input
            value={investmentRupees}
            onChange={(e) => setInvestmentRupees(e.target.value)}
            className="border p-1"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm">Low-confidence review threshold (0-100)</span>
          <input value={threshold} onChange={(e) => setThreshold(e.target.value)} className="border p-1" />
        </label>

        <p className="text-sm text-gray-500 mt-2">
          Variable-income split — must sum to 100 (currently {splitSum})
        </p>
        <div className="flex gap-4">
          <label className="flex flex-col gap-1">
            <span className="text-sm">Invest %</span>
            <input
              type="number"
              value={investPct}
              onChange={(e) => setInvestPct(Number(e.target.value))}
              className="border p-1"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-sm">Goals %</span>
            <input
              type="number"
              value={goalsPct}
              onChange={(e) => setGoalsPct(Number(e.target.value))}
              className="border p-1"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-sm">Discretionary %</span>
            <input
              type="number"
              value={discretionaryPct}
              onChange={(e) => setDiscretionaryPct(Number(e.target.value))}
              className="border p-1"
            />
          </label>
        </div>

        <button onClick={() => saveGeneral.mutate()} disabled={splitSum !== 100} className="w-fit border p-2">
          Save
        </button>
      </section>

      <section className="flex flex-col gap-2 border p-4">
        <h2 className="font-semibold">Data</h2>
        <a href={`${API_BASE_URL}/export/transactions.csv`} className="w-fit underline">
          Export transactions (CSV)
        </a>
        <a href={`${API_BASE_URL}/export/all.json`} className="w-fit underline">
          Export all data (JSON)
        </a>
      </section>

      <section className="flex flex-col gap-2 border p-4">
        <h2 className="font-semibold">Account</h2>
        <button
          onClick={async () => {
            if (!confirm("This permanently deletes your account and all data. Continue?")) return;
            await apiFetch("/auth/me", { method: "DELETE" });
            await logout();
            window.location.href = "/login";
          }}
          className="w-fit border p-2 text-red-600"
        >
          Delete account
        </button>
      </section>
    </div>
  );
}
