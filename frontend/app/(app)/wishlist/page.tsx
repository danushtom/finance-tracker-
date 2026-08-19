"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth-context";
import { useState } from "react";
import { api } from "@/lib/api-client";
import { formatCurrency } from "@/lib/format";
import type { WishlistVerdict } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Gift, CheckCircle2, XCircle, ArrowUpCircle } from "lucide-react";

export default function WishlistPage() {
  const { user } = useAuth();
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
    <div className="flex flex-col gap-6 font-sans">
      <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white">
        <CardHeader className="px-6 pt-6 pb-2">
          <CardTitle className="text-lg font-bold flex items-center gap-2">
            <Gift className="h-5 w-5 text-gray-400" /> Add to Wishlist
          </CardTitle>
        </CardHeader>
        <CardContent className="px-6 pb-6 pt-2">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (name && priceRupees) createItem.mutate();
            }}
            className="flex flex-wrap items-end gap-4"
          >
            <label className="flex flex-col gap-1.5 flex-[2] min-w-[200px]">
              <span className="text-sm font-medium text-gray-700">Item name</span>
              <input 
                value={name} 
                onChange={(e) => setName(e.target.value)} 
                placeholder="e.g. New Laptop"
                className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900" 
              />
            </label>
            <label className="flex flex-col gap-1.5 flex-1 min-w-[150px]">
              <span className="text-sm font-medium text-gray-700">Price </span>
              <input
                type="number"
                value={priceRupees}
                onChange={(e) => setPriceRupees(e.target.value)}
                placeholder="80000"
                className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
              />
            </label>
            <label className="flex flex-col gap-1.5 flex-1 min-w-[150px]">
              <span className="text-sm font-medium text-gray-700">Priority</span>
              <select 
                value={priority} 
                onChange={(e) => setPriority(e.target.value)} 
                className="rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
              >
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </label>
            <Button type="submit" disabled={!name || !priceRupees} className="rounded-full bg-gray-900 text-white hover:bg-gray-800 px-6 shadow-sm">
              Add item
            </Button>
          </form>
        </CardContent>
      </Card>

      {isLoading && (
        <div className="p-8 text-center text-gray-500 animate-pulse">Loading wishlist...</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {items?.map((item) => (
          <Card key={item.item_id} className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white overflow-hidden flex flex-col relative">
            <CardContent className="p-6 flex flex-col flex-1 gap-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-bold text-lg text-gray-900 leading-tight mb-1">{item.name}</h3>
                  <span className={`inline-flex items-center justify-center rounded-full px-2.5 py-0.5 text-xs font-medium ${item.priority === 'high' ? 'bg-red-50 text-red-700' : item.priority === 'medium' ? 'bg-blue-50 text-blue-700' : 'bg-gray-100 text-gray-600'}`}>
                    {item.priority}
                  </span>
                </div>
                <span className="font-bold text-xl text-gray-900">{formatCurrency(item.price_minor, user?.settings?.currency)}</span>
              </div>
              
              <div className="flex-1 mt-2">
                {item.affordable ? (
                  <div className="bg-green-50 rounded-2xl p-4 border border-green-100/50 h-full flex flex-col">
                    <div className="flex items-center gap-2 mb-2">
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                      <span className="font-bold text-green-800">Affordable</span>
                    </div>
                    <p className="text-sm text-green-700 font-medium leading-relaxed">
                      You can buy this now! {formatCurrency(item.remaining_after_purchase_minor ?? 0, user?.settings?.currency)} remaining after purchase.
                    </p>
                  </div>
                ) : (
                  <div className="bg-red-50 rounded-2xl p-4 border border-red-100/50 h-full flex flex-col">
                    <div className="flex items-center gap-2 mb-2">
                      <XCircle className="h-5 w-5 text-red-600" />
                      <span className="font-bold text-red-800">Not yet</span>
                    </div>
                    <p className="text-sm text-red-700 font-medium leading-relaxed mb-2">
                      Short by {formatCurrency(item.shortfall_minor, user?.settings?.currency)}
                    </p>
                    <p className="text-xs text-red-600/80">
                      {item.months_to_afford != null
                        ? `Est. ${item.months_to_afford} month(s) at current cash flow`
                        : !item.on_current_cash_flow
                          ? "Not affordable on current cash flow"
                          : ""}
                    </p>
                  </div>
                )}
              </div>

              <div className="pt-2 border-t border-gray-100 mt-2">
                <Button 
                  onClick={() => promote.mutate(item.item_id)} 
                  variant="ghost" 
                  className="w-full text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-full h-10 font-medium"
                >
                  <ArrowUpCircle className="h-4 w-4 mr-2" /> Promote to goal
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
        {items?.length === 0 && !isLoading && (
          <div className="col-span-full p-12 text-center text-gray-500 bg-gray-50/50 rounded-3xl border border-dashed border-gray-200">
            Your wishlist is empty. Add something you want to buy!
          </div>
        )}
      </div>
    </div>
  );
}
