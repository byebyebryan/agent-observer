"""Single passive native dispatch boundary; imports alone perform no native I/O."""

from dataclasses import dataclass

from .provider import profile_for


@dataclass(frozen=True)
class CodexAdapter:
    provider: str = "codex"

    @property
    def profile(self):
        return profile_for(self.provider)

    def validate_selector(self, home, selector):
        if selector != "explicit" or not home.is_absolute():
            raise ValueError("adapter_selector_invalid")

    def collect(self, home, *, host_scope, include_history=True, image_cache=None):
        self.validate_selector(home, "explicit")
        from .codex_snapshot import collect_codex

        return collect_codex(home, host_scope=host_scope, include_history=include_history,
                             **({"image_cache": image_cache} if image_cache is not None else {}))

    def listen(self, home, emitter):
        self.validate_selector(home, "explicit")
        from .codex_hints import run

        return run(home, emitter)


_ADAPTERS = {"codex": CodexAdapter()}


def adapter_for(provider):
    # Common/reserved provider vocabulary never grants native implementation.
    profile_for(provider)
    if provider not in _ADAPTERS:
        raise ValueError("unsupported_provider")
    return _ADAPTERS[provider]


def select_adapters(providers):
    if not providers or len(set(providers)) != len(providers):
        raise ValueError("invalid_provider_selection")
    return [adapter_for(provider) for provider in providers]
