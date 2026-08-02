# Reprocessing the unverified translation cohort

Audience: an agent or the repo owner executing the reprocessing decision.

**Decision required first**: reprocess (~12-15 h wall, ~$10-20 flash quota) or
accept the cohort. This runbook covers reprocessing only.

## Why

The 2026-07-31 22:09 → 2026-08-01 06:08 batch ran **without** the source-echo
alignment check (dropped during a history rewrite). Its 1,693 books may
contain rare shifted translations (card N carrying card N-1's translation).
Compression and empties were already guarded; shifts are not. The affected
list lives in `unverified-books.txt`.

## Steps

1. Compute the still-unverified subset — books whose staging output was
   **not** rewritten since the check was restored (mtime before
   2026-08-01 06:09, or missing). Rewritten books are verified; exclude them:

```bash
cd /home/ashby/Documents/code/books_to_anki
.venv/bin/python - <<'EOF'
from pathlib import Path
from datetime import datetime
staging = Path("data/translations-site")
cutoff = datetime(2026, 8, 1, 6, 9, 0)
still = []
for line in open("unverified-books.txt", encoding="utf-8"):
    rel = line.strip()
    if not rel or rel.startswith("#"):
        continue
    p = staging / rel
    if not p.exists() or datetime.fromtimestamp(p.stat().st_mtime) < cutoff:
        still.append(rel)
Path("reprocess-now.txt").write_text("\n".join(still) + "\n", encoding="utf-8")
print(f"{len(still)} books still unverified -> reprocess-now.txt")
EOF
```

2. Delete those staging files (their checkpoints; the driver re-translates
   them fresh — never delete anything under the site repo):

```bash
# each line must be prefixed with the staging dir — a bare relative path
# would not exist from the repo root, and rm would error on the directory
# itself, silently leaving every checkpoint in place
xargs -a reprocess-now.txt -d '\n' -I{} rm -v "data/translations-site/{}"
```

3. Run the orchestrator detached. It re-runs the driver (resume — only the
   deleted books re-translate), then copies staging → site and re-flags the
   index. It stops the mop-up loop when the failed set stabilizes and reports
   stuck books:

```bash
setsid nohup .venv/bin/python finish_translations.py >> finish-translations.log 2>&1 < /dev/null &
```

4. Wait for the `done:` line in `finish-translations.log`.

## Constraints

- Never modify files under the site repo (`public/api/...`) directly — only
  the orchestrator's copy step writes there.
- Never re-translate books outside the list: the resume logic skips any book
  with complete staging output, so step 2's deletion is what scopes the run.
- Never delete the site's files.
- Do not run the driver concurrently with anything else using the staging dir.

## Acceptance

- `finish-translations.log` ends with `done: ... 0 books stuck`.
- Every entry in `reprocess-now.txt` has staging mtime ≥ 2026-08-01 06:09
  after the run.
- `index.jsonl` shows `translated:true` for all 2,148 entries.
