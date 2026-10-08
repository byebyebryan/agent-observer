"""Private descriptor-anchored diagnostic digests for owned collection workers.

No session facts or provider data are cached. Only an unchanged open image
descriptor can reuse its digest; current path/process checks remain the caller's.
"""

from __future__ import annotations

import array
import fcntl
import json
import os
import re
import socket
import stat
from collections import OrderedDict
from collections.abc import MutableMapping

from .bounded_json import decode_document
from .native_artifacts import Artifact, _signature, historical_image

MAX_ENTRIES = 32
MAX_PACKET = 16384
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_INT_SIZE = array.array("i").itemsize


def _close(fds):
    for fd in set(fds):
        try:
            os.close(fd)
        except OSError:
            pass


def _check_fd(fd, signature):
    info = os.fstat(fd)
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid not in {0, os.geteuid()}
        or info.st_mode & 0o022
        or not 0 < info.st_size <= 512 * 1024 * 1024
        or flags & os.O_ACCMODE != os.O_RDONLY
        or flags & getattr(os, "O_PATH", 0)
        or _signature(info) != signature
    ):
        raise ValueError("image_memo_descriptor")


def _artifact(provider, digest):
    prior = historical_image(provider, digest)
    return Artifact(provider, prior.version if prior else "unknown", digest, "")


class ImageMemo(MutableMapping):
    def __init__(self, provider):
        if provider not in {"codex", "claude"}:
            raise ValueError("image_memo_scope")
        self.provider = provider
        self.entries = OrderedDict()

    def __len__(self):
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)

    def __getitem__(self, key):
        fd, artifact = self.entries[key]
        try:
            _check_fd(fd, key[1])
        except (ValueError, OSError):
            del self[key]
            raise KeyError(key) from None
        self.entries.move_to_end(key)
        return artifact

    def __setitem__(self, key, value):
        # A digest without its positively retained descriptor is never a memo.
        raise ValueError("image_memo_anchor_required")

    def __delitem__(self, key):
        fd, _ = self.entries.pop(key)
        _close([fd])

    def remember(self, fd, provider, signature, artifact):
        if (
            provider != self.provider
            or artifact.provider != provider
            or not _DIGEST.fullmatch(artifact.sha256)
        ):
            raise ValueError("image_memo_scope")
        anchor = os.dup(fd)
        try:
            _check_fd(anchor, signature)
        except BaseException:
            os.close(anchor)
            raise
        key = provider, signature
        if key in self.entries:
            del self[key]
        while len(self.entries) >= MAX_ENTRIES:
            del self[next(iter(self.entries))]
        self.entries[key] = anchor, _artifact(provider, artifact.sha256)

    def close(self):
        _close(fd for fd, _ in self.entries.values())
        self.entries.clear()

    def export(self):
        records, fds = [], []
        for key in list(self.entries):
            try:
                artifact = self[key]
            except KeyError:
                continue
            records.append({"signature": list(key[1]), "sha256": artifact.sha256})
            fds.append(self.entries[key][0])
        packet = json.dumps(
            {"imageMemo": 1, "provider": self.provider, "records": records}, separators=(",", ":")
        ).encode()
        if len(packet) > MAX_PACKET:
            raise ValueError("image_memo_limit")
        return packet, fds


def send(channel, memo):
    packet, fds = memo.export()
    ancillary = [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", fds))] if fds else []
    if channel.sendmsg([packet], ancillary) != len(packet):
        raise ValueError("image_memo_transfer")


def receive(channel, provider):
    memo = ImageMemo(provider)
    packet, ancillary, flags, _ = channel.recvmsg(
        MAX_PACKET, socket.CMSG_SPACE((MAX_ENTRIES + 1) * _INT_SIZE), socket.MSG_CMSG_CLOEXEC
    )
    fds, invalid = [], False
    for level, kind, data in ancillary:
        if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
            decoded = array.array("i")
            decoded.frombytes(data[: len(data) - len(data) % _INT_SIZE])
            fds.extend(decoded)
            invalid |= len(data) % _INT_SIZE != 0
        else:
            invalid = True
    remaining = set(fds)
    try:
        if (
            invalid
            or flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC)
            or len(fds) > MAX_ENTRIES
            or len(remaining) != len(fds)
        ):
            raise ValueError("image_memo_transfer")
        value = decode_document(packet, max_bytes=MAX_PACKET, max_depth=5, max_nodes=1024)
        if (
            not isinstance(value, dict)
            or set(value) != {"imageMemo", "provider", "records"}
            or type(value["imageMemo"]) is not int
            or value["imageMemo"] != 1
            or value["provider"] != provider
            or not isinstance(value["records"], list)
            or len(value["records"]) != len(fds)
        ):
            raise ValueError("image_memo_packet")
        for record, fd in zip(value["records"], fds, strict=True):
            if not isinstance(record, dict) or set(record) != {"signature", "sha256"}:
                raise ValueError("image_memo_record")
            signature, digest = record["signature"], record["sha256"]
            if (
                not isinstance(signature, list)
                or len(signature) != 7
                or any(type(v) is not int or not -(2**63) <= v < 2**64 for v in signature)
                or not isinstance(digest, str)
                or not _DIGEST.fullmatch(digest)
            ):
                raise ValueError("image_memo_record")
            signature = tuple(signature)
            key = provider, signature
            if key in memo.entries:
                raise ValueError("image_memo_duplicate")
            _check_fd(fd, signature)
            if os.get_inheritable(fd):
                raise ValueError("image_memo_descriptor")
            memo.entries[key] = fd, _artifact(provider, digest)
            remaining.remove(fd)
        return memo
    except BaseException:
        memo.close()
        _close(remaining)
        raise
