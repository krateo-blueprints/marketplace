#!/usr/bin/env python3
"""Regenerate the bundled catalog indexes.

Fetches the two live Helm-repo indexes (blueprints + operators), CURATES out the platform-component
leftovers that are not installable blueprints, and writes them as compact JSON into
`krateo-marketplace-catalog/files/{blueprints,operators}-index.json`.

WHY JSON (not the raw YAML): the installer bootstrap wave copies these files verbatim into a
ConfigMap, and the portal reads `.data["<name>-index.json"] | fromjson` over the k8s API — snowplow
does NOT YAML->JSON an in-cluster ConfigMap read (that path is external-endpointRef only), and jq has
no fromyaml. So the catalog must be stored as JSON.

WHY as-is urls: entries keep their own `urls[]` (mostly the krateo-blueprints Helm repo); per-chart
OCI pullability is not uniform, so we do NOT rewrite urls[] to oci://. Air-gap mirrorability is handled
downstream by the installer's registries[] source->mirror base-rewrite, not by assuming pullable OCI.

Run from the repo root:  python3 hack/build-index.py
"""
import json
import os
import sys
import urllib.request

import yaml  # PyYAML

BASE = os.environ.get("CATALOG_BASE", "https://krateo-blueprints.github.io/charts")
OUT = os.path.join(os.path.dirname(__file__), "..", "krateo-marketplace-catalog", "files")

# Platform components that live in the same Helm repo but are NOT installable blueprints — they are
# the platform's own charts (engine, portal, agents, operators). They must not appear as marketplace
# tiles. Keep this list in sync if platform charts are (de)published to the blueprints repo.
PLATFORM_LEAVES = {
    "clickhouse-mcp-server", "clickhouse-operator", "fetch-mcp-server", "hyperdx-provider",
    "installer", "kagent", "krateo-ansible-to-operator-agent", "krateo-authn", "krateo-autopilot",
    "krateo-code-analysis-agent", "krateo-core-provider", "krateo-frontend", "krateo-oasgen-provider",
    "krateo-snowplow", "krateo-tf-provider-to-operator-agent", "krateo-tf-to-helm-agent",
    "mongodb-operator", "portal",
}


def build(sub, fn):
    raw = urllib.request.urlopen(f"{BASE}/{sub}/index.yaml", timeout=30).read()
    idx = yaml.safe_load(raw)
    entries = idx.get("entries", {})
    before = len(entries)
    removed = sorted(k for k in list(entries) if k in PLATFORM_LEAVES)
    for k in removed:
        del entries[k]
    os.makedirs(OUT, exist_ok=True)
    payload = json.dumps(idx, separators=(",", ":"), sort_keys=True)
    with open(os.path.join(OUT, fn), "w") as f:
        f.write(payload)
    print(f"  {sub}: {before} -> {len(entries)} entries (curated {len(removed)}) | {fn} {len(payload)} bytes")
    return len(payload)


def main():
    total = 0
    total += build("blueprints", "blueprints-index.json")
    total += build("operators", "operators-index.json")
    # k8s ConfigMap hard limit is 1 MiB across all keys + metadata; warn well before.
    limit = 1024 * 1024
    print(f"  combined: {total} bytes ({100 * total // limit}% of the 1 MiB ConfigMap limit)")
    if total > int(limit * 0.8):
        print("  WARN: catalog is >80% of the ConfigMap limit — prune fields or split per-source", file=sys.stderr)


if __name__ == "__main__":
    main()
