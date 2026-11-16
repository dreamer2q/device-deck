"""Device H.264 access units to WebCodecs, without host decoding/transcoding.

The scrcpy reader waits for delivery, bounding application memory. A slow peer
terminates the stream instead of silently dropping dependent H.264 packets.
"""
from __future__ import annotations

import asyncio
import threading
import time
import uuid

from ai_phone.agent.scrcpy_client import Client
from .h264 import sps_info


class RawMirrorSession:
    def __init__(self, serial, ws_client, loop, *, stream_id="", params=None):
        self.serial, self._ws, self._loop = serial, ws_client, loop
        self.stream_id = stream_id or uuid.uuid4().hex
        self._stopped = False
        self._scrcpy = None
        self._mirror_resolution = None
        self.display_rotation = None
        self._config = b""
        self._codec = "avc1.42e01f"
        self._gop = []
        self._gop_bytes = 0
        self._lock = threading.RLock()
        self._params = params or {}
        self._touch = None
        self._touch_owner = None

    def start(self):
        self._scrcpy = Client(device=self.serial, packet_mode=True,
            max_width=self._params.get("max_width", 1280),
            max_fps=self._params.get("max_fps", 30),
            bitrate=self._params.get("bitrate", 4_000_000))
        self._scrcpy.add_listener("packet", self._on_packet)
        self._scrcpy.add_listener("disconnect", self.stop)
        try:
            self._scrcpy.start(daemon_threaded=True)
        except Exception:
            self.stop()
            raise

    @property
    def control(self):
        return self._scrcpy.control if self._scrcpy else None

    @property
    def resolution(self):
        return self._mirror_resolution

    @property
    def is_alive(self):
        return bool(not self._stopped and self._scrcpy and self._scrcpy.alive)

    def get_device_size(self, driver):
        return driver.window_size()

    def invalidate_device_size(self):
        pass

    def touch(self, phase, x=0, y=0, width=0, height=0, stream_id="", owner=None):
        with self._lock:
            if phase == "cancel":
                if owner is not None and owner != self._touch_owner:
                    return
                if self._touch and self.control:
                    x, y, width, height = self._touch
                    self.control.touch_at(x, y, width, height, action=1)
                self._touch = None
                return
            if not self.is_alive or stream_id != self.stream_id or (width, height) != self.resolution:
                self.touch("cancel")
                raise ValueError("stale mirror geometry")
            if phase not in {"down", "move", "up"}:
                raise ValueError("invalid touch phase")
            if phase == "down":
                self.touch("cancel")
                self._touch_owner = owner
            elif not self._touch or owner != self._touch_owner:
                raise ValueError("touch has no down")
            x, y = max(0, min(width - 1, int(x))), max(0, min(height - 1, int(y)))
            self.control.touch_at(x, y, width, height, action={"down": 0, "move": 2, "up": 1}[phase])
            self._touch = None if phase == "up" else (x, y, width, height)

    def stop(self):
        with self._lock:
            if self._stopped:
                return
            self.touch("cancel")
            self._stopped = True
            if self._scrcpy:
                self._scrcpy.stop()
            self._gop.clear()

    def _send(self, payload):
        if not self._stopped:
            future = asyncio.run_coroutine_threadsafe(self._ws.send(payload), self._loop)
            if not future.result(timeout=2):
                raise ConnectionError("mirror transport unavailable")

    def _on_packet(self, data, pts, config, keyframe):
        try:
            with self._lock:
                if self._stopped:
                    return
                if config:
                    info = sps_info(data)
                    if info:
                        self.touch("cancel")
                        self._codec, w, h = info
                        self._mirror_resolution = (w, h)
                        self._config = data
                        self._gop.clear()
                        self._gop_bytes = 0
                    return
                if not self._config or not self.resolution:
                    return
                w, h = self.resolution
                payload = {"type": "h264_packet", "serial": self.serial,
                    "stream_id": self.stream_id, "codec": self._codec,
                    "width": w, "height": h, "pts": pts, "key": bool(keyframe),
                    "ts": time.time(), "data": self._config + data if keyframe else data}
                if keyframe:
                    self._gop = []
                    self._gop_bytes = 0
                if keyframe or self._gop:
                    self._gop.append(payload)
                    self._gop_bytes += len(payload["data"])
                    if self._gop_bytes > 4 * 1024 * 1024 or len(self._gop) > 150:
                        self._gop.clear()
                        self._gop_bytes = 0
                self._send(payload)
        except Exception:
            self.stop()

    def replay_init(self):
        # Called in a worker thread; the same lock preserves packet order.
        with self._lock:
            for payload in self._gop:
                self._send(payload)
