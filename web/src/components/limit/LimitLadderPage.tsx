"use client";

import React, { useState, useMemo } from "react";
import {
  Flame,
  Calendar,
  Loader2,
  AlertCircle,
  AppWindow,
  Table,
  List,
} from "lucide-react";
import {
  useLimitLadder,
  useLimitMultiDays,
  useLimitList,
  useLimitLatestDate,
} from "@/hooks/useLimit";
import type { LimitStockItem, LimitType } from "@/types/limitTypes";

// ============== 视图类型 ==============
type ViewMode = "ladder" | "multi-days" | "list";

// ============== 辅助函数 ==============

/** 封单额格式化：元 → 亿元/万元 */
function formatFdAmount(val: number | null | undefined): string {
  if (val == null) return "-";
  if (val >= 1e8) return `${(val / 1e8).toFixed(2)}亿`;
  if (val >= 1e4) return `${(val / 1e4).toFixed(0)}万`;
  return val.toFixed(0);
}

/** 连板数标签（1=首板，2=2连板...） */
function levelLabel(times: number): string {
  if (times <= 1) return "首板涨停";
  return `${times}连板`;
}

/** 连板层颜色（高度越高越深红） */
function levelColorClass(times: number): string {
  if (times >= 7) return "bg-red-600 text-white";
  if (times >= 5) return "bg-red-500 text-white";
  if (times >= 4) return "bg-red-400 text-white";
  if (times >= 3) return "bg-orange-500 text-white";
  if (times >= 2) return "bg-orange-400 text-white";
  return "bg-orange-300 text-orange-900";
}

/** 个股形态标记（从 first_time / open_times 推断一字/T字等） */
function stockTags(stock: LimitStockItem): string[] {
  const tags: string[] = [];
  // 一字板：首封 09:25 且未炸板
  if (stock.firstTime && stock.firstTime <= "09:25" && (stock.openTimes ?? 0) === 0) {
    tags.push("一字");
  } else if (stock.firstTime && stock.firstTime <= "09:25") {
    tags.push("T字");
  }
  // 炸板次数 > 0
  if ((stock.openTimes ?? 0) > 0) {
    tags.push(`炸${stock.openTimes}`);
  }
  return tags;
}

// ============== 单日天梯视图 ==============

