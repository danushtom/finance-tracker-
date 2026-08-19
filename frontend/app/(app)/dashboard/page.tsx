"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  ArrowDownRight,
  ArrowUpRight,
  Plus,
  AlertCircle,
  TrendingUp,
  Target,
  Gift,
  ChevronRight,
  PiggyBank,
  Wallet,
  Bell,
} from "lucide-react";

import { api } from "@/lib/api-client";
import { currentMonthKey, formatCurrency } from "@/lib/format";
import type { DashboardPayload } from "@/types/api";
import { useAuth } from "@/lib/auth-context";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";

// Mock data for the historical chart as the current API only returns single-month data
const mockChartData = [
  { name: "Jan", income: 28000, expense: 24000, balance: 4000, netIncome: 4000, savings: 4000, netWorth: 104000 },
  { name: "Feb", income: 30000, expense: 13980, balance: 16020, netIncome: 16020, savings: 16020, netWorth: 120020 },
  { name: "Mar", income: 20000, expense: 38000, balance: -18000, netIncome: -18000, savings: 0, netWorth: 102020 },
  { name: "Apr", income: 27800, expense: 39080, balance: -11280, netIncome: -11280, savings: 0, netWorth: 90740 },
  { name: "May", income: 33800, expense: 32600, balance: 1200, netIncome: 1200, savings: 1200, netWorth: 91940 },
  { name: "Jun", income: 23900, expense: 38000, balance: -14100, netIncome: -14100, savings: 0, netWorth: 77840 },
  { name: "Jul", income: 34900, expense: 4300, balance: 30600, netIncome: 30600, savings: 30600, netWorth: 108440 },
  { name: "Aug", income: 32000, expense: 14000, balance: 18000, netIncome: 18000, savings: 18000, netWorth: 126440 },
  { name: "Sep", income: 35000, expense: 24000, balance: 11000, netIncome: 11000, savings: 11000, netWorth: 137440 },
];

const TABS = ["Summary", "Balance", "Spending", "Income", "Net Income", "Savings", "Net Worth"];

