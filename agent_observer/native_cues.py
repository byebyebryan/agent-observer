"""Pinned Claude 2.1.287 native launch cues, without retaining native output."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .contract import ContractError

_SGR = re.compile(r"\x1b\[(?:[0-9]{1,3}(?:;[0-9]{1,3}){0,15})?m")
_BACKGROUND = re.compile(r"backgrounded · ([0-9a-f]{8})(?: .{0,400})?\Z", re.ASCII)
_ATTACH = re.compile(r" {2}claude attach ([0-9a-f]{8}) +open in this terminal *\Z", re.ASCII)
_ID = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
_NOTE_ID = rf"(?:{_ID}|[0-9a-f]{{8}})"
_COPY_NOTE = re.compile(
    rf"note: session ({_NOTE_ID}) is already running in the background, so this started a copy as ({_NOTE_ID})\. `claude attach ([0-9a-f]{{8}})` opens the original\.\Z",
    re.ASCII,
)


@dataclass(frozen=True)
class BackgroundReceipt:
    job_id: str
    session_id: str | None = None
    origin_id: str | None = None


def _clean(data):
    if len(data) > 128 * 1024:
        raise ContractError("native_cue_limit")
    try:
        value = _SGR.sub("", data.decode("utf-8", "strict"))
    except UnicodeError:
        raise ContractError("native_cue_encoding") from None
    value = value.replace("\r\n", "\n")
    if any(unicodedata.category(char).startswith("C") and char != "\n" for char in value):
        raise ContractError("native_cue_controls")
    return value


def background_receipt(data):
    value = _clean(data)
    background = set()
    attachments = []
    copies = []
    for line in value.split("\n"):
        if len(line) > 512:
            raise ContractError("native_cue_line_limit")
        copied = _COPY_NOTE.fullmatch(line)
        if copied is not None:
            copies.append(copied.groups())
            continue
        if "backgrounded" in line:
            match = _BACKGROUND.fullmatch(line)
            if match is None:
                raise ContractError("native_cue_format")
            background.add(match[1])
        if "claude attach" in line:
            match = _ATTACH.fullmatch(line)
            if match is None:
                raise ContractError("native_cue_format")
            attachments.append(match[1])
    if len(background) != 1 or len(attachments) != 1 or attachments[0] not in background:
        raise ContractError("native_cue_ambiguous")
    if not copies:
        return BackgroundReceipt(attachments[0])
    if len(copies) != 1:
        raise ContractError("native_cue_ambiguous")
    origin, actual, original_job = copies[0]
    if origin[:8] == actual[:8] or original_job != origin[:8] or attachments[0] != actual[:8]:
        raise ContractError("native_cue_identity_conflict")
    return BackgroundReceipt(attachments[0], actual if len(actual) == 36 else None, origin)


def background_job(data):
    return background_receipt(data).job_id


def trust_required(data, cwd):
    try:
        value = _clean(data).strip("\n")
    except ContractError:
        return False
    expected = f"Workspace not trusted. Run `claude` in {cwd} once and accept the trust prompt, then retry."
    return value == expected
