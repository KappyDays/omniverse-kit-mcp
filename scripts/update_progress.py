import json
import datetime as dt
from pathlib import Path

pp = Path("docs/references/harvest-progress.json")
prog = json.loads(pp.read_text(encoding="utf-8"))
prog["updated_at"] = dt.datetime.now(dt.UTC).isoformat()
prog["phases"]["enrichment"]["processed"] = 50
prog["phases"]["enrichment"]["last_processed"] = "isaacsim.replicator.behavior"
prog["phases"]["enrichment"]["remaining"] = 617 - 50
prog["phases"]["enrichment"]["status"] = "running"
# per_source_counts (batch 1: 43 exts, 7 extscache, 0 extsDeprecated)
prog["phases"]["enrichment"]["per_source_counts"]["exts"]["processed"] = 43
prog["phases"]["enrichment"]["per_source_counts"]["extscache"]["processed"] = 7
prog["phases"]["enrichment"]["per_source_counts"]["extsDeprecated"]["processed"] = 0
pp.write_text(json.dumps(prog, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
print("harvest-progress.json updated")
