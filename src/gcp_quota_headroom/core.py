"""Offline quota utilization analysis of Compute Engine exports."""
import math


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite non-negative number")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{label} must be a finite non-negative number")
    return float(value)


def analyze(data):
    """Accept a region/project object, list, or REST regions.list response."""
    if isinstance(data, dict) and data.get("nextPageToken"):
        raise ValueError("Incomplete paginated export: combine every page first")
    if isinstance(data, dict):
        resources = data.get("items", [data])
    else:
        resources = data
    if not isinstance(resources, list):
        raise ValueError("Expected a resource object, list, or items array")
    findings = []
    seen = set()
    for resource in resources:
        if not isinstance(resource, dict) or "quotas" not in resource:
            raise ValueError("Every resource must contain a quotas array")
        scope = resource.get("selfLink") or resource.get("name")
        if not isinstance(scope, str) or not scope:
            raise ValueError("Every resource needs a name or selfLink")
        quotas = resource["quotas"]
        if not isinstance(quotas, list):
            raise ValueError("quotas must be an array")
        for q in quotas:
            if not isinstance(q, dict) or not isinstance(q.get("metric"), str) or not q["metric"]:
                raise ValueError("Every quota needs a metric")
            key = (scope, q["metric"])
            if key in seen:
                raise ValueError(f"Duplicate quota: {scope}/{q['metric']}")
            seen.add(key)
            used = number(q.get("usage"), "usage")
            limit = number(q.get("limit"), "limit")
            percent = used / limit * 100 if limit else None
            if percent is not None and not math.isfinite(percent):
                raise ValueError("Utilization exceeds representable range")
            # Zero limit with zero usage is unavailable capacity, not healthy headroom.
            severity = "critical" if not limit or used >= limit else "warning" if percent >= 80 else "ok"
            findings.append({"scope": scope, "metric": q["metric"], "usage": used,
                             "limit": limit, "remaining": max(0.0, limit - used),
                             "over_limit": max(0.0, used - limit),
                             "used_percent": round(percent, 2) if percent is not None else None,
                             "severity": severity})
    order = {"critical": 0, "warning": 1, "ok": 2}
    findings.sort(key=lambda r: (order[r["severity"]], r["scope"], r["metric"]))
    return {"resources_checked": len(resources), "quotas_checked": len(findings),
            "findings": findings,
            "attention_required": any(f["severity"] != "ok" for f in findings)}
