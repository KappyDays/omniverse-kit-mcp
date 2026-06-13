# USD Composer Asset Catalog

NVIDIA Omniverse's standard sample library (`omniverse-content-production` S3
bucket) to classify the assets visible in USD Composer's default content browser.

While `docs/assets/isaac/assets/` is the Isaac Sim 6.0 bundle-specific catalog, this directory
**Handles all assets** in the Composer area. Isaac Sim can also load from the same HTTPS URL.

S3 root: `https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/`

## Category table

| Category | catalog file | Representative uses |
|---|---|---|
| DigitalTwin | [`datacenter.md`](datacenter.md) | Data center — liquid cooling pipes, PDUs, server racks, network switches |

(This table is progressively expanded — ArchVis / Vegetation / Skies / Materials, etc. are added in subsequent turns)

## verification/sync

`/omniverse-asset-inventory-sync` skill also verifies .md in this directory
(Integrated with `docs/assets/isaac/assets/`). Automatic detection of URL 404/NET/5xx.
