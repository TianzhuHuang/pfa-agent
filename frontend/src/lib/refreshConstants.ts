/**
 * 数据拉取频率常量（毫秒）
 * 参考：活跃个股 5-10s，持仓总览 30-60s，汇率 4-6h
 */

/** 个股详情页：10 秒 */
export const DETAIL_REFRESH_INTERVAL = 10_000;

/** 持仓总览页：120 秒 */
export const PORTFOLIO_REFRESH_INTERVAL = 120 * 1000;

/** 汇率：5 小时（取 4-6h 中间值） */
export const FX_REFRESH_INTERVAL = 5 * 60 * 60 * 1000;
