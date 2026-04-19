"""Public entry points for the WayGate core package.

This package exposes the application bootstrap helpers used by the apps and
the core package version metadata used by release tooling.
"""

from .bootstrap import bootstrap_app, get_app_context

__VERSION__ = "0.1.0"  # x-release-please-version

__all__ = ["bootstrap_app", "get_app_context"]
