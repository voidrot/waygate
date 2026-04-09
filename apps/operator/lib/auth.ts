import process from "node:process";

import { Pool } from "pg";
import { betterAuth } from "better-auth";

const databaseUrl = process.env.DATABASE_URL;
const betterAuthSecret = process.env.BETTER_AUTH_SECRET;
const betterAuthUrl = process.env.BETTER_AUTH_URL || "http://localhost:3000";

if (!databaseUrl) {
  throw new Error("DATABASE_URL must be configured for the operator app");
}

if (!betterAuthSecret) {
  throw new Error("BETTER_AUTH_SECRET must be configured for the operator app");
}

const pool = new Pool({
  connectionString: databaseUrl,
});

export const auth = betterAuth({
  appName: "WayGate Operator",
  baseURL: betterAuthUrl,
  secret: betterAuthSecret,
  trustedOrigins: [betterAuthUrl],
  database: pool,
  emailAndPassword: {
    enabled: true,
  },
});
