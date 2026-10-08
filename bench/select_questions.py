"""Applies the eligibility rules to docs/question-pool.json and picks 2 questions per group with a fixed seed.
The rules look only at the definitions, never at answers. Output: docs/questions.json and docs/selection.md."""
import json, random
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"
SEED = 20261007
RULES = {
    "E1": "Every named field and option exists in the portal. An option named by a wrong label is corrected to the existing option with the same meaning; if none exists, the question is out.",
    "E2": "No moving or unknown time reference (for example 'in the last 30 days' relative to an enrichment run).",
    "E3": "Sellestial fields only (no fields of a second brand that shares the portal).",
    "E4": "No answer that names a person or reveals named companies or domains from our prospect list, because the answers are published.",
    "E5": "Not a repeat of one of the five v1 pilot questions (job titles, average company size, top industries, contacts per month, companies without a domain): the test must be held out. Added on reviewer advice after the first draw and before any scored run; the first draw is kept in docs/selection-first-draw.md.",
}
OUT = {"g2-08": "E2", "g3-09": "E2", "g1-08": "E3", "g2-09": "E3", "g5-05": "E3", "g5-07": "E3",
       "g5-04": "E4", "g4-05": "E4", "g4-07": "E4", "g4-08": "E4",
       "g4-01": "E5", "g5-01": "E5", "g2-03": "E5", "g3-01": "E5", "g1-03": "E5"}
FIXES = {"g5-08": ("label 'United States'", "label 'United States of America (the)'")}

pool = json.loads((DOCS / "question-pool.json").read_text())
for q in pool:
    if q["id"] in FIXES:
        old, new = FIXES[q["id"]]
        assert old in q["definition"], q["id"]
        q["definition"] = q["definition"].replace(old, new)
eligible = [q for q in pool if q["id"] not in OUT]
rng = random.Random(SEED)
picked = []
for g in sorted({q["group"] for q in pool}, key=lambda g: min(q["id"] for q in pool if q["group"] == g)):
    ids = sorted(q["id"] for q in eligible if q["group"] == g)
    picked += rng.sample(ids, 2)
chosen = [q for q in pool if q["id"] in picked]
(DOCS / "questions.json").write_text(json.dumps(chosen, indent=1, ensure_ascii=False))
lines = ["# Question selection", "", f"Pool: {len(pool)} questions written by a separate AI agent that saw only the field list (docs/question-pool.json).", "",
         "## Eligibility rules (fixed before selection; they look only at definitions, never at answers)", ""]
lines += [f"- **{k}**: {v}" for k, v in RULES.items()]
lines += ["", "## Excluded", ""] + [f"- {i} ({r}): {next(q['question'] for q in pool if q['id'] == i)}" for i, r in sorted(OUT.items())]
lines += ["", "## Corrected", ""] + [f"- {i}: {a} -> {b}" for i, (a, b) in FIXES.items()]
lines += ["", f"## Selection: seed {SEED}, Python random.Random(seed).sample, 2 per group in id order", ""]
lines += [f"- {q['id']} ({q['group']}): {q['question']}" for q in chosen]
(DOCS / "selection.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines[-12:]))
