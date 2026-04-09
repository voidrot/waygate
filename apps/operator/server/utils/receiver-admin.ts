import { createError, type H3Event } from "h3";

import { auth } from "~~/lib/auth";

function receiverAdminUrl(event: H3Event, path: string): string {
  const config = useRuntimeConfig(event);
  const baseUrl = config.public.receiverBaseUrl.replace(/\/$/, "");
  const suffix = path.startsWith("/") ? path : `/${path}`;
  return `${baseUrl}${suffix}`;
}

function extractReceiverDetail(payload: unknown): string {
  if (
    typeof payload === "object" &&
    payload !== null &&
    "detail" in payload &&
    typeof payload.detail === "string"
  ) {
    return payload.detail;
  }
  return "Receiver request failed";
}

export async function requireOperatorSession(event: H3Event) {
  const session = await auth.api.getSession({
    headers: event.headers,
  });

  if (!session) {
    throw createError({
      statusCode: 401,
      statusMessage: "Authentication required",
    });
  }

  return session;
}

export async function proxyReceiverAdmin<T>(
  event: H3Event,
  path: string,
  init?: {
    method?: "GET" | "PATCH";
    body?: Record<string, unknown>;
  },
): Promise<T> {
  await requireOperatorSession(event);

  const response = await $fetch.raw<T>(receiverAdminUrl(event, path), {
    method: init?.method,
    body: init?.body,
    ignoreResponseError: true,
  });

  if (response.status >= 400) {
    throw createError({
      statusCode: response.status,
      statusMessage: extractReceiverDetail(response._data),
      data: response._data,
    });
  }

  return response._data as T;
}