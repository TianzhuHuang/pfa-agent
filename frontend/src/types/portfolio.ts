/**
 * PFA 核心数据模型规范 (Data Contract)
 * 现价永远为标的原始价格，市值根据全局汇率动态计算。
 */

export type CurrencyCode = "USD" | "CNY" | "HKD";

export interface ExchangeRates {
  [key: string]: number; // e.g. { "USD": 7.21, "HKD": 0.92, "CNY": 1.0 } (rate to CNY)
}

export interface PortfolioAsset {
  id?: string;
  symbol: string;
  name: string;
  exchange?: string;

  /** 标的原始币种 (录入时确定，如 NIO 为 USD) */
  originalCurrency: CurrencyCode;
  /** 市场实时现价 (原始币种数值，禁止折算) */
  currentPrice: number;
  /** 持仓成本 (原始币种数值) */
  costPrice: number;
  quantity: number;

  dailyChangePercent: number;
  /** 市值 (根据 displayCurrencyMode 动态计算) */
  marketValue?: number;
  /** 币种配置错误时无法计算，显示 -- */
  currencyError?: boolean;
}

export interface InvestmentAccount {
  id: string;
  accountName: string;
  defaultCurrency: CurrencyCode;
  assets: PortfolioAsset[];
}

export type DisplayCurrencyMode = "ORIGINAL" | "CNY" | "USD";

export interface UIState {
  displayCurrencyMode: DisplayCurrencyMode;
}
