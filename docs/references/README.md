# docs/references/ — Public-Safe References

## 파일

| 파일/폴더 | 무엇 | 편집 가능? |
|-----------|------|-----------|
| `sensor_menu_catalog.md` | `Create > Sensors` 메뉴 카탈로그. MCP resource source | ✅ 필요 시 갱신 |
| `CLAUDE.md` | 이 디렉토리 작업 지침 | ✅ 작업 수정 시 동기화 |

## Local-Only Generated References

아래 파일들은 public repo 에서 추적하지 않는다. 로컬 Kit / Isaac Sim / USD
Composer 설치 메타데이터 또는 외부 문서 스냅샷을 반영하는 생성 산출물이기
때문이다.

- `extensions.json`
- `extensions-catalog.md`
- `harvest-progress.json`
- `app-specific/`
- `testbed-snapshot/`

## 재생성 명령

- `.venv/Scripts/python.exe scripts/harvest_extension_metadata.py`
- `.venv/Scripts/python.exe scripts/render_catalog_md.py`
- `.venv/Scripts/python.exe -m pytest tests/unit/test_catalog_integrity.py -q`

생성된 파일은 `.gitignore` 대상이다. 공유해야 할 durable rule 은 catalog 원문
대신 `docs/invariants/` 또는 `docs/runbooks/` 로 요약해서 반영한다.
