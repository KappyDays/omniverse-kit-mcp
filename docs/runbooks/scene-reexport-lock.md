<!-- Parent: ../CLAUDE.md -->
<!-- Scope: 씬 USD 를 코드로 재빌드→재오픈 반복 시 파일 잠금 / 레지스트리 / pycache 함정 -->
# Scene Re-export Lock — Runbook

## 증상

- worker/scene `.py` 빌더를 수정해 같은 경로로 re-export 했는데 **디스크 파일이 안 바뀜**
  (이후 `stage_open` 이 옛 콘텐츠 재로드). farm 세션: worker 수정 6회가 silent 무시.
- `CreateNew` 가 옛 부분 콘텐츠를 재사용 → 잔존 xformOp 로 `AddXformOp` 충돌.
- traceback 이 주석 라인을 가리키는 등 오진 → stale `__pycache__` 의 옛 바이트코드 실행.

## 근본 원인

1. **파일 잠금**: 라이브 Kit 이 `stage_open` 으로 USD 를 열면 OS 가 파일을 잠가, 같은 경로
   re-export 가 silent 실패.
2. **Sdf 레이어 레지스트리 캐시**: 실패한 build run 이 해당 레이어를 메모리에 stale 로 남겨,
   `Usd.Stage.CreateNew(path)` 가 그 캐시를 재사용.
3. **stale `__pycache__`**: importlib 로 빌더를 로드하면 옛 `.pyc` 바이트코드가 실행됨.

## 표준 해결 루프

1. 라이브 Kit 스테이지를 비워 락 해제: `stage_new` (Kit crash 아니면 restart 불필요).
   - validation_api 자신이 아닌 사용자 extension 코드만 바뀌었으면 `extension_reload(ext_id)` 로
     충분 (kit 재시작 불필요). 상세: `../invariants/ext-reload.md`.
2. 빌더는 **레지스트리/락 우회 기법**으로 export:
   ```python
   import sys
   sys.dont_write_bytecode = True          # stale .pyc 방지
   from pxr import Sdf
   layer = Sdf.Layer.CreateAnonymous()     # 레지스트리/디스크 락 우회
   # ... layer 에 stage 저작 ...
   layer.Export(out_path)                  # 원자적 디스크 쓰기
   ```
3. 재오픈해 검증: `stage_open(out_path)`.

## 헬퍼

`scripts/rebuild_scene.py <builder.py> --out <out.usd> [--reopen]` 가 위 루프를 한 커맨드로
수행한다. 빌더는 `build(layer)` (anonymous layer 에 저작) 또는 `build_to(out_path)` 중 하나를
노출하면 된다. 래퍼가 `sys.dont_write_bytecode=True` 를 설정하고 anonymous-layer 경로를 우선한다.

## 관련 경계

- USD 로드 4 조건 + 복붙 레시피: `../invariants/usd-load.md`, `../../kkr-extensions/docs/usd-load-deadlock-recipe.md`
- Extension reload (kit 재시작 회피): `../invariants/ext-reload.md`
- 메모리: `project_scene-reexport-file-lock`
