# People — Isaac Sim 6.0 Asset Catalog

`$ISAAC` = `https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.0/Isaac`

Root: `$ISAAC/People/`
Drill down to: `asset_list(category="people", subpath="{SubFolder}")`

---

## Characters (Named)

Root: `$ISAAC/People/Characters/`
**File Rule**: Named character is `{name}/{name}.usd` folder pattern.

| assets | USD path | explanation |
|---|---|---|
| F_Business_02 | `Characters/F_Business_02/F_Business_02.usd` ✓ | women business attire |
| F_Medical_01 | `Characters/F_Medical_01/F_Medical_01.usd` ✓ | women medical attire |
| M_Medical_01 | `Characters/M_Medical_01/M_Medical_01.usd` ✓ | male medical attire |
| female_adult_police_01_new | `Characters/female_adult_police_01_new/female_adult_police_01_new.usd` ✓ | female police |
| female_adult_police_02 | `Characters/female_adult_police_02/female_adult_police_02.usd` ✓ | female police |
| female_adult_police_03_new | `Characters/female_adult_police_03_new/female_adult_police_03_new.usd` ✓ | female police |
| male_adult_construction_01_new | `Characters/male_adult_construction_01_new/male_adult_construction_01_new.usd` ✓ | male worker |
| male_adult_construction_03 | `Characters/male_adult_construction_03/male_adult_construction_03.usd` ✓ | male worker |
| male_adult_construction_05_new | `Characters/male_adult_construction_05_new/male_adult_construction_05_new.usd` ✓ | male worker |
| male_adult_police_04 | `Characters/male_adult_police_04/male_adult_police_04.usd` ✓ | male police |
| original_female_adult_business_02 | `Characters/original_female_adult_business_02/...` | Old version (legacy) |
| original_female_adult_medical_01 | `Characters/original_female_adult_medical_01/...` | Old version |
| original_female_adult_police_01/02/03 | `Characters/original_female_adult_police_*/...` | Old version police (3 types) |
| original_male_adult_construction_01/02/03/05 | `Characters/original_male_adult_construction_*/...` | Old version worker (4 types) |
| original_male_adult_medical_01 | `Characters/original_male_adult_medical_01/...` | Old version |
| original_male_adult_police_04 | `Characters/original_male_adult_police_04/...` | Old version |

> **Check for absence (2026-04-19)**: `female_child_casual_01`, `male_child_casual_01` — Not present in S3.

---

## DH_Characters (High Quality Digital Human)

Root: `$ISAAC/People/DH_Characters/`
22 UUID format folder names + `Common`. File rule: `{uuid}/{uuid}.usd`
Navigation: `asset_list(category="people", subpath="DH_Characters")`
Check the time: Isaac Sim Content Browser → `Isaac Sim Assets (Beta) > People > DH_Characters`

---

## DH_Characters_Extended

Based on the same 22 UUIDs, `_1`~`_10` variant (costume/appearance diversification) for each UUID. Total 220+ folders.

---

## Animations

Root: `$ISAAC/People/Animations/`

| file | explanation |
|---|---|
| `LookAround.skelanim.usd` | look around |
| `Sit.skelanim.usd` | sit |
| `push_button.skelanim.usd` | press button |
| `stand_idle_loop.skelanim.usd` | Stand and wait (loop) |
| `stand_idle_loop_mirror.skelanim.usd` | standing and waiting mirror |
| `stand_idle_wave_loop.skelanim.usd` | standing and waving loop |
| `stand_idle_wave_loop_mirror.skelanim.usd` | mirror |
| `stand_walk_loop.skelanim.usd` | walking loop (in place) |
| `stand_walk_loop_in_place.skelanim.usd` | walking in place |
| `stand_walk_loop_in_place_mirror.skelanim.usd` | mirror |
| `stand_walk_loop_mirror.skelanim.usd` | walking loop mirror |
| `stand_walk_1~5, 7.skelanim.usd` | Various walking movements (6 types + 1 type of mirror each) |
| `type_keyboard.skelanim.usd` | keyboard typing |
