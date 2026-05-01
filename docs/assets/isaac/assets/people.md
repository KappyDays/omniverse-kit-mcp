# People — Isaac Sim 5.1 Asset Catalog

`$ISAAC` = `https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac`

루트: `$ISAAC/People/`  
드릴다운: `asset_list(category="people", subpath="{SubFolder}")`

---

## Characters (Named)

루트: `$ISAAC/People/Characters/`  
**파일 규칙**: `Biped_Setup.usd` 만 루트에 직접 존재. 나머지는 `{name}/{name}.usd` 폴더 패턴.

| 에셋 | USD 경로 | 설명 |
|---|---|---|
| Biped_Setup | `Characters/Biped_Setup.usd` ✓ | AnimationGraph 기본 rig |
| F_Business_02 | `Characters/F_Business_02/F_Business_02.usd` ✓ | 여성 비즈니스 복장 |
| F_Medical_01 | `Characters/F_Medical_01/F_Medical_01.usd` ✓ | 여성 의료 복장 |
| M_Medical_01 | `Characters/M_Medical_01/M_Medical_01.usd` ✓ | 남성 의료 복장 |
| biped_demo | `Characters/biped_demo/biped_demo_meters.usd` | 데모용 biped (파일명 suffix 주의) |
| female_adult_police_01_new | `Characters/female_adult_police_01_new/female_adult_police_01_new.usd` ✓ | 여성 경찰 |
| female_adult_police_02 | `Characters/female_adult_police_02/female_adult_police_02.usd` ✓ | 여성 경찰 |
| female_adult_police_03_new | `Characters/female_adult_police_03_new/female_adult_police_03_new.usd` ✓ | 여성 경찰 |
| male_adult_construction_01_new | `Characters/male_adult_construction_01_new/male_adult_construction_01_new.usd` ✓ | 남성 작업자 |
| male_adult_construction_03 | `Characters/male_adult_construction_03/male_adult_construction_03.usd` ✓ | 남성 작업자 |
| male_adult_construction_05_new | `Characters/male_adult_construction_05_new/male_adult_construction_05_new.usd` ✓ | 남성 작업자 |
| male_adult_police_04 | `Characters/male_adult_police_04/male_adult_police_04.usd` ✓ | 남성 경찰 |
| original_female_adult_business_02 | `Characters/original_female_adult_business_02/...` | 구버전 (legacy) |
| original_female_adult_medical_01 | `Characters/original_female_adult_medical_01/...` | 구버전 |
| original_female_adult_police_01/02/03 | `Characters/original_female_adult_police_*/...` | 구버전 경찰 (3종) |
| original_male_adult_construction_01/02/03/05 | `Characters/original_male_adult_construction_*/...` | 구버전 작업자 (4종) |
| original_male_adult_medical_01 | `Characters/original_male_adult_medical_01/...` | 구버전 |
| original_male_adult_police_04 | `Characters/original_male_adult_police_04/...` | 구버전 |

> **부재 확인 (2026-04-19)**: `female_child_casual_01`, `male_child_casual_01` — S3 에 존재하지 않음.

---

## DH_Characters (고품질 Digital Human)

루트: `$ISAAC/People/DH_Characters/`  
UUID 형식 폴더명 22개 + `Common`. 파일 규칙: `{uuid}/{uuid}.usd`  
탐색: `asset_list(category="people", subpath="DH_Characters")`  
시각 확인: Isaac Sim Content Browser → `Isaac Sim Assets (Beta) > People > DH_Characters`

---

## DH_Characters_Extended

동일 22 UUID 기반, 각 UUID당 `_1`~`_10` variant (의상/외형 다양화). 총 220+ 폴더.

---

## Animations

루트: `$ISAAC/People/Animations/`

| 파일 | 설명 |
|---|---|
| `LookAround.skelanim.usd` | 주위 둘러보기 |
| `Sit.skelanim.usd` | 앉기 |
| `push_button.skelanim.usd` | 버튼 누르기 |
| `stand_idle_loop.skelanim.usd` | 서서 대기 (루프) |
| `stand_idle_loop_mirror.skelanim.usd` | 서서 대기 미러 |
| `stand_idle_wave_loop.skelanim.usd` | 서서 손 흔들기 루프 |
| `stand_idle_wave_loop_mirror.skelanim.usd` | 미러 |
| `stand_walk_loop.skelanim.usd` | 걷기 루프 (제자리) |
| `stand_walk_loop_in_place.skelanim.usd` | 걷기 제자리 |
| `stand_walk_loop_in_place_mirror.skelanim.usd` | 미러 |
| `stand_walk_loop_mirror.skelanim.usd` | 걷기 루프 미러 |
| `stand_walk_1~5, 7.skelanim.usd` | 다양한 걷기 동작 (6종 + mirror 각 1종) |
| `type_keyboard.skelanim.usd` | 키보드 타이핑 |
