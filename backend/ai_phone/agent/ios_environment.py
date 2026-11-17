"""Read-only, bounded iOS host preflight. Never builds, signs or starts a device."""
from __future__ import annotations

import json
import platform
import subprocess
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path


def _run(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=8)
        return result.returncode, result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return -1, ""


def collect_ios_environment():
    # Rehello may be frequent on USB changes; do not repeatedly spawn tools.
    return _collect(int(time.monotonic() // 60))


@lru_cache(maxsize=1)
def _collect(_bucket):
    report = {"supported": platform.system() == "Darwin",
              "checked_at": datetime.now(timezone.utc).isoformat(),
              "checks": [], "runtimes": [], "device_types": []}
    if not report["supported"]:
        return report
    from ai_phone.config import get_settings
    settings = get_settings()
    checks = report["checks"]

    def check(key, ok, title, action):
        checks.append({"id": key, "status": "ok" if ok else "blocked",
                       "title": title, "next_step": "" if ok else action})

    code, version = _run(["xcodebuild", "-version"])
    xcode_ok = code == 0 and version.startswith("Xcode ")
    report["xcode_version"] = version.splitlines()[0][:80] if xcode_ok else ""
    check("xcode", xcode_ok, "完整 Xcode", "安装与 macOS 兼容的完整 Xcode，并选择其开发工具目录。")
    project = settings.wda_project_dir
    check("wda_project", bool(project and (Path(project) / "WebDriverAgent.xcodeproj").is_dir()),
          "WDA 工程", "配置包含 WebDriverAgent.xcodeproj 的工程目录。")
    if xcode_ok:
        for noun, key in (("runtimes", "runtimes"), ("devicetypes", "device_types")):
            code, output = _run(["xcrun", "simctl", "list", noun, "-j"])
            try:
                rows = json.loads(output).get(noun, []) if code == 0 else []
                report[key] = [{k: row[k] for k in ("identifier", "name", "version", "isAvailable", "supportedDeviceTypes") if k in row}
                               for row in rows if isinstance(row, dict)][:256]
                for row in report[key]:
                    if isinstance(row.get("supportedDeviceTypes"), list):
                        row["supportedDeviceTypes"] = [item.get("identifier", "") if isinstance(item, dict) else item
                                                       for item in row["supportedDeviceTypes"]]
            except (ValueError, TypeError, AttributeError):
                pass
    usable = [r for r in report["runtimes"] if r.get("isAvailable") is True and "iOS" in r.get("identifier", "")]
    check("simulator_runtime", bool(usable), "iOS 模拟器运行时", "在完整 Xcode 中安装一个目标 iOS runtime；模拟器不需要真机签名证书。")
    code, identities = _run(["security", "find-identity", "-v", "-p", "codesigning"])
    has_identity = code == 0 and any('"Apple Development:' in line or '"iPhone Developer:' in line for line in identities.splitlines())
    check("device_signing", has_identity and bool(settings.wda_team_id), "真机开发签名",
          "准备可用的开发证书与 Team 配置；此项仅用于真机，不阻塞模拟器。")
    return report
