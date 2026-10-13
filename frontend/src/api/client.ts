// Thin fetch wrapper over server.py's GET-only `/api/*` routes. Every
// response is enveloped as { data, meta }; `apiGet` unwraps `data` and
// throws on a non-2xx.
import type { ApiError, BoardPayload, Envelope, ProjectsResponse, TaskDetail, TaskDocContent } from "./types";

export class ApiNotFoundError extends Error {}

async function apiGet<T>(path: string, params: Record<string, string | undefined> = {}): Promise<T> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) query.set(key, value);
  }
  const qs = query.toString();
  const res = await fetch(`/api${path}${qs ? `?${qs}` : ""}`);
  if (!res.ok) {
    const body = (await res.json().catch(() => ({ error: res.statusText }))) as ApiError;
    if (res.status === 404) throw new ApiNotFoundError(body.error);
    throw new Error(body.error);
  }
  const body = (await res.json()) as Envelope<T>;
  return body.data;
}

export const api = {
  projects: () => apiGet<ProjectsResponse>("/projects"),

  board: () => apiGet<BoardPayload>("/tasks"),

  taskDetail: (project: string, folder: string) => apiGet<TaskDetail>("/tasks/detail", { project, folder }),

  taskDoc: (project: string, folder: string, file: string) =>
    apiGet<TaskDocContent>("/tasks/doc", { project, folder, file }),
};
