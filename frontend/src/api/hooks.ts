// @tanstack/react-query wrappers, one per api.ts entry point. The board
// polls every 15s: the exports change at session ends, so faster polling
// would not surface data sooner.
import { useQuery } from "@tanstack/react-query";
import { api } from "./client";

export const POLL_INTERVAL_MS = 15_000;

export function useProjects() {
  return useQuery({ queryKey: ["projects"], queryFn: api.projects, refetchInterval: POLL_INTERVAL_MS });
}

export function useBoard() {
  return useQuery({ queryKey: ["board"], queryFn: api.board, refetchInterval: POLL_INTERVAL_MS });
}

// The drawer is a point-in-time read of one folder, so it does not poll.
export function useTaskDetail(project: string | null, folder: string | null) {
  return useQuery({
    queryKey: ["task-detail", project ?? "", folder ?? ""],
    queryFn: () => api.taskDetail(project as string, folder as string),
    enabled: project !== null && folder !== null,
  });
}

// A doc is fetched only once a sidebar row is clicked.
export function useTaskDoc(project: string | null, folder: string | null, file: string | null) {
  return useQuery({
    queryKey: ["task-doc", project ?? "", folder ?? "", file ?? ""],
    queryFn: () => api.taskDoc(project as string, folder as string, file as string),
    enabled: project !== null && folder !== null && file !== null,
  });
}
