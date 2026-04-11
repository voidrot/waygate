from waygate_core.plugin import PluginRegistry, PluginGroups, WebhookPlugin

webhook_registry = PluginRegistry(PluginGroups.WEBHOOKS, WebhookPlugin)

webhook_registry.register_plugins()
