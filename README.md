# krateo-blueprints/marketplace

The Krateo marketplace **catalog** — the curated blueprint + operator index, packaged as a data-only
OCI Helm artifact so it can be pulled **in-cluster** into a ConfigMap and served to the portal, with
**no external GitHub-Pages fetch** at portal runtime.

## What this is (and is not)
- **Is:** `krateo-marketplace-catalog/` — a template-less, image-less Helm chart whose only payload is
  two files, `files/blueprints-index.json` and `files/operators-index.json` (Helm v1 repo indexes,
  one entry per installable Composition, stored as compact JSON).
- **Is not:** the blueprint *content*. The charts themselves live in `krateo-blueprints/*` and are
  published to `oci://ghcr.io/krateo-blueprints/charts` + the `krateo-blueprints.github.io/charts` Helm
  repo. This repo only indexes them.

## Why JSON, why in-cluster
The installer's catalog bootstrap wave `helm pull`s this chart and copies the two JSON files into a
ConfigMap (`blueprints-catalog-index`). The portal reads `.data["<name>-index.json"] | fromjson` over
the k8s API. snowplow does **not** YAML→JSON an in-cluster ConfigMap read (that conversion is external-
`endpointRef` only) and jq has no `fromyaml`, so the catalog must be **JSON**. Serving from a ConfigMap
removes the runtime dependency on an external Pages host and makes the marketplace work behind a mirror.

## Curation
`hack/build-index.py` regenerates the two JSON files from the live indexes and **removes platform-
component leftovers** (the engine/portal/agents/operators charts that share the blueprints Helm repo but
are not installable blueprints — see `PLATFORM_LEAVES` in the script). Entry `urls[]` are kept **as-is**;
air-gap mirrorability is handled downstream by the installer's `registries[]` source→mirror base-rewrite,
not by rewriting urls here.

## Regenerate
```
python3 hack/build-index.py        # refetch live indexes, curate, rewrite the two JSON files
```

## Release
Tag a semver (`X.Y.Z`); `.github/workflows/release-tag.yaml` stamps the `CHART_VERSION` placeholder and
publishes `oci://ghcr.io/krateo-blueprints/charts/krateo-marketplace-catalog:X.Y.Z`. The installer pins
that version and pulls it via the same `registries[]` credential it already uses for krateo-blueprints.
