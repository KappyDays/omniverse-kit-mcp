<!-- Parent: ../CLAUDE.md -->
<!-- Scope: 설치 스크립트 — repo clone, uv sync, .env, ~/.claude.json 등록 -->

# setup — 설치 스크립트

신규 PC에서 Isaac-sim-MCP 를 사용 가능 상태까지 준비하는 스크립트들. 실제 로직은 PowerShell(`setup_isaacsim_mcp.ps1`)이, 진입점은 배치 파일(`setup-isaacsim-mcp.bat`)이 담당.

## 파일

| 파일 | 역할 |
|------|------|
| `setup-isaacsim-mcp.bat` | Windows 진입점. 더블 클릭 또는 `setup\setup-isaacsim-mcp.bat` 로 실행. PowerShell 스크립트를 `ExecutionPolicy Bypass`로 호출 |
| `setup_isaacsim_mcp.ps1` | 실제 설치 로직 (4 단계) |

## 스크립트 동작

`setup_isaacsim_mcp.ps1` 가 수행하는 단계:

1. **Prerequisites 확인** — `git`, `uv` 가 PATH에 있는지 확인. 없으면 안내 후 종료
2. **Repo clone 또는 검증** — `$env:USERPROFILE\workspace\Isaac-sim-MCP` 에 repo 가 있으면 `uv sync`, 없으면 `git clone` 후 `uv sync`
3. **.env 생성** — `.env.example` → `.env` 복사 (이미 있으면 skip, 기존 값 보존)
4. **`~/.claude.json` 등록** — `mcpServers.isaacsim-mcp` entry 추가/갱신

## 🚨 MCP 서버 등록 위치 (주의)

- **등록 파일**: `~/.claude.json` (= `$env:USERPROFILE\.claude.json`)
- **NOT** `~/.claude/settings.json` — Claude Code 는 오직 `.claude.json` 한 파일에서 MCP 서버를 읽는다
- 기존 `~/.claude.json` 이 있으면 `mcpServers` 키에 `isaacsim-mcp` entry 를 병합 (덮어쓰기 아님)
- 동일 이름 entry 가 이미 있으면 덮어쓰기 후 Claude Code 재시작 안내

## Idempotent 설계

- 재실행 안전: `uv sync`, `.env` 스킵, `~/.claude.json` merge 모두 idempotent
- repo 경로가 이미 존재하면 재 clone 하지 않음 (`pyproject.toml` 존재 여부로 판별)

## 신규 PC 설치 절차

```bash
setup\setup-isaacsim-mcp.bat
```

실행 후:
1. Claude Code 완전 재시작 (MCP 서버 목록 갱신)
2. `isaacsim-mcp` tool prefix 로 도구들이 보이는지 확인
3. Isaac Sim 은 별도 설치 필요 (standalone 5.1.0, 경로: `C:\Users\<you>\workspace\branch\isaac-sim-standalone-5.1.0-windows-x86_64\`)
4. Kit extension 활성화는 `kit.exe --ext-folder ... --enable omni.mycompany.validation_api` 로 자동 (Extension Manager 수동 토글 불필요) — 자세한 플래그는 `../src/isaacsim_mcp/modules/CLAUDE.md` 참조

## 수정 시 주의

- `$env:USERPROFILE` 기준 경로만 사용 (개발자 절대경로 하드코드 금지)
- PowerShell `$ErrorActionPreference = 'Stop'` 유지 — 중간 실패 시 조용히 넘기지 않도록
- 콘솔 출력은 UTF-8 강제 (`[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`)

## 관련 경계

- kit.exe 실행 플래그 및 프로세스 제어: `../src/isaacsim_mcp/modules/CLAUDE.md` (ProcessModule)
- Extension 개발 규칙: `../isaac_extension/CLAUDE.md`
- 환경 변수 전체 목록: root `CLAUDE.md`
