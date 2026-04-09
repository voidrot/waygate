<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";

import { authClient } from "~~/lib/auth-client";

type SettingsOwner = "core" | "plugin";
type SettingSource = "stored" | "env" | "default";
type SettingValueType = "string" | "integer" | "boolean" | "string_list";
type DraftValue = string | number | boolean;

interface SettingsNamespaceSummary {
  namespace: string;
  title: string;
  owner: SettingsOwner;
  plugin_name: string | null;
  settings_count: number;
}

interface SettingsEntryView {
  key: string;
  title: string;
  description: string | null;
  value_type: SettingValueType;
  editable: boolean;
  secret: boolean;
  default_value: unknown;
  stored: boolean;
  stored_value: unknown;
  effective_source: SettingSource;
  effective_value: unknown;
}

interface SettingsNamespaceView {
  namespace: string;
  title: string;
  owner: SettingsOwner;
  plugin_name: string | null;
  settings: SettingsEntryView[];
}

definePageMeta({
  middleware: ["authenticated"],
});

const { data: session } = await authClient.useSession(useFetch);

const selectedNamespace = ref("");
const saving = ref(false);
const resettingKey = ref<string | null>(null);
const saveMessage = ref("");
const saveError = ref("");
const draftValues = reactive<Record<string, DraftValue>>({});

const {
  data: namespacesResponse,
  pending: namespacesPending,
  error: namespacesError,
  refresh: refreshNamespaces,
} = await useFetch<{ namespaces: SettingsNamespaceSummary[] }>(
  "/api/receiver/settings",
);

const namespaces = computed(() => namespacesResponse.value?.namespaces ?? []);

watch(
  namespaces,
  (items) => {
    const firstNamespace = items[0];

    if (!items.length) {
      selectedNamespace.value = "";
      return;
    }

    if (!selectedNamespace.value && firstNamespace) {
      selectedNamespace.value = firstNamespace.namespace;
      return;
    }

    if (
      firstNamespace &&
      !items.some((item) => item.namespace === selectedNamespace.value)
    ) {
      selectedNamespace.value = firstNamespace.namespace;
    }
  },
  { immediate: true },
);

const settingsCacheKey = computed(() =>
  selectedNamespace.value
    ? `receiver-settings-${selectedNamespace.value}`
    : "receiver-settings-empty",
);

const {
  data: namespaceData,
  pending: namespacePending,
  error: namespaceError,
  refresh: refreshNamespace,
} = await useAsyncData<SettingsNamespaceView | null>(
  settingsCacheKey,
  async () => {
    if (!selectedNamespace.value) {
      return null;
    }

    return await $fetch<SettingsNamespaceView>(
      `/api/receiver/settings/${selectedNamespace.value}`,
    );
  },
  { watch: [selectedNamespace] },
);

watch(
  () => namespaceData.value,
  (namespace) => {
    resetDraft(namespace ?? null);
  },
  { immediate: true },
);

const namespaceCountLabel = computed(() => {
  if (!namespaces.value.length) {
    return "No settings namespaces discovered";
  }
  return `${namespaces.value.length} namespaces available`;
});

function resetDraft(namespace: SettingsNamespaceView | null) {
  for (const key of Object.keys(draftValues)) {
    delete draftValues[key];
  }

  saveError.value = "";
  saveMessage.value = "";

  if (!namespace) {
    return;
  }

  for (const setting of namespace.settings) {
    draftValues[setting.key] = initialDraftValue(setting);
  }
}

function initialDraftValue(setting: SettingsEntryView): DraftValue {
  if (setting.secret) {
    return "";
  }

  if (setting.value_type === "boolean") {
    return Boolean(setting.effective_value ?? setting.default_value ?? false);
  }

  if (setting.value_type === "integer") {
    const value = setting.effective_value ?? setting.default_value;
    return typeof value === "number" ? value : Number(value ?? 0);
  }

  if (setting.value_type === "string_list") {
    const value = Array.isArray(setting.effective_value)
      ? setting.effective_value
      : Array.isArray(setting.default_value)
        ? setting.default_value
        : [];
    return value.join(", ");
  }

  return String(setting.effective_value ?? setting.default_value ?? "");
}

function buildPatchPayload(
  namespace: SettingsNamespaceView,
): Record<string, unknown> {
  const values: Record<string, unknown> = {};

  for (const setting of namespace.settings) {
    if (!setting.editable) {
      continue;
    }

    const draftValue = draftValues[setting.key];

    if (setting.secret) {
      if (typeof draftValue === "string" && draftValue.trim()) {
        values[setting.key] = draftValue.trim();
      }
      continue;
    }

    if (setting.value_type === "boolean") {
      values[setting.key] = Boolean(draftValue);
      continue;
    }

    if (setting.value_type === "integer") {
      if (
        draftValue === "" ||
        draftValue === undefined ||
        draftValue === null
      ) {
        continue;
      }
      const numericValue =
        typeof draftValue === "number" ? draftValue : Number(draftValue);
      if (!Number.isNaN(numericValue)) {
        values[setting.key] = numericValue;
      }
      continue;
    }

    if (setting.value_type === "string_list") {
      const items =
        typeof draftValue === "string"
          ? draftValue
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean)
          : [];
      values[setting.key] = items;
      continue;
    }

    values[setting.key] =
      typeof draftValue === "string" ? draftValue : String(draftValue ?? "");
  }

  return values;
}

