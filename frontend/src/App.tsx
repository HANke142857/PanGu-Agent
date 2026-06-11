import { Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { WorkbenchPage } from "@/pages/WorkbenchPage";
import { DrawingsPage } from "@/pages/DrawingsPage";
import { TasksPage } from "@/pages/TasksPage";
import { KnowledgePage } from "@/pages/KnowledgePage";
import { PLMPage } from "@/pages/PLMPage";

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<WorkbenchPage />} />
        <Route path="/drawings" element={<DrawingsPage />} />
        <Route path="/tasks" element={<TasksPage />} />
        <Route path="/knowledge" element={<KnowledgePage />} />
        <Route path="/plm" element={<PLMPage />} />
      </Routes>
    </AppShell>
  );
}
