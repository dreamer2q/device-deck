from types import SimpleNamespace
import pytest

from ai_phone.agent import ios_environment as env
from ai_phone.shared.ios_environment import safe_ios_environment


@pytest.fixture(autouse=True)
def clear_preflight_cache():
    env._collect.cache_clear()
    yield
    env._collect.cache_clear()


def test_non_mac_preflight_never_runs_native_tools(monkeypatch):
    env._collect.cache_clear()
    monkeypatch.setattr(env.platform, "system", lambda: "Linux")
    monkeypatch.setattr(env, "_run", lambda _: (_ for _ in ()).throw(AssertionError("native tool")))
    assert env.collect_ios_environment()["supported"] is False


def test_missing_xcode_and_signing_remain_independent(monkeypatch, tmp_path):
    import ai_phone.config as config
    env._collect.cache_clear()
    monkeypatch.setattr(env.platform, "system", lambda: "Darwin")
    project = tmp_path / "WebDriverAgent.xcodeproj"
    project.mkdir()
    monkeypatch.setattr(config, "get_settings", lambda: SimpleNamespace(wda_project_dir=tmp_path, wda_team_id=None))
    calls = []
    def run(args):
        calls.append(args)
        return (1, "") if args[0] == "xcodebuild" else (0, "0 valid identities found")
    monkeypatch.setattr(env, "_run", run)
    report = env.collect_ios_environment()
    checks = {c["id"]: c["status"] for c in report["checks"]}
    assert checks == {"xcode": "blocked", "wda_project": "ok", "simulator_runtime": "blocked", "device_signing": "blocked"}
    assert all("simctl" not in c for c in calls)
    assert env.collect_ios_environment() == report
    assert len(calls) == 2  # USB rehello does not repeat preflight in the same minute.


def test_reports_cannot_export_keys_or_raw_certificate_identity():
    clean = safe_ios_environment({"supported": True, "secret": "must-not-export",
        "checks": [{"id": "xcode", "status": "ok", "title": "Xcode", "private_key": "secret"}],
        "runtimes": [{"identifier": "runtime", "name": "iOS", "isAvailable": True, "token": "secret"}],
        "device_types": "invalid"})
    assert "secret" not in repr(clean)
    assert clean["device_types"] == []
    assert clean["runtimes"][0]["isAvailable"] is True
    assert safe_ios_environment(None) == {}
