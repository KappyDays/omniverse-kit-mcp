<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: kit.exe cold boot hang 발생 시 진단 / 재현 / 복구 -->
<!-- ============================================================ -->
<!-- ⛔ DO-NOT-EDIT — L17 4시간 디버깅 결과 보호 (2026-04-24)        -->
<!--                                                                 -->
<!-- 이 파일은 재구성 작업 (CLAUDE.md Pull-First) 시 루트            -->
<!-- CLAUDE.md §"kit.exe cold boot hang — stdin pipe deadlock"       -->
<!-- 의 본문이 이관된 곳. 보호 의도 (4h+ 디버깅 결과의 정확한        -->
<!-- 보존) 는 그대로 따라옴. 축약 허용 / 단 아래 5 항목은 어떤       -->
<!-- 축약에서도 사라지면 안 됨:                                       -->
<!--   1. "stdin=subprocess.DEVNULL" 문자열                           -->
<!--   2. "process_module.py::start" 위치 표기                        -->
<!--   3. 검증 수치 240 / 13                                          -->
<!--   4. "extra_ext_ids race" 진단 무효 cross-ref                    -->
<!--   5. lessons-learned L17 참조                                    -->
<!--                                                                  -->
<!-- 자동 검증: tests/unit/test_do_not_edit_guards.py G1-G7          -->
<!-- ============================================================ -->

# kit.exe cold boot hang — stdin pipe deadlock

> 4시간 디버깅 (2026-04-23 hang × 2 → 2026-04-24 root cause 확정).
> 재발 발생 시 이 파일 첫 진입.

## 증상

- MCP tool `kit_app_start` / `kit_app_restart` 호출 → startup_timeout 까지 health
  무응답 → `status=timeout` (또는 240s 후 `status=still_loading`)
- `Get-Process kit` = alive (PID 정상), CPU 거의 0 (<5s after 5분), WS ~60MB (boot
  시작도 못함)
- internal kit log
  (`%LocalAppData%/../.nvidia-omniverse/logs/Kit/Isaac-Sim Full/5.1/kit_*.log`)
  가 ~85-91ms 시점 ext registration 직후 mtime 정체 — `[ext: omni.kit.loop-isaac]
  registered` 같은 line 이 마지막
- isaac-sim.bat 으로 동일 args 직접 실행 / `scripts/run_process_module_standalone.py
  start` (bash 에서) 는 15초 만에 정상 ready — 같은 코드 같은 .env 인데 결과 다름

## 근본 원인

`subprocess.Popen` 의 **stdin inheritance**:

- MCP server (`omniverse-kit-mcp`) 는 Claude Code 가 stdio 로 spawn → MCP server 의
  stdin = Claude Code 와의 양방향 MCP protocol pipe
- ProcessModule 의 `subprocess.Popen(...)` 가 `stdin` 인자 명시 안 했었음 →
  자식 kit.exe 가 그 MCP pipe stdin 을 그대로 상속
- kit.exe cold boot 중 어느 init component (carb plugin / GLFW / 일부 Python ext) 가
  stdin 을 read 시도 → MCP pipe 에서 block (Claude Code 는 stdin 채워주지 않음)
- 그 thread block → 다른 init thread 도 join 대기 → 전체 boot 정지
- 정확한 thread 가 어느 component 인지는 미특정 (~85ms 시점 = ext registration 끝 /
  ext startup 진입 직전)
- bash 에서 standalone 실행 시 stdin = TTY → `isatty()` 체크 통과 또는 EOF 즉시
  반환 → 정상 진행

## Fix 적용 위치

`src/omniverse_kit_mcp/modules/process_module.py::start` 의 `subprocess.Popen(...)` 에
**`stdin=subprocess.DEVNULL` 추가**. 단 한 줄. 절대 누락 / 변경 금지.

```python
self._process = subprocess.Popen(
    cmd,
    stdin=subprocess.DEVNULL,  # CRITICAL — 절대 누락 금지
    stdout=self._stdout_handle,
    stderr=subprocess.STDOUT,
    env=env,
    ...
)
```

## 검증 (2026-04-24 실측)

- Fix 전: stdin=PIPE 환경 시뮬레이션 (`subprocess.Popen([standalone_script],
  stdin=subprocess.PIPE)`) → **240s** timeout (재현 100%)
- Fix 후: 같은 시뮬레이션 → **13.0s** ready ✅

재현 검증 (Fix 회귀 방지):
```bash
python -c "import subprocess; p=subprocess.Popen(['.venv/Scripts/python.exe','scripts/run_process_module_standalone.py','start'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True); print(p.communicate(input='', timeout=300))"
```
→ ~13s ready 여야 PASS, 240s timeout 면 stdin DEVNULL 누락

## ⚠️ 잘못된 진단 회피

2026-04-23 의 mistake (이 회피 표기는 절대 제거 금지):
- "extra_ext_ids 7-8개 race" 진단은 잘못됨 — stdin pipe 가 실원인
- "GPU 셰이더 캐시 cold" / "user.config corruption" 등도 모두 상관관계만 있고
  인과관계 없음
- ext 갯수 / dependency 변경은 stdin race 의 timing 만 바꿈 — 진짜 원인 가린다

다음 hang 발생 시:
1. **반드시 stdin 명시 여부 첫 번째로 확인** (코드 변경 후 stdin=DEVNULL 누락 의심)
2. ext_ids 갯수 줄이기 / dependency 변경은 마지막 수단

## 관련 추가 fix 필요 시

다른 `subprocess.Popen` 호출 위치 (`scripts/`, `clients/` 등) 도 child 가 input
안 받을 거면 동일하게 `stdin=subprocess.DEVNULL` 명시. inheritance 가 default 라
silent leak.

## 관련 경계

- L17 사고 기록 원문: `kkr-extensions/docs/lessons-learned.md`
- 코드 위치 SoT: `src/omniverse_kit_mcp/modules/process_module.py::start`
- ProcessModule 결정 트리 / hang recovery 4종 함정: `src/omniverse_kit_mcp/modules/process-ops.md`
- Process 생애주기 invariants: `docs/invariants/process-lifecycle.md`
- Cold boot timeout 응답 분기 (still_loading vs crashed): `docs/runbooks/cold-boot-timeout.md`