function LadderView({ tradeDate }: { tradeDate: string | null }) {
  const { ladder, isLoading, isError } = useLimitLadder({ tradeDate });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16 text-gray-400">
        <Loader2 className="animate-spin" size={24} />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center py-16 text-red-500">
        <AlertCircle className="mr-2" size={20} />
        加载失败，请稍后重试
      </div>
    );
  }

  if (!ladder || !ladder.hasData) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-gray-400">
        <Flame size={40} className="mb-3 opacity-30" />
        <p>该交易日暂无涨停数据</p>
        <p className="text-sm mt-1">请先在管理后台同步涨停专题数据</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 涨停最强板块统计条 */}
      {ladder.sectors.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-medium text-gray-500">
            涨停最强板块
          </h3>
          <div className="flex flex-wrap gap-2">
            {ladder.sectors.map((s, i) => (
              <div
                key={i}
                className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-3 py-1 text-sm shadow-sm"
                title={`${s.upStat ?? ""} | 连板${s.consNums ?? 0}家`}
              >
                <span className="font-medium text-gray-800">{s.name}</span>
                <span className="rounded-full bg-red-100 px-1.5 text-xs font-semibold text-red-600">
                  {s.upNums}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 连板天梯分层 */}
      <div className="space-y-4">
        {ladder.levels.map((level) => (
          <div key={level.limitTimes} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
            {/* 层标题 */}
            <div className="mb-3 flex items-center gap-2">
              <span
                className={`inline-flex items-center rounded-lg px-2.5 py-1 text-sm font-bold ${levelColorClass(
                  level.limitTimes
                )}`}
              >
                {level.limitTimes}
              </span>
              <span className="font-semibold text-gray-800">
                {levelLabel(level.limitTimes)}
              </span>
              <span className="text-sm text-gray-400">({level.count})</span>
            </div>

            {/* 个股卡片网格 */}
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
              {level.stocks.map((stock) => (
                <div
                  key={stock.tsCode}
                  className="flex flex-col rounded-lg border border-gray-100 bg-gray-50 p-2.5 transition hover:border-orange-300 hover:bg-orange-50"
                >
                  {/* 股票名 + 板块 */}
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-gray-900 truncate">
                      {stock.name}
                    </span>
                    <span className="ml-1 shrink-0 text-xs text-gray-400">
                      {stock.firstTime ?? "-"}
                    </span>
                  </div>
                  <div className="mt-0.5 flex items-center gap-1.5">
                    <span className="text-xs text-blue-500">
                      {stock.industry ?? "-"}
                    </span>
                    {/* 形态标记 */}
                    {stockTags(stock).map((tag, idx) => (
                      <span
                        key={idx}
                        className="rounded bg-red-100 px-1 text-[10px] font-medium text-red-600"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                  {/* 涨幅 + 封单 */}
                  <div className="mt-1 flex items-center justify-between text-xs">
                    <span className="font-semibold text-red-600">
                      +{(stock.pctChg ?? 0).toFixed(2)}%
                    </span>
                    <span className="text-gray-400">
                      封单 {formatFdAmount(stock.fdAmount)}
                    </span>
                  </div>
                  {/* up_stat（如 7天4板） */}
                  {stock.upStat && (
                    <div className="mt-0.5 text-[10px] text-gray-400">
                      {stock.upStat}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============== 多日表格视图 ==============

function MultiDaysView({ endDate }: { endDate: string | null }) {
  const { multiDays, isLoading, isError } = useLimitMultiDays({
    endDate,
    days: 7,
  });

  // 动态列：取所有行中最大的连板高度（hook 必须在所有 early return 之前调用）
  const maxCol = useMemo(() => {
    if (!multiDays || !multiDays.hasData) return 0;
    return Math.max(...multiDays.items.map((it) => it.maxTimes || 0), 0);
  }, [multiDays]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16 text-gray-400">
        <Loader2 className="animate-spin" size={24} />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center py-16 text-red-500">
        <AlertCircle className="mr-2" size={20} />
        加载失败
      </div>
    );
  }

  if (!multiDays || !multiDays.hasData || multiDays.items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-gray-400">
        <Table size={40} className="mb-3 opacity-30" />
        <p>暂无多日统计数据</p>
      </div>
    );
  }

  const cols = Array.from({ length: Math.max(maxCol - 1, 0) }, (_, i) => i + 2);

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50 text-gray-600">
            <th className="px-4 py-3 text-left font-medium">交易日</th>
            <th className="px-4 py-3 text-right font-medium">涨停总数</th>
            <th className="px-4 py-3 text-right font-medium">最高连板</th>
            {cols.map((c) => (
              <th key={c} className="px-4 py-3 text-right font-medium">
                {c}连板
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {multiDays.items.map((item) => (
            <tr key={item.tradeDate} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="px-4 py-3 text-gray-800">{item.tradeDate}</td>
              <td className="px-4 py-3 text-right font-semibold text-red-600">
                {item.totalUp}
              </td>
              <td className="px-4 py-3 text-right">
                {item.maxTimes > 0 ? (
                  <span className="font-bold text-red-600">{item.maxTimes}板</span>
                ) : (
                  "-"
                )}
              </td>
              {cols.map((c) => {
                const val = (item[`limitUp${c}`] as number) ?? 0;
                return (
                  <td key={c} className="px-4 py-3 text-right text-gray-600">
                    {val > 0 ? val : "-"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ============== 列表视图 ==============

function ListView({ tradeDate }: { tradeDate: string | null }) {
  const [page, setPage] = useState(1);
  const [filterType, setFilterType] = useState<LimitType | "">("");
  const pageSize = 50;
  const { list, isLoading, isError } = useLimitList({
    tradeDate,
    limitType: filterType || undefined,
    page,
    pageSize,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16 text-gray-400">
        <Loader2 className="animate-spin" size={24} />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center py-16 text-red-500">
        <AlertCircle className="mr-2" size={20} />
        加载失败
      </div>
    );
  }

  if (!list || !list.hasData || list.items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-gray-400">
        <List size={40} className="mb-3 opacity-30" />
        <p>暂无数据</p>
      </div>
    );
  }

  const totalPages = Math.ceil(list.total / pageSize);

  return (
    <div className="space-y-3">
      {/* 类型筛选 */}
      <div className="flex items-center gap-2">
        {([
          { v: "", label: "全部" },
          { v: "U", label: "涨停" },
          { v: "D", label: "跌停" },
          { v: "Z", label: "炸板" },
        ] as { v: LimitType | ""; label: string }[]).map((opt) => (
          <button
            key={opt.v}
            onClick={() => {
              setFilterType(opt.v);
              setPage(1);
            }}
            className={`rounded-lg px-3 py-1 text-sm transition ${
              filterType === opt.v
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {opt.label}
          </button>
        ))}
        <span className="ml-auto text-sm text-gray-400">共 {list.total} 条</span>
      </div>

      {/* 表格 */}
      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50 text-gray-600">
              <th className="px-3 py-2.5 text-left font-medium">代码</th>
              <th className="px-3 py-2.5 text-left font-medium">名称</th>
              <th className="px-3 py-2.5 text-left font-medium">板块</th>
              <th className="px-3 py-2.5 text-right font-medium">连板</th>
              <th className="px-3 py-2.5 text-right font-medium">涨幅</th>
              <th className="px-3 py-2.5 text-right font-medium">封单</th>
              <th className="px-3 py-2.5 text-center font-medium">首封</th>
              <th className="px-3 py-2.5 text-center font-medium">炸板</th>
              <th className="px-3 py-2.5 text-left font-medium">连板统计</th>
            </tr>
          </thead>
          <tbody>
            {list.items.map((s) => (
              <tr key={s.tsCode} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-3 py-2 text-gray-500">{s.tsCode}</td>
                <td className="px-3 py-2 font-medium text-gray-900">{s.name}</td>
                <td className="px-3 py-2 text-blue-500">{s.industry ?? "-"}</td>
                <td className="px-3 py-2 text-right">
                  {s.limitTimes && s.limitTimes > 1 ? (
                    <span className="font-bold text-red-600">{s.limitTimes}</span>
                  ) : (
                    <span className="text-gray-400">首板</span>
                  )}
                </td>
                <td
                  className={`px-3 py-2 text-right font-semibold ${
                    s.limitType === "D" ? "text-green-600" : "text-red-600"
                  }`}
                >
                  {(s.pctChg ?? 0) > 0 ? "+" : ""}
                  {(s.pctChg ?? 0).toFixed(2)}%
                </td>
                <td className="px-3 py-2 text-right text-gray-500">
                  {formatFdAmount(s.fdAmount)}
                </td>
                <td className="px-3 py-2 text-center text-gray-500">
                  {s.firstTime ?? "-"}
                </td>
                <td className="px-3 py-2 text-center">
                  {(s.openTimes ?? 0) > 0 ? (
                    <span className="text-orange-500">{s.openTimes}</span>
                  ) : (
                    <span className="text-gray-300">0</span>
                  )}
                </td>
                <td className="px-3 py-2 text-xs text-gray-400">
                  {s.upStat ?? "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="rounded-lg border border-gray-200 px-3 py-1 text-sm disabled:opacity-40"
          >
            上一页
          </button>
          <span className="text-sm text-gray-500">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="rounded-lg border border-gray-200 px-3 py-1 text-sm disabled:opacity-40"
          >
            下一页
          </button>
        </div>
      )}
    </div>
  );
}

// ============== 主页面 ==============

export default function LimitLadderPage() {
  const [viewMode, setViewMode] = useState<ViewMode>("ladder");
  const [tradeDateInput, setTradeDateInput] = useState("");

  // 取最新交易日作为默认
  const { latestDate, isLoading: isLatestLoading } = useLimitLatestDate();

  const activeDate = tradeDateInput || latestDate;

  return (
    <div className="space-y-4">
      {/* 页头 */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-100">
            <Flame className="text-orange-600" size={24} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">连板天梯</h1>
            <p className="text-sm text-gray-500">
              涨停个股分层 · 连板晋级 · 最强板块
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* 日期选择器 */}
          <div className="flex items-center gap-1.5">
            <Calendar size={16} className="text-gray-400" />
            <input
              type="date"
              value={tradeDateInput}
              onChange={(e) => setTradeDateInput(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* 视图切换 */}
          <div className="flex items-center gap-1 rounded-lg border border-gray-200 bg-gray-50 p-0.5">
            {([
              { v: "ladder", label: "单日", Icon: AppWindow },
              { v: "multi-days", label: "多日", Icon: Table },
              { v: "list", label: "列表", Icon: List },
            ] as { v: ViewMode; label: string; Icon: React.ComponentType<{ size?: number }> }[]).map(
              (opt) => {
                const active = viewMode === opt.v;
                return (
                  <button
                    key={opt.v}
                    onClick={() => setViewMode(opt.v)}
                    className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition ${
                      active
                        ? "bg-white text-gray-900 shadow-sm"
                        : "text-gray-500 hover:text-gray-700"
                    }`}
                  >
                    <opt.Icon size={14} />
                    {opt.label}
                  </button>
                );
              }
            )}
          </div>
        </div>
      </div>

      {/* 数据日期提示 */}
      {!tradeDateInput && (
        <div className="text-xs text-gray-400">
          {isLatestLoading
            ? "加载最新交易日..."
            : latestDate
            ? `显示最新交易日 ${latestDate} 的数据`
            : "暂无数据，请先同步涨停专题数据"}
        </div>
      )}

      {/* 视图内容 */}
      {viewMode === "ladder" && <LadderView tradeDate={activeDate} />}
      {viewMode === "multi-days" && <MultiDaysView endDate={activeDate} />}
      {viewMode === "list" && <ListView tradeDate={activeDate} />}
    </div>
  );
}
