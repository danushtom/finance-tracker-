"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api-client";
import { formatINR } from "@/lib/format";
import type { WishlistVerdict } from "@/types/api";

export default function WishlistPage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [priceRupees, setPriceRupees] = useState("");
  const [priority, setPriority] = useState("medium");

  const { data: items, isLoading } = useQuery({
    queryKey: ["wishlist"],
    queryFn: () => api.get<WishlistVerdict[]>("/wishlist"),
  });

  const createItem = useMutation({
    mutationFn: () =>
      api.post("/wishlist", {
        name,
        price_minor: Math.round(parseFloat(priceRupees) * 100),
        priority,
      }),
    onSuccess: () => {
      setName("");
      setPriceRupees("");
      void queryClient.invalidateQueries({ queryKey: ["wishlist"] });
    },
  });

  const promote = useMutation({
    mutationFn: (id: string) => api.post(`/wishlist/${id}/promote`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["wishlist"] }),
  });

  return (
    <div className="flex flex-col gap-8">
      <h1 className="text-xl font-semibold">Things I want</h1>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (name && priceRupees) createItem.mutate();
        }}
        className="flex flex-wrap items-end gap-2 border p-4"
      >
        <label className="flex flex-col gap-1">
          <span className="text-sm">Item</span>
          <input value={name} onChange={(e) => setName(e.target.value)} className="border p-1" />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm">Price (₹)</span>
          <input
            type="number"
            value={priceRupees}
            onChange={(e) => setPriceRupees(e.target.value)}
            className="border p-1"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm">Priority</span>
          <select value={priority} onChange={(e) => setPriority(e.target.value)} className="border p-1">
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </label>
        <button type="submit" className="border p-2">
          Add
        </button>
      </form>

      {isLoading && <p>Loading…</p>}

      <ul className="flex flex-col gap-3">
        {items?.map((item) => (
          <li key={item.item_id} className="border p-4">
            <div className="flex items-center justify-between">
              <span className="font-medium">
                {item.name} ({item.priority})
              </span>
              <span>{formatINR(item.price_minor)}</span>
            </div>
            <p className="mt-1 text-sm">
              {item.affordable ? (
                <>✅ Yes — {formatINR(item.remaining_after_purchase_minor ?? 0)} remaining after purchase</>
              ) : (
                <>
                  ❌ Not yet — short by {formatINR(item.shortfall_minor)}
                  {item.months_to_afford != null
                    ? `, about ${item.months_to_afford} month(s) at current cash flow`
                    : !item.on_current_cash_flow
                      ? " — not on current cash flow"
                      : ""}
                </>
              )}
            </p>
            <button onClick={() => promote.mutate(item.item_id)} className="mt-2 text-sm underline">
              Promote to goal
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
