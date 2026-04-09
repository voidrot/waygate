import { proxyReceiverAdmin } from "~~/server/utils/receiver-admin";

export default defineEventHandler(async (event) => {
  return await proxyReceiverAdmin(event, "/admin/settings", {
    method: "GET",
  });
});
