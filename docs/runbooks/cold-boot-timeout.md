<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: isaac_sim_start timeout 응답 (still_loading / crashed) 분기 해석 -->
# Cold boot timeout 응답 해석

`isaac_sim_start` 가 `startup_timeout` 만료 후 timeout 응답을 줄 때, 다음 액션을
결정하는 분기 가이드.

## 응답 분기

| `process_alive` | `status` | 의미 | 다음 action |
|---|---|---|---|
| `true` | `still_loading` | cold boot 진행 중. spawn 안 함 | **재호출** (Branch 2 폴링 이어감) — 강제 죽이지 말 것 |
| `false` | `crashed` | spawn 후 즉시 죽음 또는 boot 실패 | **즉시 진단** — log_tail 분석 |

## still_loading 처리

cold boot 가 GPU 셰이더 캐시 재빌드 등으로 5-10 분 걸릴 수 있음. timeout 후 status
가 still_loading 이면:
1. `log_tail` 마지막 line 확인 — ext registration 진행 중이면 정상
2. `isaac_sim_start` 재호출 — Branch 2 (alive but health 무응답) 로 진입하여 spawn
   없이 폴링만 이어감
3. 여러 번 재호출해도 계속 still_loading 이면 hang 의심:
   - **stdin pipe deadlock 의심** → `docs/runbooks/kit-stdin-deadlock.md`
   - hub orphan 의심 → `docs/runbooks/hub-orphan.md`
   - 수 분째 mtime 정체 → `cmd //c "taskkill /F /IM kit.exe /T"` + 재기동

## crashed 처리 — log_tail 분석 패턴

`startup_log` / `log_tail` 의 마지막 entries 시그니처별 진단:

### ext 누락
```
[Error] [omni.ext.plugin] Extension 'X' could not be found
```
→ `.env` 의 `ISAAC_SIM_EXTRA_EXT_IDS` 가 silent 무시된 경우 가능 (L14) →
`docs/runbooks/env-sub-config.md`

### MDL deadlock (S3 asset 로드 시)
```
[Warning] [omni.usd.resolver] Disabling base URL to resolve MDL identifier 'OmniPBR.mdl'
... (반복) ...
(silent)
```
→ `LogCaptureService` 활성 + S3 MDL-heavy asset 로드 → carb log callback GIL 경합 →
Kit main loop deadlock. 회피: USD 로드 4 조건 → `docs/invariants/usd-load.md`

### GPU driver 문제
```
[Error] [carb.graphics-vulkan.plugin] Failed to create Vulkan instance
```
→ GPU driver 재설치 / Vulkan SDK 확인

### Hub failure
```
Hub failed to launch: child exited with exit code: 1
```
→ `docs/runbooks/hub-orphan.md`

## startup_timeout 기본값 변경 시

`.env` 의 `ISAAC_SIM_STARTUP_TIMEOUT=600` (예: cold boot 까지 기다리고 싶을 때) —
주의: silent fail 시 진단이 늦어짐. 기본 120 이 빠른 진단 위해 권장.

설정 적용 안 되는 경우 env sub-config 함정 확인 → `docs/runbooks/env-sub-config.md`

## 관련 경계

- ProcessModule 결정 트리 + stdin/stdout 규약: `src/omniverse_kit_mcp/modules/process-ops.md`
- Process 생애주기 invariants: `docs/invariants/process-lifecycle.md`
- stdin pipe hang 본문: `docs/runbooks/kit-stdin-deadlock.md`
- env 무시 함정: `docs/runbooks/env-sub-config.md`
- Hub orphan: `docs/runbooks/hub-orphan.md`
