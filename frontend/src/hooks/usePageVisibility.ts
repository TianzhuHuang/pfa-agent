"use client";

import { useState, useEffect } from "react";

/**
 * 监听 document.visibilityState，标签页隐藏时返回 false。
 * 用于智能休眠：切到别的网页时暂停定时器，节省流量。
 */
export function usePageVisibility(): boolean {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const handler = () => {
      setVisible(document.visibilityState === "visible");
    };
    handler(); // 初始化
    document.addEventListener("visibilitychange", handler);
    return () => document.removeEventListener("visibilitychange", handler);
  }, []);

  return visible;
}
