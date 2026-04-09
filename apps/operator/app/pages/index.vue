<script setup lang="ts">
import { authClient } from "~~/lib/auth-client";

const { data: session } = await authClient.useSession(useFetch);
</script>

<template>
  <main class="page-wrap stack">
    <section class="hero-grid">
      <article class="panel hero-card">
        <span class="eyebrow">WayGate Operator</span>
        <h1 class="headline">
          Control the data plane before the agents touch it.
        </h1>
        <p class="lede">
          This Nuxt app hosts Better Auth, provides the first operator shell,
          and becomes the place where runtime and plugin settings move out of ad
          hoc environment editing.
        </p>
        <div class="button-row">
          <NuxtLink v-if="session" class="button" to="/dashboard">
            Open dashboard
          </NuxtLink>
          <NuxtLink v-else class="button" to="/sign-in"> Sign in </NuxtLink>
          <a class="ghost-button" href="/api/auth/get-session">
            Auth endpoint
          </a>
        </div>
      </article>

      <aside class="panel info-card stack">
        <div>
          <div class="meta-label">Persistence</div>
          <div class="meta-value">Postgres-backed Better Auth state</div>
        </div>
        <div>
          <div class="meta-label">Next handoff</div>
          <div class="meta-value">
            Authenticated receiver settings editor is live in the dashboard
          </div>
        </div>
        <div>
          <div class="meta-label">Current session</div>
          <div class="meta-value">
            {{ session?.user?.email || "No active operator session" }}
          </div>
        </div>
      </aside>
    </section>
  </main>
</template>
