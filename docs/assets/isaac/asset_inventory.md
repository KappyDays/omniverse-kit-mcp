# Isaac Sim 6.0 — Asset Catalog Index

**실측 완료**: 2026-06-10 Isaac Sim 6.0 S3 HEAD 검증 (`scripts/diff_asset_inventory.py --verbose`: 112 URLs, 0 invalid).
**사용법**: 필요한 카테고리 파일만 Read — 불필요한 토큰 소비 없음.

---

## 버킷 루트 URLs

| 카탈로그 | Bucket | Prefix |
|---|---|---|
| **Isaac Sim Assets** | `omniverse-content-production.s3-us-west-2.amazonaws.com` | `Assets/Isaac/6.0/Isaac/` |
| **SimReady Explorer** | `omniverse-content-staging.s3.us-west-2.amazonaws.com` | `Assets/simready_content/common_assets/props/` |

- `$ISAAC` = `https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.0/Isaac`
- `$SIM`   = `https://omniverse-content-staging.s3.us-west-2.amazonaws.com/Assets/simready_content/common_assets/props`

두 버킷 모두 public read. `stage_load_usd` 호출 시 **full HTTPS URL** 사용 (`file://` 금지).

---

## 카테고리별 파일 포인터

| 요청 종류 | 읽을 파일 | 내용 요약 |
|---|---|---|
| 로봇 추가 / 로봇 추천 | `docs/assets/robots.md` | 44 벤더 · 100+ 모델 · 유형별 인덱스 · USD 파일명 전수 실측 |
| 환경 / 씬 로드 | `docs/assets/environments.md` | 10개 환경 폴더 · 주요 USD 크기 |
| 사람 / 캐릭터 / 애니메이션 | `docs/assets/people.md` | Named Characters · DH_Characters · Animations |
| 산업용 prop (팔레트·지게차·선반) | `docs/assets/props.md` | Isaac Core Props 23 폴더 |
| 가구 / 박스 / 컨테이너 | `docs/assets/simready.md` | SimReady Props 1000+ 종 분류 목록 |
| RL 학습 / 재질 / 예제 / 센서 | `docs/assets/other.md` | IsaacLab · Materials · Samples · Sensors |

---

## 검색 가이드

```python
# 카테고리 목록
asset_list()

# 특정 카테고리 탐색
asset_list(category="robots", subpath="Unitree")
asset_list(category="environments", subpath="Simple_Warehouse")

# SimReady 탐색 (1000+ 종, 알파벳 순 pagination)
content_browse("$SIM", max_entries=500)
content_browse("$SIM/{name}")  # → {name}.usd 가 canonical
```
