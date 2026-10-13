import { useEffect, useState } from "react";
import { Kanban } from "./pages/Kanban";

type DrawerTab = "details" | "docs";

// Drawer URL state: `/?task=<folder>&tab=details|docs`, shareable and
// restorable on a hard reload.
function pathFor(task: string | null, tab: DrawerTab): string {
  if (!task) return "/";
  const params = new URLSearchParams({ task, tab });
  return `/?${params.toString()}`;
}

function parse(search: string): { task: string | null; tab: DrawerTab } {
  const params = new URLSearchParams(search);
  return { task: params.get("task"), tab: params.get("tab") === "docs" ? "docs" : "details" };
}

export function App() {
  const initial = parse(window.location.search);
  const [openTask, setOpenTask] = useState<string | null>(initial.task);
  const [drawerTab, setDrawerTab] = useState<DrawerTab>(initial.tab);

  function navigateToTask(task: string | null, tab: DrawerTab = "details") {
    setOpenTask(task);
    setDrawerTab(tab);
    const path = pathFor(task, tab);
    if (path !== window.location.pathname + window.location.search) window.history.pushState(null, "", path);
  }

  useEffect(() => {
    function onPopState() {
      const view = parse(window.location.search);
      setOpenTask(view.task);
      setDrawerTab(view.tab);
    }
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  return <Kanban openTask={openTask} drawerTab={drawerTab} onOpenTask={navigateToTask} />;
}