function detailFromError(error: unknown): string {
  if (typeof error === "object" && error !== null) {
    if (
      "data" in error &&
      typeof error.data === "object" &&
      error.data !== null &&
      "detail" in error.data &&
      typeof error.data.detail === "string"
    ) {
      return error.data.detail;
    }

    if ("message" in error && typeof error.message === "string") {
      return error.message;
    }
  }

  return "Receiver settings request failed";
}

async function saveSettings() {
  if (!namespaceData.value || !selectedNamespace.value) {
    return;
  }

  saving.value = true;
  saveError.value = "";
  saveMessage.value = "";

  try {
    const updatedNamespace = await $fetch<SettingsNamespaceView>(
      `/api/receiver/settings/${selectedNamespace.value}`,
      {
        method: "PATCH",
        body: { values: buildPatchPayload(namespaceData.value) },
      },
    );
    namespaceData.value = updatedNamespace;
    resetDraft(updatedNamespace);
    await Promise.all([refreshNamespace(), refreshNamespaces()]);
    saveMessage.value = `Saved ${updatedNamespace.title}.`;
  } catch (error) {
    saveError.value = detailFromError(error);
  } finally {
    saving.value = false;
  }
}

async function resetStoredValue(settingKey: string) {
  if (!selectedNamespace.value) {
    return;
  }

  resettingKey.value = settingKey;
  saveError.value = "";
  saveMessage.value = "";

  try {
    const updatedNamespace = await $fetch<SettingsNamespaceView>(
      `/api/receiver/settings/${selectedNamespace.value}`,
      {
        method: "PATCH",
        body: { values: { [settingKey]: null } },
      },
    );
    namespaceData.value = updatedNamespace;
    resetDraft(updatedNamespace);
    await Promise.all([refreshNamespace(), refreshNamespaces()]);
    saveMessage.value = `Reset ${settingKey} to env/default.`;
  } catch (error) {
    saveError.value = detailFromError(error);
  } finally {
    resettingKey.value = null;
  }
}

function formatResolvedValue(setting: SettingsEntryView): string {
  if (setting.secret) {
    return setting.stored ? "Stored secret" : "Not set";
  }

  const value = setting.effective_value;
  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "Not set";
  }
  if (value === null || value === undefined || value === "") {
    return "Not set";
  }
  return String(value);
}

function formatStoredValue(setting: SettingsEntryView): string {
  if (!setting.stored) {
    return "No stored override";
  }
  if (setting.secret) {
    return "Stored secret";
  }
  if (Array.isArray(setting.stored_value)) {
    return setting.stored_value.length ? setting.stored_value.join(", ") : "[]";
  }
  if (
    setting.stored_value === null ||
    setting.stored_value === undefined ||
    setting.stored_value === ""
  ) {
    return "Empty value";
  }
  return String(setting.stored_value);
}

async function signOut() {
  await authClient.signOut();
  await navigateTo("/");
}
</script>

