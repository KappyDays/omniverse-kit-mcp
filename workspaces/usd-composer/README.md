# USD Composer Workspace

USD Composer 로 USD scene authoring / DCC 워크플로 작업.

## 사용

```
cd instance-1   # 또는 instance-2
claude
```

## 동시 가동

| CC 창 | 폴더 | Kit REST 포트 |
|---|---|---|
| 1 | `instance-1/` | 8114 |
| 2 | `instance-2/` | 8015 |

## Capability 제약

USD Composer 는 robotics ext (robot_*, sensor_attach_rtx_*, character_*, replicator_*) 미지원. 상세: `CLAUDE.md`.

## 작업 룰

`CLAUDE.md` 의 pull-doc 표 + scenario commit 룰 참조.
