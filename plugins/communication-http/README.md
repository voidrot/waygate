# waygate-plugin-communication-http

HTTP-based communication client plugin for submitting workflow trigger messages to worker runtimes.

## Configuration

Configuration lives under the plugin namespace:

- `WAYGATE_COMMUNICATION_HTTP__ENDPOINT`
- `WAYGATE_COMMUNICATION_HTTP__TIMEOUT_SECONDS`
- `WAYGATE_COMMUNICATION_HTTP__AUTH_TOKEN` (optional)
- `WAYGATE_COMMUNICATION_HTTP__AUTH_HEADER` (optional)

## Registration

This plugin registers under the `waygate.plugins.communication` entry point group.
