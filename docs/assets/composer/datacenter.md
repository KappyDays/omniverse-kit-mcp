# Datacenter — USD Composer Asset Catalog

`$DT` = `https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/DigitalTwin/Assets`

Root: `$DT/Datacenter/`

Assets for data center simulation. Infrastructure components such as liquid cooling pipes / power distribution / server racks.

## Folder organization (6 sub-folders)

| folder | Representative USD | explanation |
|---|---|---|
| **Liquid_Cooling/Data_Hall** | `Liquid_Cooling/Data_Hall/DCP_A/DCP_A_01.usd` ✓ | Data Center Pipe (DCP) — Liquid cooling pipeline |
| **Power_Distribution/Controllers** | `Power_Distribution/Controllers/PDU_A/rPDU_A_01.usd` ✓ | Rack PDU (Power Distribution Unit) — Server rack wire distribution |
| Facilities | — | Data center facility (requires drilldown) |
| Network_Switches | — | Network switch (requires drilldown) |
| Racks | — | Server rack skeleton (requires drilldown) |
| Server_Nodes | — | Server node (requires drilldown) |

## Example of use
- **Pipe / When you need wires**: `DCP_A_01.usd` (pipe), `rPDU_A_01.usd` (collection of wires)
- Entire data center environment: Assemble the USD in the above 6 folders as a reference

## drilldown incomplete items
`✓` Unattached rows only check sub-folders, and the representative USD is not specified. In subsequent catalog turns
After an additional walk with `content_browse`, it is confirmed as `✓`.
