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
CLAUDE_READ = NativeContract("claude_registry_job_metadata_v1", "claude", (
    "owned_stable_registry_and_job_directories", "exact_session_and_job_ids",
    "worker_pid_domain_and_start_token", "configured_provider_executable_locator",
    "known_status_and_wait_semantics", "terminal_clock_and_pending_work_predicates",
))
CODEX_ENTRY = NativeContract("codex_tty_entry_v1", "codex", (
    "native_tty", "codex_home_selector", "resume_all_exact_session_uuid",
    "native_permission_and_trust_handling",
))
CLAUDE_ENTRY = NativeContract("claude_background_attach_v1", "claude", (
    "config_home_selector", "background_launch_with_closed_stdin",
    "settings_bg_isolation_none", "exact_saved_resume_uuid",
    "bounded_typed_launch_receipt", "exact_job_attach", "native_tty",
))
CONTRACTS = (CODEX_READ, CLAUDE_READ, CODEX_ENTRY, CLAUDE_ENTRY)


def claude_registry_capabilities(record):
    """For a verified worker; never a substitute for its identity recheck."""
    if (
        record.get("kind") not in {"interactive", "bg"}
        or record.get("status") not in {"busy", "shell", "idle", "waiting"}
        or record.get("statusUpdatedAt") is None
        or record.get("procStart") is None or record.get("pidDomain") is None
    ):
        return []
    capabilities = ["registry_phase", "input_wait"]
    if record["kind"] == "interactive" and record.get("jobId") is None:
        capabilities.append("interactive_readiness")
    if record.get("questionWait") is True and record["status"] == "waiting":
        capabilities.append("job_question")
        if record["kind"] == "interactive" and record.get("jobId") is None:
            capabilities.append("foreground_question")
    return capabilities
