<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: branch/ 의 외부 .bat 직접 실행이 3초만에 fail / dependency solver 미해결 진단 / 복구 -->
# Kit dependency solver fail (`.bat` 3 초 즉시 종료)

`branch/` 의 외부 Kit app build (`isaac-sim.bat`, `kkr_usd_composer.kit.bat`,
`kkr_usd_composer_streaming.kit.bat` 등) 가 직접 실행 3 초만에 종료 + log 에
`Failed to resolve extension dependencies` 가 보일 때 진입.

## 증상

- `.bat` 더블클릭 또는 PowerShell `Start-Process` 실행 후 약 3 초 만에
  cmd 창이 닫힘 (kit.exe 가 GUI 보이기 전)
- stdout 로그 마지막 라인:
  ```
  [3.4xxs] [Error] [omni.kit.app.plugin] Exiting app because of dependency solver failure...
  ```
- stderr 에 미해결 dependency 나열:
  ```
  Failed to resolve extension dependencies. Failure hints:
    * No versions of <ext-id> that satisfies: <app-id> depends on <ext-id> version *
      - Available packages for <ext-id> version *:
        (none found)
  ```
- 미해결 후보가 `omni.mycompany.*` 같은 사내 / kkr-extensions 소속 패키지면
  ext folder 경로가 stale 한 경우가 거의 100% .

## 근본 원인

`.kit` 파일의 `[settings.app.exts.folders]` `'++'` 리스트에 박힌 **절대경로**
(예: `"C:/Users/<you>/workspace/<old-name>/kkr-extensions"`) 가 디렉토리
rename / repo move 후 stale → kit 이 그 경로를 스캔해도 빈 폴더만 발견 →
`omni.mycompany.*` 같은 의존 extension 미해결 → solver 종료.

대표 사례 (2026-05-04):
- commit `be4aced refactor: rename Isaac-sim-MCP -> omniverse-kit-mcp` 가
  작업 디렉토리만 rename 했으나 `.kit` 파일 안의 절대경로 미갱신
- 옛 경로 `C:/Users/<you>/workspace/Isaac-sim-MCP/kkr-extensions/` 가 (사고 시점) stale,
  실 extension 들은 `C:/Users/<you>/workspace/omniverse-kit-mcp/kkr-extensions/`
  에 위치 → solver 가 아무 것도 못 찾아 종료

> ⚠️ 정정 (2026-05-26): 위는 2026-05-04 사고 시점 기록. 현재 `C:/Users/<you>/workspace/Isaac-sim-MCP/`
> 는 rename 전 **전체 클론**(stale·미사용, 639M)이 통째로 남아 있어 "빈 폴더" 가 아님.
> 라이브는 `omniverse-kit-mcp/` 사용 — solver 진단 시 옛 경로가 비었다고 단정하지 말 것.

## 진단 단계

### 1. `.bat` stdout/stderr 캡처 후 미해결 dependency 식별

```powershell
$bat = "C:\Users\<you>\workspace\branch\<...>\<app>.kit.bat"
Start-Process $bat `
  -RedirectStandardOutput "$env:TEMP\kit_dep.log" `
  -RedirectStandardError  "$env:TEMP\kit_dep.err" `
  -PassThru -WindowStyle Hidden
# 약 5초 대기 후
Get-Content "$env:TEMP\kit_dep.err"
```

(주의: `Start-Process cmd.exe -ArgumentList "/c","..."` 형태 + inline redirect
는 quoting 이 깨져 로그가 아예 생성 안됨 — 위 패턴 사용)

### 2. 어떤 ext 가 미해결인지 메시지에서 추출

stderr 의 `* No versions of <ext-id> that satisfies: <app-id> depends on <ext-id>`
줄에서 `<ext-id>` 메모.

### 3. `.kit` 파일의 `[settings.app.exts.folders]` 경로 검증

```bash
grep -rn '"C:/Users/<you>/workspace/' --include='*.kit' C:/Users/<you>/workspace/branch/
# 매치된 각 경로에 대해
ls <hardcoded-path>
# 비어있거나 없으면 stale
```

### 4. 실제 ext 위치 확인

```bash
ls C:/Users/<you>/workspace/omniverse-kit-mcp/kkr-extensions/ | grep <ext-id-stem>
```

### 5. 최근 디렉토리 rename / move commit 여부 확인

```bash
cd C:/Users/<you>/workspace/omniverse-kit-mcp
git log --oneline -n 10 | grep -iE 'rename|move|relocat'
```

## 복구

`.kit` 파일의 stale 절대경로를 실제 ext 폴더 위치로 갱신:

```bash
# 모든 .kit 의 stale 경로 일괄 grep
grep -rln '"C:/Users/<you>/workspace/<old-name>' --include='*.kit' C:/Users/<you>/workspace/branch/
# 각 파일에서 옛 → 새 경로로 Edit
# 갱신 후 다시 .bat 실행하여 검증
```

`kit-app-template` 의 `source/apps/<app>.kit` 와
`_build/.../release/apps/<app>.kit` 는 hardlink (동일 inode) 라 source 만
수정해도 양쪽 갱신됨 — `stat <source> <build>` 의 Inode 비교로 확인 가능.

## 검증 (성공 신호)

- stderr 에 `Failed to resolve extension dependencies` 사라짐
- stdout 에 `[NN.NNNs] [ext: kkr_usd_composer-<ver>] startup` 또는
  `[ext: isaacsim.exp.full-<ver>] startup` 도달
- `[NN.NNNs] app ready` + `[NN.NNNs] RTX ready` (Composer) /
  `Isaac Sim Full App is loaded.` (Standalone) 까지 진행

## 재발 방지

- 디렉토리 rename / repo move 시 작업 시작 전 `docs/invariants/multi-app.md`
  의 `## .kit ext folder 절대경로` 섹션 Read
- rename 직후 `grep -rn '"C:/Users/<you>/workspace/' --include='*.kit' branch/`
  로 stale 경로 일괄 검출 후 갱신
- 사고 기록 (재현 증거): `kkr-extensions/docs/lessons-learned.md` (2026-05-04 entry)

## 관련 경계

- Multi-app invariant 본문: `docs/invariants/multi-app.md`
- 사고 기록 / 재현 증거: `kkr-extensions/docs/lessons-learned.md`
- Cold boot 진단 (다른 시그니처): `docs/runbooks/cold-boot-timeout.md`
- `.bat` quoting / process lifecycle: user `~/.claude/CLAUDE.md` "Shell" §
