# CHANGELOG — omni.sdg_mcp.dataset_gen

## [0.1.0] - 2026-05-26

- Initial scaffold (headless-verified). Warehouse env + 3 labeled real props (forklift/bin/pallet) +
  3-camera ring authored via usd-core. Replicator graph (randomize pose/material/light + RGB/depth/
  semantic+instance seg/2D+3D bbox annotators + BasicWriter) wired for the live session.
- Headless: USD authoring + idempotency + units pass. Live (Replicator orchestration, RTX Lidar,
  annotator readout) verified in a workspaces/isaac session — see mcp-upgrade/make_progress/sdg_make.md.