<template>
  <main class="page-wrap stack">
    <section class="panel hero-card">
      <div class="split-header">
        <div>
          <span class="eyebrow">Authenticated</span>
          <h1 class="headline">Receiver settings control plane</h1>
          <p class="lede">
            The operator app now fronts the receiver settings API. Namespace
            reads and updates stay behind Better Auth, while the receiver keeps
            the source-of-truth contract and secret redaction behavior.
          </p>
        </div>

        <button class="ghost-button" type="button" @click="signOut">
          Sign out
        </button>
      </div>

      <div class="session-card stack">
        <div>
          <div class="meta-label">Signed in as</div>
          <div class="meta-value">
            {{ session?.user?.email || "Unknown user" }}
          </div>
        </div>
        <div>
          <div class="meta-label">Receiver namespaces</div>
          <div class="meta-value">{{ namespaceCountLabel }}</div>
        </div>
      </div>
    </section>

    <section class="dashboard-grid">
      <aside class="panel sidebar-card stack">
        <div>
          <div class="meta-label">Namespaces</div>
          <div class="meta-value">Select a core or plugin scope to edit.</div>
        </div>

        <div v-if="namespacesPending" class="empty-state">
          Loading discovered settings namespaces...
        </div>

        <div v-else-if="namespacesError" class="banner is-error">
          {{ detailFromError(namespacesError) }}
        </div>

        <div v-else-if="!namespaces.length" class="empty-state">
          The receiver did not return any settings namespaces.
        </div>

        <div v-else class="namespace-list">
          <button
            v-for="namespace in namespaces"
            :key="namespace.namespace"
            class="namespace-button"
            :class="{ 'is-active': namespace.namespace === selectedNamespace }"
            type="button"
            @click="selectedNamespace = namespace.namespace"
          >
            <span class="namespace-title">{{ namespace.title }}</span>
            <span class="namespace-meta">
              {{ namespace.owner }} • {{ namespace.settings_count }} settings
            </span>
            <span v-if="namespace.plugin_name" class="namespace-meta">
              {{ namespace.plugin_name }}
            </span>
          </button>
        </div>
      </aside>

      <section class="panel settings-card stack">
        <div class="split-header">
          <div>
            <div class="meta-label">Selected namespace</div>
            <div class="meta-value">
              {{ namespaceData?.title || "Waiting for selection" }}
            </div>
          </div>
          <div class="inline-actions">
            <button
              class="ghost-button"
              type="button"
              @click="refreshNamespace()"
            >
              Refresh
            </button>
            <button
              class="button"
              type="button"
              :disabled="saving || !namespaceData"
              @click="saveSettings"
            >
              {{ saving ? "Saving..." : "Save namespace" }}
            </button>
          </div>
        </div>

        <div v-if="saveError" class="banner is-error">{{ saveError }}</div>
        <div v-if="saveMessage" class="banner is-success">
          {{ saveMessage }}
        </div>

        <div v-if="namespacePending" class="empty-state">
          Loading namespace details...
        </div>

        <div v-else-if="namespaceError" class="banner is-error">
          {{ detailFromError(namespaceError) }}
        </div>

        <div v-else-if="!namespaceData" class="empty-state">
          Select a namespace to inspect or update its settings.
        </div>

        <div v-else class="settings-grid">
          <article
            v-for="setting in namespaceData.settings"
            :key="setting.key"
            class="setting-card"
          >
            <div class="setting-header">
              <div>
                <h2 class="setting-title">{{ setting.title }}</h2>
                <p v-if="setting.description" class="setting-description">
                  {{ setting.description }}
                </p>
              </div>

              <div class="setting-badges">
                <span class="badge is-accent">{{ setting.value_type }}</span>
                <span class="badge">{{ setting.effective_source }}</span>
                <span v-if="setting.secret" class="badge">secret</span>
                <span v-if="!setting.editable" class="badge">read-only</span>
              </div>
            </div>

            <div class="setting-details">
              <div class="setting-detail">
                <div class="meta-label">Effective value</div>
                <div class="setting-detail-value">
                  {{ formatResolvedValue(setting) }}
                </div>
              </div>

              <div class="setting-detail">
                <div class="meta-label">Stored override</div>
                <div class="setting-detail-value">
                  {{ formatStoredValue(setting) }}
                </div>
              </div>

              <div class="setting-detail">
                <div class="meta-label">Default value</div>
                <div class="setting-detail-value">
                  {{
                    setting.secret
                      ? "Hidden"
                      : JSON.stringify(setting.default_value)
                  }}
                </div>
              </div>
            </div>

            <div v-if="setting.editable" class="form-grid">
              <div v-if="setting.value_type === 'boolean'" class="field">
                <label :for="setting.key">Value</label>
                <label class="checkbox-row" :for="setting.key">
                  <input
                    :id="setting.key"
                    v-model="draftValues[setting.key]"
                    type="checkbox"
                  />
                  <span>
                    {{ draftValues[setting.key] ? "Enabled" : "Disabled" }}
                  </span>
                </label>
              </div>

              <div
                v-else-if="setting.value_type === 'string_list'"
                class="field"
              >
                <label :for="setting.key">Comma-separated values</label>
                <textarea
                  :id="setting.key"
                  v-model="draftValues[setting.key]"
                  placeholder="alpha, beta, gamma"
                />
              </div>

              <div v-else class="field">
                <label :for="setting.key">Value</label>
                <input
                  v-if="setting.value_type === 'integer'"
                  :id="setting.key"
                  v-model.number="draftValues[setting.key]"
                  type="number"
                />
                <input
                  v-else
                  :id="setting.key"
                  v-model="draftValues[setting.key]"
                  :type="setting.secret ? 'password' : 'text'"
                  :placeholder="
                    setting.secret && setting.stored
                      ? 'Stored secret is hidden'
                      : ''
                  "
                />
              </div>
            </div>

            <div class="inline-actions">
              <button
                v-if="setting.stored && setting.editable"
                class="ghost-button"
                type="button"
                :disabled="resettingKey === setting.key"
                @click="resetStoredValue(setting.key)"
              >
                {{
                  resettingKey === setting.key
                    ? "Resetting..."
                    : "Reset stored override"
                }}
              </button>
            </div>
          </article>
        </div>
      </section>
    </section>
  </main>
</template>
