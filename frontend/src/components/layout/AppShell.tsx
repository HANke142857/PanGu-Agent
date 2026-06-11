import type { ReactNode } from "react";
import { TopBar } from "./TopBar";
import { SideNav } from "./SideNav";
import { UploadProvider } from "@/components/upload/UploadProvider";

// 应用外壳：顶栏 + 左导航 + 内容区
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <UploadProvider>
      <div className="flex h-screen flex-col overflow-hidden">
        <TopBar />
        <div className="flex min-h-0 flex-1">
          <SideNav />
          <main className="min-w-0 flex-1 overflow-hidden">{children}</main>
        </div>
      </div>
    </UploadProvider>
  );
}
