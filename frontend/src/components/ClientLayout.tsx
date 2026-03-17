"use client";

import { usePathname } from "next/navigation";
import { motion } from "framer-motion";

export function ClientLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <motion.div
      key={pathname}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.15 }}
      className="min-h-[calc(100vh-48px)] bg-[#0A0F1E]"
    >
      {children}
    </motion.div>
  );
}
