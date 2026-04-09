import { createError, getRouterParam } from "h3";

import { proxyReceiverAdmin } from "~~/server/utils/receiver-admin";

export default defineEventHandler(async (event) => {
  const namespace = getRouterParam(event, "namespace");

  if (!namespace) {
    throw createError({
      statusCode: 400,
      statusMessage: "Missing namespace parameter",
    });
  }

  return await proxyReceiverAdmin(
    event,
    `/admin/settings/${encodeURIComponent(namespace)}`,
    {
      method: "GET",
    },
  );
});
