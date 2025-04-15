"""Command-line interface for offline JSON analysis."""
import argparse
import json
from pathlib import Path
import sys
from .core import analyze


def reject_constant(value):
    raise ValueError("Non-finite numbers are not JSON")


def main(argv=None):
    parser = argparse.ArgumentParser(description='Report quota headroom from exported Compute Engine region or project JSON.')
    parser.add_argument("input", help="JSON input path, or - for stdin")
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    parser.add_argument("--fail-on-findings", action="store_true", help="exit 1 when attention is required")
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        result = analyze(json.loads(raw, parse_constant=reject_constant))
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
        # Do not echo malformed input: exports can contain sensitive values.
        print(f"Invalid input ({type(exc).__name__}); check the documented input schema.", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    else:
        print("Attention required" if result["attention_required"] else "No findings in supplied data")
        for key, value in result.items():
            if key != "attention_required":
                print(f"{key}: {json.dumps(value, sort_keys=True, allow_nan=False)}")
    return 1 if args.fail_on_findings and result["attention_required"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
