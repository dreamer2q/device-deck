"""Lease checked continuous Android input on the browser's existing socket."""
from __future__ import annotations

import asyncio
import secrets
from typing import Literal

from pydantic import BaseModel, Field


class Touch(BaseModel):
    phase: Literal["down", "move", "up", "cancel"]
    x: int = Field(default=0, ge=0, le=16384)
    y: int = Field(default=0, ge=0, le=16384)
    width: int = Field(ge=1, le=16384)
    height: int = Field(ge=1, le=16384)
    stream_id: str = Field(min_length=1, max_length=128)
    lock_token: str = Field(min_length=1, max_length=256)
    seq: int = Field(ge=0)


class RealtimeInput:
    def __init__(self, hub, store, serial):
        self.hub, self.store, self.serial = hub, store, serial
        self.active = None
        self.last_seq = -1

    async def cancel(self):
        active, self.active = self.active, None
        if active:
            await self.hub.send_to_serial(self.serial, {"type": "input", "serial": self.serial,
                "kind": "realtime_touch", "params": {"phase": "cancel", "owner": active}})

    async def handle(self, data):
        try:
            touch = Touch.model_validate(data)
        except ValueError:
            return {"type": "input_ack", "ok": False, "reason": "invalid_input"}
        lock = self.store.peek(self.serial)
        if lock is None or not secrets.compare_digest(lock.token, touch.lock_token):
            await self.cancel()
            return {"type": "input_ack", "ok": False, "reason": "lease_lost", "seq": touch.seq}
        if touch.seq <= self.last_seq:
            return {"type": "input_ack", "ok": False, "reason": "stale_sequence", "seq": touch.seq}
        self.last_seq = touch.seq
        if touch.phase in {"move", "up"} and self.active != lock.token:
            return {"type": "input_ack", "ok": False, "reason": "missing_down", "seq": touch.seq}
        if touch.phase == "down":
            await self.cancel()
            self.active = lock.token
        params = touch.model_dump(exclude={"seq", "lock_token"})
        params["owner"] = lock.token
        sent = await self.hub.send_to_serial(self.serial,
            {"type": "input", "serial": self.serial, "kind": "realtime_touch", "params": params})
        if touch.phase in {"up", "cancel"}:
            self.active = None
        return {"type": "input_ack", "ok": sent, "seq": touch.seq,
            "stage": "server_dispatch"}

    async def watch(self):
        try:
            while True:
                await asyncio.sleep(0.25)
                if self.active:
                    lock = self.store.peek(self.serial)
                    if lock is None or lock.token != self.active:
                        await self.cancel()
        finally:
            await self.cancel()
