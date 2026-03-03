/**
 * 交易时段校验（A 股 / 港股）
 * 9:15 - 11:30（早盘）
 * 13:00 - 16:00（午盘，港股下午至 16:00）
 * 周末不交易
 */

function isWeekday(d: Date): boolean {
  const day = d.getDay();
  return day >= 1 && day <= 5; // 周一至周五
}

function timeToMinutes(h: number, m: number): number {
  return h * 60 + m;
}

function dateToMinutes(d: Date): number {
  return d.getHours() * 60 + d.getMinutes();
}

/**
 * 当前是否在交易时段内（本地时间，CST 适用）
 */
export function isTradingHours(): boolean {
  const now = new Date();
  if (!isWeekday(now)) return false;

  const mins = dateToMinutes(now);
  const morningStart = timeToMinutes(9, 15);
  const morningEnd = timeToMinutes(11, 30);
  const afternoonStart = timeToMinutes(13, 0);
  const afternoonEnd = timeToMinutes(16, 0);

  return (
    (mins >= morningStart && mins <= morningEnd) ||
    (mins >= afternoonStart && mins <= afternoonEnd)
  );
}
