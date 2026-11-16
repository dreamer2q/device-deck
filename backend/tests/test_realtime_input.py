import asyncio
import struct
from unittest.mock import Mock

import pytest

from ai_phone.server.lockstore import DeviceLockStore
from ai_phone.server.ws.realtime import RealtimeInput
from ai_phone.shared.mirror_wire import decode_mirror_message, encode_mirror_message
from ai_phone.agent.mirror.raw import RawMirrorSession


class Hub:
    def __init__(self):
        self.sent = []

    async def send_to_serial(self, serial, data):
        self.sent.append(data)
        return True


async def fixture():
    hub, store = Hub(), DeviceLockStore()
    lease = await store.acquire("phone", "human", "session")
    channel = RealtimeInput(hub, store, "phone")
    def message(phase="down", seq=1, **changes):
        return {"phase": phase, "seq": seq, "lock_token": lease.token,
            "x": 20, "y": 30, "width": 720, "height": 1280, "stream_id": "stream", **changes}
    return hub, store, lease, channel, message


@pytest.mark.asyncio
async def test_continuous_input_arrives_before_up_and_retains_order():
    hub, _, _, channel, message = await fixture()
    for seq, phase in enumerate(["down", "move", "move", "up"], 1):
        assert (await channel.handle(message(phase, seq)))["ok"]
        assert len(hub.sent) == seq  # down/move don't wait for a later up
    assert [m["params"]["phase"] for m in hub.sent] == ["down", "move", "move", "up"]
    assert channel.active is None


@pytest.mark.asyncio
async def test_released_lease_rejects_existing_channel_and_cancels_touch():
    hub, store, lease, channel, message = await fixture()
    await channel.handle(message())
    await store.release("phone", lease.token)
    result = await channel.handle(message("move", 2))
    assert not result["ok"] and result["reason"] == "lease_lost"
    assert hub.sent[-1]["params"] == {"phase": "cancel", "owner": lease.token}
    assert len(hub.sent) == 2


@pytest.mark.asyncio
async def test_expiry_cancels_even_without_more_client_messages():
    hub, store, lease, channel, message = await fixture()
    await channel.handle(message())
    lease.last_heartbeat_at -= lease.ttl_seconds + 1
    task = asyncio.create_task(channel.watch())
    await asyncio.sleep(0.3)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert hub.sent[-1]["params"]["phase"] == "cancel"
    assert channel.active is None


@pytest.mark.asyncio
async def test_invalid_duplicate_and_missing_down_do_not_reach_device():
    hub, _, _, channel, message = await fixture()
    assert not (await channel.handle(message("move")))["ok"]
    assert not (await channel.handle(message(x=-1)))["ok"]
    assert not hub.sent
    assert (await channel.handle(message(seq=2)))["ok"]
    assert not (await channel.handle(message("move", 2)))["ok"]
    assert len(hub.sent) == 1


def test_binary_packet_preserves_pts_and_payload_without_base64():
    packet = {"type": "h264_packet", "serial": "phone", "key": True,
        "pts": 123456, "data": bytes(range(256))}
    wire = encode_mirror_message(packet)
    assert decode_mirror_message(wire) == packet
    for bad in [b"", b"BAD!" + wire[4:], b"APM1" + struct.pack(">I", 17000)]:
        with pytest.raises(ValueError):
            decode_mirror_message(bad)


def test_old_channel_cancel_cannot_release_new_owners_touch():
    session = RawMirrorSession("phone", None, None, stream_id="stream")
    session._scrcpy = Mock(alive=True)
    session._mirror_resolution = (720, 1280)
    session.touch("down", 1, 2, 720, 1280, "stream", "first")
    session.touch("down", 3, 4, 720, 1280, "stream", "second")
    before = session.control.touch_at.call_count
    session.touch("cancel", owner="first")
    assert session.control.touch_at.call_count == before
    assert session._touch == (3, 4, 720, 1280)
    session.touch("cancel", owner="second")
    assert session.control.touch_at.call_args.kwargs["action"] == 1


def test_stale_rotation_releases_held_pointer():
    session = RawMirrorSession("phone", None, None, stream_id="stream")
    session._scrcpy = Mock(alive=True)
    session._mirror_resolution = (720, 1280)
    session.touch("down", 1, 2, 720, 1280, "stream", "owner")
    session._mirror_resolution = (1280, 720)
    with pytest.raises(ValueError):
        session.touch("move", 2, 3, 720, 1280, "stream", "owner")
    assert session._touch is None
