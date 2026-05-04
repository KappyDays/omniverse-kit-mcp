<!-- Parent: ../CLAUDE.md -->
<!-- Scope: 설치 스크립트 — repo clone / uv sync / .env / ~/.claude.json legacy cleanup -->

# setup — 설치 스크립트

신규 PC에서 omniverse-kit-mcp 를 사용 가능 상태까지 준비하는 스크립트들. 실제 로직은 PowerShell(`setup_omniverse_kit_mcp.ps1`)이, 진입점은 배치 파일(`setup-omniverse-kit-mcp.bat`)이 담당.

## 파일

| 파일 | 역할 |
|------|------|
| `setup-omniverse-kit-mcp.bat` | Windows 진입점. 더블 클릭 또는 `setup\setup-omniverse-kit-mcp.bat` 로 실행. PowerShell 스크립트를 `ExecutionPolicy Bypass`로 호출 |
| `setup_omniverse_kit_mcp.ps1` | 실제 설치 로직 (4 단계) |

## 스크립트 동작

`setup_omniverse_kit_mcp.ps1` 가 수행하는 단계:

1. **Prerequisites 확인** — `git`, `uv` 가 PATH에 있는지 확인. 없으면 안내 후 종료
2. **Repo clone 또는 검증** — `$env:USERPROFILE\workspace\omniverse-kit-mcp` 에 repo 가 있으면 `uv sync`, 없으면 `git clone` 후 `uv sync`
3. **.env 생성** — `.env.example` → `.env` 복사 (이미 있으면 skip, 기존 값 보존)
4. **`~/.claude.json` legacy cleanup** — 과거 setup 이 등록했던 7 entry (`isaacsim-mcp-{1,2,3}`, `usdcomposer-mcp-{1,2,3}`, `omniverse-kit-mcp`) 를 global `mcpServers` 에서 제거. 신규 등록은 하지 않음 — MCP 서버는 in-repo `workspaces/<profile>/instance-<N>/.mcp.json` 4 개에서 로드

## 🚨 MCP 서버 로드 위치

- **현재 SoT**: in-repo `workspaces/<profile>/instance-<N>/.mcp.json` 4 개 (committed, `uv --directory ../../..` 상대경로 — repo clone 위치 무관)
- **NOT** `~/.claude.json` 의 global `mcpServers` — 옛 등록 방식. 본 setup 의 Step 4 가 cleanup
- CC 진입은 `cd workspaces/<profile>/instance-<N>` 후 `claude` — 그 폴더에서만 해당 instance 의 MCP 1 개 로드 (tool prefix `mcp__isaacsim-mcp-1__*` 등, ~150 tool)

## Idempotent 설계

- 재실행 안전: `uv sync`, `.env` 스킵, legacy cleanup 모두 idempotent (cleanup 은 entry 부재 시 no-op)
- repo 경로가 이미 존재하면 재 clone 하지 않음 (`pyproject.toml` 존재 여부로 판별)

## 신규 PC 설치 절차

```bash
setup\setup-omniverse-kit-mcp.bat
```

실행 후:
1. Isaac Sim 5.1 standalone 별도 설치 — `.env` 의 `ISAAC_SIM_KIT_EXE` / `ISAAC_SIM_KIT_FILE` 로 경로 override (`../README.md` Isaac Sim Setup 섹션 참조)
2. `cd workspaces/isaac/instance-1` (또는 다른 instance 폴더) 후 `claude` 시작 → 시스템 리마인더에 해당 instance 의 `mcp__isaacsim-mcp-N__*` / `mcp__usdcomposer-mcp-N__*` tool prefix 표시 확인
3. Kit extension 활성화는 `kit.exe --ext-folder ... --enable omni.mycompany.validation_api` 로 자동 (Extension Manager 수동 토글 불필요) — 자세한 플래그는 `../src/omniverse_kit_mcp/modules/CLAUDE.md` 참조

## 수정 시 주의

- `$env:USERPROFILE` 기준 경로만 사용 (개발자 절대경로 하드코드 금지)
- PowerShell `$ErrorActionPreference = 'Stop'` 유지 — 중간 실패 시 조용히 넘기지 않도록
- 콘솔 출력은 UTF-8 강제 (`[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`)
- in-repo 4 개 `.mcp.json` 의 구조 / `../../..` 상대경로 / 환경 고유 substring 부재 / template-leftover 부재는 `tests/unit/test_workspace_mcp_configs.py` 가 가드

## 관련 경계

- kit.exe 실행 플래그 및 프로세스 제어: `../src/omniverse_kit_mcp/modules/CLAUDE.md` (ProcessModule)
- Extension 개발 규칙: `../kkr-extensions/CLAUDE.md`
- 환경 변수 전체 목록: root `CLAUDE.md`
- 워크스페이스 디렉토리 규약: `../workspaces/README.md`
