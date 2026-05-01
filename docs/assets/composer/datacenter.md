# Datacenter — USD Composer Asset Catalog

`$DT` = `https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/DigitalTwin/Assets`

루트: `$DT/Datacenter/`

데이터센터 시뮬레이션용 자산. 액체냉각 파이프 / 전원 분배 / 서버 랙 등 인프라 구성요소.

## 폴더 구성 (6 sub-folders)

| 폴더 | 대표 USD | 설명 |
|---|---|---|
| **Liquid_Cooling/Data_Hall** | `Liquid_Cooling/Data_Hall/DCP_A/DCP_A_01.usd` ✓ | Data Center Pipe (DCP) — 액체냉각 파이프 라인 |
| **Power_Distribution/Controllers** | `Power_Distribution/Controllers/PDU_A/rPDU_A_01.usd` ✓ | Rack PDU (전원 분배 유닛) — 서버랙 전선 분배 |
| Facilities | — | 데이터센터 시설물 (drilldown 필요) |
| Network_Switches | — | 네트워크 스위치 (drilldown 필요) |
| Racks | — | 서버 랙 골격 (drilldown 필요) |
| Server_Nodes | — | 서버 노드 (drilldown 필요) |

## 활용 예
- **Pipe / 전선이 필요할 때**: `DCP_A_01.usd` (파이프), `rPDU_A_01.usd` (전선 모음)
- 데이터센터 환경 전체: 위 6 폴더의 USD 들을 reference 로 조립

## drilldown 미완료 항목
`✓` 미부착 행은 sub-folders 만 확인했고 대표 USD 는 미특정. 후속 catalog turn 에서
`content_browse` 로 추가 walk 후 `✓` 로 확정.