export default function DashboardPage() {
  const [month, setMonth] = useState(currentMonthKey());
  const [activeTab, setActiveTab] = useState("Summary");
  const { user } = useAuth();

  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard", month],
    queryFn: () => api.get<DashboardPayload>(`/dashboard?month=${month}`),
  });

  if (isLoading) {
    return (
      <div className="flex min-h-[80vh] items-center justify-center bg-transparent text-foreground">
        <p className="animate-pulse text-lg font-medium text-gray-500">Loading dashboard...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex min-h-[80vh] items-center justify-center bg-transparent text-red-600">
        <p>Could not load the dashboard.</p>
      </div>
    );
  }

  return (
    <div className="font-sans">
      {/* Main Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Left Column (Spans 2) */}
        <div className="xl:col-span-2 space-y-6 flex flex-col">
          
          {/* Financial Analytics Chart */}
          <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white flex-1 overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between pb-6 pt-7 px-8">
              <CardTitle className="text-xl font-bold">Financial analytics</CardTitle>
            </CardHeader>
            <div className="px-8 pb-2">
              <div className="flex space-x-6 text-sm font-medium text-gray-400 border-b border-gray-100/60 overflow-x-auto no-scrollbar whitespace-nowrap">
                {TABS.map(tab => (
                  <span 
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`cursor-pointer pb-3 transition-colors ${activeTab === tab ? 'text-gray-900 border-b-2 border-gray-900' : 'hover:text-gray-900'}`}
                  >
                    {tab}
                  </span>
                ))}
              </div>
            </div>
            <CardContent className="px-8 pb-8 pt-6">
              <div className="h-[320px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  {activeTab === "Summary" ? (
                    <LineChart data={mockChartData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
                      <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#9ca3af', fontSize: 13 }} dy={15} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fill: '#9ca3af', fontSize: 13 }} tickFormatter={(value) => new Intl.NumberFormat(user?.settings?.currency === "INR" ? "en-IN" : "en-US", { style: "currency", currency: user?.settings?.currency || "INR", notation: "compact", maximumFractionDigits: 0 }).format(value)} dx={-10} />
                      <Tooltip cursor={{ stroke: '#f3f4f6', strokeWidth: 2 }} contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 8px 30px rgba(0,0,0,0.08)', padding: '16px' }} itemStyle={{ fontWeight: 600, fontSize: '14px' }} labelStyle={{ color: '#9ca3af', marginBottom: '8px' }} />
                      <Line type="monotone" dataKey="income" stroke="#2563eb" strokeWidth={3} dot={{ r: 4, strokeWidth: 2 }} activeDot={{ r: 6, strokeWidth: 0 }} />
                      <Line type="monotone" dataKey="expense" stroke="#ff6b4a" strokeWidth={3} dot={{ r: 4, strokeWidth: 2 }} activeDot={{ r: 6, strokeWidth: 0 }} />
                    </LineChart>
                  ) : activeTab === "Net Worth" ? (
                    <AreaChart data={mockChartData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorNetWorth" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
                      <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#9ca3af', fontSize: 13 }} dy={15} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fill: '#9ca3af', fontSize: 13 }} tickFormatter={(value) => new Intl.NumberFormat(user?.settings?.currency === "INR" ? "en-IN" : "en-US", { style: "currency", currency: user?.settings?.currency || "INR", notation: "compact", maximumFractionDigits: 0 }).format(value)} dx={-10} />
                      <Tooltip cursor={{ stroke: '#f3f4f6', strokeWidth: 2 }} contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 8px 30px rgba(0,0,0,0.08)', padding: '16px' }} itemStyle={{ fontWeight: 600, fontSize: '14px' }} labelStyle={{ color: '#9ca3af', marginBottom: '8px' }} />
                      <Area type="monotone" dataKey="netWorth" stroke="#10b981" fillOpacity={1} fill="url(#colorNetWorth)" strokeWidth={3} />
                    </AreaChart>
                  ) : (
                    <BarChart data={mockChartData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }} barGap={-16}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
                      <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#9ca3af', fontSize: 13 }} dy={15} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fill: '#9ca3af', fontSize: 13 }} tickFormatter={(value) => new Intl.NumberFormat(user?.settings?.currency === "INR" ? "en-IN" : "en-US", { style: "currency", currency: user?.settings?.currency || "INR", notation: "compact", maximumFractionDigits: 0 }).format(value)} dx={-10} />
                      <Tooltip cursor={{ fill: '#f8f9fc', opacity: 0.5 }} contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 8px 30px rgba(0,0,0,0.08)', padding: '16px' }} itemStyle={{ fontWeight: 600, fontSize: '14px' }} labelStyle={{ color: '#9ca3af', marginBottom: '8px' }} />
                      
                      {activeTab === "Balance" && <Bar dataKey="balance" fill="#8b5cf6" radius={[6, 6, 6, 6]} barSize={32} />}
                      {activeTab === "Spending" && <Bar dataKey="expense" fill="#ff6b4a" radius={[6, 6, 6, 6]} barSize={32} />}
                      {activeTab === "Income" && <Bar dataKey="income" fill="#2563eb" radius={[6, 6, 6, 6]} barSize={32} />}
                      {activeTab === "Net Income" && <Bar dataKey="netIncome" fill="#06b6d4" radius={[6, 6, 6, 6]} barSize={32} />}
                      {activeTab === "Savings" && <Bar dataKey="savings" fill="#10b981" radius={[6, 6, 6, 6]} barSize={32} />}
                    </BarChart>
                  )}
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Bottom row of left column */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* Accounts Card */}
            <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white h-[280px]">
              <CardHeader className="flex flex-row items-center justify-between px-7 pt-7 pb-2">
                <CardTitle className="text-xl font-bold">Accounts</CardTitle>
                <Button variant="outline" size="sm" className="rounded-full px-5 h-9 border-gray-200 text-gray-700 hover:bg-gray-50">
                  + Add
                </Button>
              </CardHeader>
              <CardContent className="px-7 pb-7 pt-4">
                <p className="text-sm text-gray-400 mb-6 font-medium tracking-wide">Investments</p>
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="h-11 w-11 rounded-full bg-[#0052FF] flex items-center justify-center text-white font-bold text-xs shadow-sm">CB</div>
                      <div>
                        <p className="font-semibold text-gray-900">Coinbase</p>
                        <p className="text-xs text-gray-400 mt-0.5">9 minutes ago</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-gray-900 text-lg">{formatCurrency(34200, user?.settings?.currency)}</p>
                      <p className="text-xs text-green-500 font-medium flex justify-end items-center gap-1 mt-0.5"><ArrowUpRight className="h-3 w-3" />14%</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="h-11 w-11 rounded-full bg-gray-900 flex items-center justify-center text-white font-bold text-sm shadow-sm">M</div>
                      <div>
                        <p className="font-semibold text-gray-900">me</p>
                        <p className="text-xs text-gray-400 mt-0.5">26 hours ago</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-gray-900 text-lg">{formatCurrency(29600, user?.settings?.currency)}</p>
                      <p className="text-xs text-red-500 font-medium flex justify-end items-center gap-1 mt-0.5"><ArrowDownRight className="h-3 w-3" />16%</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Expenses Card */}
            <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white h-[280px] flex flex-col">
              <CardHeader className="flex flex-row items-center justify-between px-7 pt-7 pb-2">
                <CardTitle className="text-xl font-bold">Expenses</CardTitle>
                <Button variant="outline" size="sm" className="rounded-full px-5 h-9 border-gray-200 text-gray-700 hover:bg-gray-50">
                  Transactions
                </Button>
              </CardHeader>
              <CardContent className="px-7 pb-7 pt-4 flex flex-col flex-1">
                <p className="text-sm text-gray-400 font-medium tracking-wide">Latest Transaction</p>
                <p className="text-4xl font-bold text-gray-900 mt-2 mb-2">{formatCurrency(72203, user?.settings?.currency)}</p>
                <div className="flex-1 flex items-end justify-between relative mt-2">
                   <p className="text-xs text-gray-400 font-medium pb-1">Average: {formatCurrency(72203, user?.settings?.currency)}</p>
                   {/* Mock small bar chart for days */}
                   <div className="flex gap-2 h-full items-end ml-auto pt-4">
                     <div className="w-9 bg-gray-100 rounded-md h-[25%] flex flex-col justify-end items-center"><span className="text-[11px] text-gray-400 mt-1 absolute -bottom-5">Mon</span></div>
                     <div className="w-9 bg-[#ff6b4a] rounded-md h-[85%] flex flex-col justify-start items-center relative shadow-[0_4px_10px_rgba(255,107,74,0.3)]"><div className="absolute -top-7 bg-gray-900 text-white text-[10px] font-medium px-2 py-1 rounded-md">{formatCurrency(11479, user?.settings?.currency)}</div><span className="text-[11px] text-gray-400 absolute -bottom-5">Tue</span></div>
                     <div className="w-9 bg-gray-100 rounded-md h-[35%] flex flex-col justify-end items-center"><span className="text-[11px] text-gray-400 mt-1 absolute -bottom-5">Wed</span></div>
                     <div className="w-9 bg-gray-100 rounded-md h-[55%] flex flex-col justify-end items-center"><span className="text-[11px] text-gray-400 mt-1 absolute -bottom-5">Thu</span></div>
                   </div>
                </div>
              </CardContent>
            </Card>

          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          
          {/* Dark Card - Progress */}
          <Card className="rounded-3xl border-none bg-[#1c1c1e] text-white shadow-xl overflow-hidden relative">
            <CardContent className="p-7 flex items-center justify-between">
              <div className="flex items-center gap-5">
                <div className="relative h-14 w-14">
                  {/* Fake Circular Progress */}
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                    <path
                      className="text-gray-800"
                      strokeDasharray="100, 100"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      stroke="currentColor" strokeWidth="3" fill="none"
                    />
                    <path
                      className="text-[#ff6b4a]"
                      strokeDasharray="75, 100"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      stroke="currentColor" strokeWidth="3" fill="none" strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-sm font-bold">75%</span>
                  </div>
                </div>
                <div>
                  <h3 className="font-bold text-[15px] leading-tight">Get your money&apos;s worth</h3>
                  <p className="text-xs text-gray-400 mt-1 font-medium">Finish setting up Bright AI</p>
                </div>
              </div>
              <ChevronRight className="h-5 w-5 text-gray-500" />
            </CardContent>
          </Card>

          {/* Invite Promo Card */}
          <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-[#f8f9fc] relative overflow-hidden h-[240px]">
             <div className="absolute right-0 bottom-0 opacity-60 mix-blend-multiply w-40 h-40 bg-gradient-to-tl from-purple-200 to-transparent rounded-full -mr-12 -mb-12 blur-2xl"></div>
             <CardContent className="p-8 h-full flex flex-col justify-center">
               <h3 className="font-bold text-xl mb-3 pr-8">Invite friends, earn rewards</h3>
               <p className="text-gray-500 text-[13px] mb-6 leading-relaxed pr-4 font-medium">
                 Get a $25 credit & boosted APY, once they become a member.
               </p>
               <Button className="rounded-full bg-gray-900 text-white hover:bg-gray-800 px-6 h-11 w-max shadow-md">
                 Share Bright AI
               </Button>
               <div className="absolute right-6 top-1/2 -translate-y-1/2 text-[80px] opacity-90 drop-shadow-xl" style={{ filter: 'drop-shadow(0 10px 15px rgba(0,0,0,0.1))' }}>
                 🎁
               </div>
             </CardContent>
          </Card>

          {/* Spending Summary Card */}
          <Card className="rounded-3xl border-none shadow-[0_4px_20px_rgba(0,0,0,0.03)] bg-white">
             <CardHeader className="flex flex-row items-center justify-between px-8 pt-8 pb-0">
               <CardTitle className="text-xl font-bold">Spending</CardTitle>
               <Button variant="outline" size="icon" className="rounded-full h-9 w-9 border-gray-200 shadow-sm text-gray-700 hover:bg-gray-50">
                 <ChevronRight className="h-4 w-4" />
               </Button>
             </CardHeader>
               <CardContent className="p-8 pt-6">
               <p className="text-sm text-gray-400 font-medium tracking-wide">Spent This Month</p>
               <p className="text-[40px] leading-none font-bold text-gray-900 mt-2 mb-8">{formatCurrency(38456745, user?.settings?.currency)}</p>
               
               {/* Segmented Progress Bar */}
               <div className="h-2.5 flex w-full rounded-full overflow-hidden mb-8 gap-0.5">
                 <div className="bg-gray-900 h-full rounded-l-full" style={{ width: '37%' }}></div>
                 <div className="bg-[#2563eb] h-full" style={{ width: '44%' }}></div>
                 <div className="bg-[#ff6b4a] h-full rounded-r-full" style={{ width: '19%' }}></div>
               </div>

               <div className="grid grid-cols-3 gap-2 mb-10">
                 <div>
                   <div className="flex items-center gap-2 mb-1.5">
                     <div className="w-2 h-2 rounded-full bg-gray-900"></div>
                     <span className="text-[13px] text-gray-500 font-medium">Salary</span>
                   </div>
                   <p className="font-bold text-gray-900">{formatCurrency(14200000, user?.settings?.currency)}</p>
                   <p className="text-xs text-gray-400 mt-0.5 font-medium">37%</p>
                 </div>
                 <div>
                   <div className="flex items-center gap-2 mb-1.5">
                     <div className="w-2 h-2 rounded-full bg-[#2563eb]"></div>
                     <span className="text-[13px] text-gray-500 font-medium">Business</span>
                   </div>
                   <p className="font-bold text-gray-900">{formatCurrency(16800000, user?.settings?.currency)}</p>
                   <p className="text-xs text-gray-400 mt-0.5 font-medium">44%</p>
                 </div>
                 <div>
                   <div className="flex items-center gap-2 mb-1.5">
                     <div className="w-2 h-2 rounded-full bg-[#ff6b4a]"></div>
                     <span className="text-[13px] text-gray-500 font-medium">Investment</span>
                   </div>
                   <p className="font-bold text-gray-900">{formatCurrency(7450000, user?.settings?.currency)}</p>
                   <p className="text-xs text-gray-400 mt-0.5 font-medium">19%</p>
                 </div>
               </div>

               <Button variant="outline" className="w-full rounded-full border-gray-200 h-12 font-semibold text-gray-700 hover:bg-gray-50">
                 Show detailed report
               </Button>
             </CardContent>
          </Card>

        </div>
      </div>
    </div>
  );
}
