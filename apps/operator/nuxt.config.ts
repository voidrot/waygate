import process from "node:process";

export default defineNuxtConfig({
  compatibilityDate: "2026-04-09",
  devtools: { enabled: true },
  css: ["~/assets/css/main.css"],
  runtimeConfig: {
    betterAuthSecret: process.env.BETTER_AUTH_SECRET,
    databaseUrl: process.env.DATABASE_URL,
    public: {
      betterAuthUrl: process.env.BETTER_AUTH_URL || "http://localhost:3000",
      appName: "WayGate Operator",
      receiverBaseUrl: process.env.RECEIVER_BASE_URL || "http://127.0.0.1:8000",
    },
  },
});
