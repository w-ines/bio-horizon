"use client";

import { usePathname } from "next/navigation";
import Sidebar from "./Sidebar";

export default function LayoutWrapper({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isHomePage = pathname === "/";

  if (isHomePage) {
    // Dashboard only - no sidebar
    return <>{children}</>;
  }

  // All other pages - with sidebar
  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <main style={{ marginLeft: "250px", flex: 1, minHeight: "100vh", overflow: "auto" }}>
        {children}
      </main>
    </div>
  );
}
