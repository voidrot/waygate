# waygate-plugin-communication-http

HTTP-based communication client plugin for submitting workflow trigger messages to worker runtimes.

## Configuration

Configuration lives under the plugin namespace:

- `WAYGATE_COMMUNICATION_HTTP__ENDPOINT`
- `WAYGATE_COMMUNICATION_HTTP__TIMEOUT_SECONDS`
- `WAYGATE_COMMUNICATION_HTTP__AUTH_TOKEN` (optional)
- `WAYGATE_COMMUNICATION_HTTP__AUTH_HEADER` (optional)
- `WAYGATE_COMMUNICATION_HTTP__WORKER_HOST` (worker-side listener bind host)
- `WAYGATE_COMMUNICATION_HTTP__WORKER_PORT` (worker-side listener bind port)
- `WAYGATE_COMMUNICATION_HTTP__WORKER_ENDPOINT_PATH` (worker-side listener path)

## Registration

This plugin registers under the `waygate.plugins.communication` entry point group and
exposes both the HTTP communication client and the worker-side HTTP listener companion.
