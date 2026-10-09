"""Pure provider vocabulary; reserved profiles do not enable native adapters."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderProfile:
    display_name: str
    runtime_scope: str


PROFILES = {
    "codex": ProviderProfile("Codex", "daemon_threads"),
    "claude": ProviderProfile("Claude", "provider_sessions"),
}


def profile_for(provider):
    try:
        return PROFILES[provider]
    except (KeyError, TypeError):
        raise ValueError("invalid_provider_selection") from None
