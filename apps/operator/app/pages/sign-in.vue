<script setup lang="ts">
import { computed, ref } from "vue";

import { authClient } from "~~/lib/auth-client";

type AuthMode = "sign-in" | "sign-up";

const mode = ref<AuthMode>("sign-in");
const name = ref("");
const email = ref("");
const password = ref("");
const pending = ref(false);
const errorMessage = ref("");

const submitLabel = computed(() =>
  mode.value === "sign-in" ? "Sign in" : "Create operator account",
);

async function submitForm() {
  pending.value = true;
  errorMessage.value = "";

  try {
    const result =
      mode.value === "sign-in"
        ? await authClient.signIn.email({
            email: email.value,
            password: password.value,
            callbackURL: "/dashboard",
          })
        : await authClient.signUp.email({
            email: email.value,
            password: password.value,
            name: name.value,
            callbackURL: "/dashboard",
          });

    if (result?.error) {
      errorMessage.value = result.error.message || "Authentication failed";
      return;
    }

    await navigateTo("/dashboard");
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "Authentication failed";
  } finally {
    pending.value = false;
  }
}
</script>

<template>
  <main class="page-wrap hero-grid">
    <section class="panel hero-card">
      <span class="eyebrow">Operator Access</span>
      <h1 class="headline">Sign in to the control plane.</h1>
      <p class="lede">
        The initial auth shell is intentionally narrow: email and password,
        Postgres persistence, and a session-aware dashboard that later epics can
        build on.
      </p>
      <div class="button-row">
        <button
          class="ghost-button"
          type="button"
          @click="mode = mode === 'sign-in' ? 'sign-up' : 'sign-in'"
        >
          {{
            mode === "sign-in" ? "Need an account?" : "Already have an account?"
          }}
        </button>
        <NuxtLink class="ghost-button" to="/">Back home</NuxtLink>
      </div>
    </section>

    <section class="panel auth-card">
      <div class="split-header">
        <div>
          <div class="meta-label">
            {{ mode === "sign-in" ? "Sign in" : "Sign up" }}
          </div>
          <h2>{{ submitLabel }}</h2>
        </div>
      </div>

      <form class="form-grid" @submit.prevent="submitForm">
        <div v-if="mode === 'sign-up'" class="field">
          <label for="name">Name</label>
          <input id="name" v-model="name" autocomplete="name" required />
        </div>

        <div class="field">
          <label for="email">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            autocomplete="email"
            required
          />
        </div>

        <div class="field">
          <label for="password">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            autocomplete="current-password"
            minlength="8"
            required
          />
        </div>

        <p class="form-error">{{ errorMessage }}</p>

        <button class="button" type="submit" :disabled="pending">
          {{ pending ? "Working..." : submitLabel }}
        </button>
      </form>
    </section>
  </main>
</template>
