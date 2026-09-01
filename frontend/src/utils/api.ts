/**
 * Browser-side HTTP client for the REST API under /api. Each function maps to
 * a single route and returns the parsed DTO. Non-2xx responses are surfaced as
 * thrown Errors carrying the server's error message when available.
 */
import { ApiUser, ApiThread, ApiMessage } from "@/types/dto";

interface ErrorEnvelope {
  error?: { code?: string; message?: string };
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  const text = await res.text();
  const body = text ? JSON.parse(text) : null;

  if (!res.ok) {
    const message =
      (body as ErrorEnvelope | null)?.error?.message ??
      `Request to ${url} failed with status ${res.status}`;
    throw new Error(message);
  }

  return body as T;
}

export function getUsers(): Promise<ApiUser[]> {
  return request<ApiUser[]>("/api/users");
}

export function getThreads(query?: string): Promise<ApiThread[]> {
  const qs = query ? `?query=${encodeURIComponent(query)}` : "";
  return request<ApiThread[]>(`/api/threads${qs}`);
}

export function createThread(
  title: string,
  userIds: string[]
): Promise<ApiThread> {
  return request<ApiThread>("/api/threads", {
    method: "POST",
    body: JSON.stringify({ title, userIds }),
  });
}

export function getMessages(threadId: string): Promise<ApiMessage[]> {
  return request<ApiMessage[]>(
    `/api/threads/${encodeURIComponent(threadId)}/messages`
  );
}

export function sendMessage(
  threadId: string,
  userId: string,
  message: string
): Promise<ApiMessage> {
  return request<ApiMessage>(
    `/api/threads/${encodeURIComponent(threadId)}/messages`,
    {
      method: "POST",
      body: JSON.stringify({ userId, message }),
    }
  );
}
