"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { api, apiFetch } from "@/lib/api-client";
import type { Account, ImportRecord } from "@/types/api";

export default function ImportPage() {
  const queryClient = useQueryClient();
  const fileInput = useRef<HTMLInputElement>(null);
  const [accountId, setAccountId] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const { data: accounts } = useQuery({
    queryKey: ["accounts"],
    queryFn: () => api.get<Account[]>("/accounts"),
  });

  const { data: imports } = useQuery({
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
      setMessage("Import queued.");
      void queryClient.invalidateQueries({ queryKey: ["imports"] });
    },
    onError: (err: unknown) => {
      setMessage(err instanceof Error ? err.message : "Upload failed");
    },
  });

  return (
    <div className="flex flex-col gap-8">
      <h1 className="text-xl font-semibold">Import a statement</h1>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void upload.mutate();
        }}
        className="flex flex-col gap-3 border p-4"
      >
        <label className="flex flex-col gap-1">
          <span>Account</span>
          <select value={accountId} onChange={(e) => setAccountId(e.target.value)} className="border p-2">
            <option value="">Select account…</option>
            {accounts?.map((a) => (
              <option key={a._id} value={a._id}>
                {a.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span>Statement file (CSV, XLS/XLSX, PDF)</span>
          <input ref={fileInput} type="file" accept=".csv,.xls,.xlsx,.pdf" className="border p-2" />
        </label>
        <label className="flex flex-col gap-1">
          <span>PDF password (if protected, used once and never stored)</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="border p-2"
          />
        </label>
        <button type="submit" disabled={upload.isPending} className="border p-2">
          {upload.isPending ? "Uploading…" : "Upload"}
        </button>
        {message && <p className="text-sm">{message}</p>}
      </form>

      <section>
        <h2 className="mb-2 font-semibold">Import history</h2>
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b text-left">
              <th className="p-2">File</th>
              <th className="p-2">Status</th>
              <th className="p-2">Imported</th>
              <th className="p-2">Duplicates</th>
              <th className="p-2">Needs review</th>
            </tr>
          </thead>
          <tbody>
            {imports?.map((i) => (
              <tr key={i._id} className="border-b">
                <td className="p-2">{i.filename}</td>
                <td className="p-2">{i.status}</td>
                <td className="p-2">{i.summary.imported}</td>
                <td className="p-2">{i.summary.duplicates_skipped}</td>
                <td className="p-2">{i.summary.needs_review_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
