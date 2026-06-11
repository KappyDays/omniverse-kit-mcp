# USD Composer Asset Catalog

NVIDIA Omniverse 의 standard sample library (`omniverse-content-production` S3
bucket) 중 USD Composer 의 default Content browser 에서 보이는 asset 들을 분류.

`docs/assets/isaac/assets/` 가 Isaac Sim 6.0 번들 한정 catalog 인 데 비해, 이 디렉토리는
**Composer 영역의 모든 asset** 을 다룬다. Isaac Sim 에서도 같은 HTTPS URL 로 load 가능.

S3 root: `https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/`

## 카테고리 표

| 카테고리 | catalog 파일 | 대표 사용처 |
|---|---|---|
| DigitalTwin | [`datacenter.md`](datacenter.md) | 데이터센터 — 액체냉각 pipe, PDU, 서버 랙, 네트워크 스위치 |

(이 표는 점진 확장 — ArchVis / Vegetation / Skies / Materials 등은 후속 turn 에 추가)

## 검증 / sync

`/omniverse-asset-inventory-sync` skill 이 이 디렉토리의 .md 도 함께 검증
(`docs/assets/isaac/assets/` 와 통합). URL 404 / NET / 5xx 자동 감지.
