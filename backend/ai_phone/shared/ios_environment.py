"""Whitelist the non-secret host environment reported by Agents."""


def safe_ios_environment(value):
    if not isinstance(value, dict):
        return {}
    result = {"supported": value.get("supported") is True}
    for key in ("checked_at", "xcode_version"):
        if isinstance(value.get(key), str):
            result[key] = value[key][:100]
    result["checks"] = [
        {key: str(row.get(key, ""))[:400] for key in ("id", "status", "title", "next_step")}
        for row in value.get("checks", [])[:20] if isinstance(row, dict)
    ] if isinstance(value.get("checks"), list) else []
    for key in ("runtimes", "device_types"):
        rows = value.get(key)
        result[key] = []
        if not isinstance(rows, list):
            continue
        for row in rows[:256]:
            if not isinstance(row, dict):
                continue
            clean = {field: row[field][:255] for field in ("identifier", "name", "version") if isinstance(row.get(field), str)}
            if isinstance(row.get("isAvailable"), bool):
                clean["isAvailable"] = row["isAvailable"]
            # Runtime-native compatibility metadata is used only when present.
            types = row.get("supportedDeviceTypes")
            if isinstance(types, list):
                clean["supportedDeviceTypes"] = [x[:255] for x in types[:256] if isinstance(x, str)]
            result[key].append(clean)
    return result
