"""Required native contracts; provider release labels never select support.

These describe the narrow semantics used by the existing metadata projection.
Shape checks happen in each adapter before facts are accepted. A new variant
does not inherit the meaning of a known one. Native conformance is recorded
separately from these declarations; physical executable identity is independent.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class NativeContract:
    name: str
    provider: str
    requirements: tuple[str, ...]


CODEX_READ = NativeContract("codex_managed_metadata_v1", "codex", (
    "existing_owned_endpoint", "initialize_exact_codex_home", "bounded_inventory_pages",
    "exact_thread_and_session_uuids", "known_status_and_active_flag_semantics",
    "latest_turn_metadata_without_items", "native_unix_second_turn_clocks",
))
CODEX_ENTRY = NativeContract("codex_tty_entry_v1", "codex", (
    "native_tty", "codex_home_selector", "resume_all_exact_session_uuid",
    "native_permission_and_trust_handling",
))
CONTRACTS = (CODEX_READ, CODEX_ENTRY)
