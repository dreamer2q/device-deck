"""Optional browser mirror envelopes; Agent messages remain backward compatible.

APM1 + uint32 big-endian JSON-header length + UTF-8 header + raw media bytes.
Only a browser explicitly requesting mirror=binary-v1 receives these messages.
Logs, control messages and older clients keep their original JSON protocol.
"""
from __future__ import annotations

import base64
import binascii
import json
import struct
from typing import Any

MEDIA_TYPES = frozenset({"video_init", "video_segment", "mirror_jpeg", "h264_packet"})
MAGIC = b"APM1"
MAX_HEADER = 16 * 1024


def encode_mirror_message(payload: dict[str, Any]) -> bytes | None:
    if payload.get("type") not in MEDIA_TYPES or not isinstance(payload.get("data"), (str, bytes)):
        return None
    try:
        media = payload["data"] if isinstance(payload["data"], bytes) else base64.b64decode(payload["data"], validate=True)
    except (binascii.Error, ValueError):
        return None
    header = json.dumps(
        {key: value for key, value in payload.items() if key != "data"},
        ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    if len(header) > MAX_HEADER:
        return None
    return MAGIC + struct.pack(">I", len(header)) + header + media


def decode_mirror_message(raw: bytes) -> dict[str, Any]:
    if len(raw) < 8 or raw[:4] != MAGIC:
        raise ValueError("invalid media envelope")
    size = struct.unpack(">I", raw[4:8])[0]
    if not 0 < size <= MAX_HEADER or 8 + size > len(raw):
        raise ValueError("invalid media header")
    header = json.loads(raw[8:8+size])
    if not isinstance(header, dict) or header.get("type") not in MEDIA_TYPES:
        raise ValueError("invalid media type")
    return {**header, "data": raw[8+size:]}
