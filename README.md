# gcp-quota-headroom

Report quota headroom from exported Compute Engine region or project JSON.

**Status: working offline CLI.** Reads exported JSON only. No credentials, network access, or cloud changes. Requires Python 3.10+; no runtime dependencies.

## Install and try

```bash
pip install git+https://github.com/narayana006/gcp-quota-headroom
```

Clone this repository for the fictional sample inventory, then run:

```bash
gcp-quota-headroom examples/input.json --json
```

The actual sample output is captured in [examples/output.json](examples/output.json).

```bash
cat examples/input.json | gcp-quota-headroom - --json
gcp-quota-headroom examples/input.json --fail-on-findings
```

Exit codes: `0` for a completed report; `1` for findings when `--fail-on-findings` is supplied; `2` for invalid input or an unreadable file. Without the failure flag, findings do not cause a nonzero exit. `--json` emits stable JSON; text output is available by omitting it. Invalid input is rejected without echoing its contents.

## Input and interpretation

Accepts the JSON object returned by Compute Engine `regions.get` or `projects.get`, an array of those objects, or a `regions.list` object containing `items`. A non-empty `nextPageToken` is rejected. Pass all pages yourself: the tool does not follow pagination. Include a unique `name` or `selfLink` on every resource. A single export should cover one project; use `selfLink` to disambiguate mixed-project input.

Quotas at 80% utilization are warnings; at or above the limit they are critical. A zero limit is critical even when usage is zero. Remaining capacity is clamped at zero; `over_limit` records excess usage. The report measures the supplied snapshot only: it does not predict capacity, request increases, or measure service availability. Empty exports explicitly report zero quotas checked.

Reference: [Compute Engine regions resource](https://docs.cloud.google.com/compute/docs/reference/rest/v1/regions). Only the `name`, `selfLink`, and `quotas` fields are used.

## Shipped features

- [x] Region/project quota parsing with finite non-negative number validation
- [x] Deterministic utilization ranking, zero-limit and over-limit detection
- [x] Text/JSON reports, stdin and CI failure mode

## Limits

No live collection, pagination, quota changes, cost estimates, or forecasting. This covers Compute Engine allocation quota exports, not arbitrary Cloud Quotas or Monitoring responses.

## Development and contributing

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

Issues and focused pull requests are welcome. Include fictional input and a regression test when reporting parsing or analysis errors. Never include credentials or private exports.

Built and maintained by [Narayana Vemburaj](https://github.com/narayana006).

[MIT license](LICENSE).
