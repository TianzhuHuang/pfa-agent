"use client";

import Link from "next/link";

export default function XueqiuExtensionPage() {
  return (
    <div className="mx-auto max-w-2xl p-6">
      <Link href="/settings" className="text-sm text-[#1976d2] hover:text-[#42a5f5] mb-4 inline-block">
        ← 返回设置
      </Link>
      <h1 className="mb-6 text-xl font-semibold text-white">PFA 雪球 Chrome 扩展</h1>
      <p className="mb-4 text-sm text-[#888]">
        雪球 Web 端 API 有严格的防爬机制和动态 Token。通过扩展程序直接读取用户已登录的浏览器环境是最稳定的方案。
      </p>
      <div className="space-y-4 rounded-lg border border-white/5 bg-[#0a0a0a] p-4 text-sm text-white">
        <h2 className="font-medium text-[#888]">安装步骤</h2>
        <ol className="list-decimal list-inside space-y-2 text-[#ccc]">
          <li>在 Chrome 中打开 <code className="rounded bg-white/10 px-1">chrome://extensions/</code></li>
          <li>开启右上角「开发者模式」</li>
          <li>点击「加载已解压的扩展程序」</li>
          <li>选择项目根目录下的 <code className="rounded bg-white/10 px-1">chrome-extension/</code> 文件夹</li>
        </ol>
        <h2 className="font-medium text-[#888] pt-2">使用步骤</h2>
        <ol className="list-decimal list-inside space-y-2 text-[#ccc]">
          <li>在浏览器中打开 <a href="https://xueqiu.com" target="_blank" rel="noopener noreferrer" className="text-[#1976d2] hover:underline">xueqiu.com</a> 并登录</li>
          <li>打开 PFA 设置页 → 社交与监控 → 雪球</li>
          <li>点击「同步 Cookie」，扩展会将 Cookie 同步到后端</li>
          <li>同步成功后即可在「雪球用户」中添加监控账号</li>
        </ol>
        <p className="pt-2 text-xs text-[#666]">
          安全说明：Cookie 仅存储在本地 config/xueqiu-auth.json，不提交到 git，后端不会在日志中明文打印。
        </p>
      </div>
    </div>
  );
}
