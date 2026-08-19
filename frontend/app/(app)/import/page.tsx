"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { api, apiFetch } from "@/lib/api-client";
import type { Account, ImportRecord } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { UploadCloud, History, CheckCircle2, AlertTriangle, Loader2 } from "lucide-react";

export default function ImportPage() {
  const queryClient = useQueryClient();
  const fileInput = useRef<HTMLInputElement>(null);
  const [accountId, setAccountId] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

  const { data: accounts } = useQuery({
    queryKey: ["accounts"],
    queryFn: () => api.get<Account[]>("/accounts"),
  });

  const { data: imports, isLoading: isImportsLoading } = useQuery({
    queryKey: ["imports"],
    queryFn: () => api.get<ImportRecord[]>("/imports"),
    refetchInterval: 3000, // poll job status (FR-2.5)
  });

  const upload = useMutation({
    mutationFn: async () => {
      const file = fileInput.current?.files?.[0];
      if (!file || !accountId) throw new Error("Choose a file and an account");
      const form = new FormData();
      form.append("file", file);
      form.append("account_id", accountId);
      if (password) form.append("password", password);
      return apiFetch<{ import_id: string }>("/imports", { method: "POST", body: form });
    },
    onSuccess: () => {
      setMessage({ text: "Import queued successfully.", type: "success" });
      if (fileInput.current) fileInput.current.value = "";
      setPassword("");
      void queryClient.invalidateQueries({ queryKey: ["imports"] });
    },
    onError: (err: unknown) => {
      setMessage({ text: err instanceof Error ? err.message : "Upload failed", type: "error" });
    },
  });

  return (
    <div className="flex flex-col gap-6 font-sans">
      <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white max-w-3xl">
        <CardHeader className="px-6 pt-6 pb-2">
          <CardTitle className="text-lg font-bold flex items-center gap-2">
            <UploadCloud className="h-5 w-5 text-gray-400" /> Upload Statement
          </CardTitle>
        </CardHeader>
        <CardContent className="px-6 pb-6 pt-2">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void upload.mutate();
            }}
            className="flex flex-col gap-5"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <label className="flex flex-col gap-1.5">
                <span className="text-sm font-medium text-gray-700">Account</span>
                <select 
                  value={accountId} 
                  onChange={(e) => setAccountId(e.target.value)} 
                  className="rounded-lg border border-gray-200 bg-transparent px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
                >
                  <option value="">Select account…</option>
                  {accounts?.map((a) => (
                    <option key={a._id} value={a._id}>
                      {a.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="flex flex-col gap-1.5">
                <span className="text-sm font-medium text-gray-700">Statement file <span className="text-gray-400 font-normal">(CSV, XLS/XLSX, PDF)</span></span>
                <input 
                  ref={fileInput} 
                  type="file" 
                  accept=".csv,.xls,.xlsx,.pdf" 
                  className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 file:mr-4 file:py-1 file:px-3 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-gray-50 file:text-gray-700 hover:file:bg-gray-100" 
                />
              </label>
            </div>

            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-gray-700">PDF password <span className="text-gray-400 font-normal">(if protected, used once and never stored)</span></span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Leave blank if not password protected"
                className="rounded-lg border border-gray-200 bg-transparent px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
              />
            </label>

            <div className="flex items-center justify-between pt-2">
              <Button type="submit" disabled={upload.isPending} className="rounded-full bg-gray-900 text-white hover:bg-gray-800 px-8 shadow-sm">
                {upload.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Uploading...
                  </>
                ) : (
                  "Upload"
                )}
              </Button>
              
              {message && (
                <div className={`flex items-center gap-2 text-sm font-medium ${message.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                  {message.type === 'success' ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
                  {message.text}
                </div>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white overflow-hidden mt-2">
        <CardHeader className="px-6 pt-6 pb-4 border-b border-gray-100">
          <CardTitle className="text-lg font-bold flex items-center gap-2">
            <History className="h-5 w-5 text-gray-400" /> Import History
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isImportsLoading && (
            <div className="p-8 text-center text-gray-500 animate-pulse">Loading import history...</div>
          )}
          
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm text-left">
              <thead className="bg-gray-50/50">
                <tr className="border-b border-gray-100 text-gray-500">
                  <th className="p-4 px-6 font-medium">File</th>
                  <th className="p-4 px-6 font-medium">Status</th>
                  <th className="p-4 px-6 font-medium text-center">Imported</th>
                  <th className="p-4 px-6 font-medium text-center">Duplicates</th>
                  <th className="p-4 px-6 font-medium text-center">Needs Review</th>
                </tr>
              </thead>
              <tbody>
                {imports?.map((i) => (
                  <tr key={i._id} className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
                    <td className="p-4 px-6 font-medium text-gray-900">{i.filename}</td>
                    <td className="p-4 px-6">
                      <span className={`inline-flex items-center justify-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        i.status === 'completed' ? 'bg-green-100 text-green-700' : 
                        i.status === 'failed' ? 'bg-red-100 text-red-700' : 
                        'bg-blue-100 text-blue-700'
                      }`}>
                        {i.status}
                      </span>
                    </td>
                    <td className="p-4 px-6 text-center font-medium text-gray-900">{i.summary.imported}</td>
                    <td className="p-4 px-6 text-center text-gray-500">{i.summary.duplicates_skipped}</td>
                    <td className="p-4 px-6 text-center">
                      {i.summary.needs_review_count > 0 ? (
                        <span className="inline-flex items-center justify-center rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-orange-700">
                          {i.summary.needs_review_count}
                        </span>
                      ) : (
                        <span className="text-gray-400">0</span>
                      )}
                    </td>
                  </tr>
                ))}
                {imports?.length === 0 && !isImportsLoading && (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-gray-500">No imports found yet.</td>
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
