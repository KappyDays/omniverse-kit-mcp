# Implementation Issues — 2회 재시도 실패 후 skip 한 항목 기록

**규칙**: 어떤 tool/step 이 2회 재시도 후에도 실패하면 여기에 기록 후 건너뛰기. 사용자 질의 금지.

**형식**
```
## [Phase X] {tool_name or step_name}
- **날짜**: YYYY-MM-DD HH:MM
- **시도 1**: {approach 설명} → {failure 이유, 에러 메시지}
- **시도 2**: {근본적으로 다른 approach} → {failure 이유}
- **skip 사유**: {final judgement — 왜 더 진행 불가한지}
- **영향 범위**: {어느 슬라이드/Phase/워크플로우에 영향}
- **대체 수단**: {있으면 명시, 없으면 "없음"}
```

---
