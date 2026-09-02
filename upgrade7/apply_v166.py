#!/usr/bin/env python3
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

DIST = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
PATCH_FILE = Path(sys.argv[2] if len(sys.argv) > 2 else "upgrade7/v1.66_patch.json")
BASE_APPLY = Path(sys.argv[3] if len(sys.argv) > 3 else "/tmp/apply_712.py")

CORE_IMMUTABLE = ("id","question","choiceA","choiceB","choiceC","choiceD","answer")

def die(msg):
    raise SystemExit("ERROR: " + msg)

def canonical_digest(questions):
    raw = json.dumps(
        questions, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def load_base_module():
    spec = importlib.util.spec_from_file_location("apply712", BASE_APPLY)
    if spec is None or spec.loader is None:
        die("cannot load base apply module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def main():
    patch = json.loads(PATCH_FILE.read_text(encoding="utf-8"))
    if patch.get("schema") != "common-subject-712-v166-delta-v1":
        die("unexpected patch schema")

    mod = load_base_module()
    parts = sorted(DIST.glob("data.part*"))
    if not parts:
        die("dist/data.partXX files not found")

    raw = b"".join(p.read_bytes() for p in parts)
    root, kind = mod.decode_data(raw)
    questions = mod.locate_questions(root)

    if len(questions) != patch["questionCount"]:
        die(f"expected {patch['questionCount']} questions, got {len(questions)}")

    expected_ids = [f"LEARN-COM-{i:03d}" for i in range(1, 713)]
    actual_ids = [q.get("id") for q in questions]
    if actual_ids != expected_ids:
        die("ID sequence mismatch before v1.66 patch")

    before_digest = canonical_digest(questions)
    if before_digest != patch["baseCanonicalSha256"]:
        die(
            "base canonical digest mismatch: "
            f"got={before_digest} expected={patch['baseCanonicalSha256']}"
        )

    by_id = {q["id"]: q for q in questions}
    before_core = {
        q["id"]: {k: q.get(k) for k in CORE_IMMUTABLE}
        for q in questions
    }

    changed_fields = []
    for change in patch["changes"]:
        qid = change["id"]
        field = change["field"]
        if qid not in by_id:
            die("patch target missing: " + qid)
        q = by_id[qid]
        if q.get(field) != change["before"]:
            die(f"unexpected pre-patch value: {qid}.{field}")
        q[field] = change["after"]
        changed_fields.append((qid, field))

    if len(changed_fields) != 20 or len(set(changed_fields)) != 20:
        die("v1.66 patch must contain exactly 20 unique field changes")

    option_count = sum(field == "optionExplanations" for _, field in changed_fields)
    explanation_count = sum(field == "explanation" for _, field in changed_fields)
    if option_count != 19 or explanation_count != 1:
        die(
            "unexpected change scope: "
            f"optionExplanations={option_count}, explanation={explanation_count}"
        )

    for q in questions:
        for field in CORE_IMMUTABLE:
            if q.get(field) != before_core[q["id"]][field]:
                die(f"immutable core field changed: {q['id']}.{field}")

    after_digest = canonical_digest(questions)
    if after_digest != patch["targetCanonicalSha256"]:
        die(
            "target canonical digest mismatch: "
            f"got={after_digest} expected={patch['targetCanonicalSha256']}"
        )

    encoded = mod.encode_data(root, kind)
    n = len(parts)
    cuts = [round(len(encoded) * i / n) for i in range(n + 1)]
    for i, p in enumerate(parts):
        p.write_bytes(encoded[cuts[i]:cuts[i + 1]])

    persisted = b"".join(p.read_bytes() for p in parts)
    root2, _ = mod.decode_data(persisted)
    questions2 = mod.locate_questions(root2)
    persisted_digest = canonical_digest(questions2)
    if persisted_digest != patch["targetCanonicalSha256"]:
        die("persisted dataset digest mismatch after re-encode")

    (DIST / "DATASET_712_V166_AUDIT.json").write_text(
        json.dumps(questions2, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (DIST / "DATASET_VERSION.txt").write_text(
        "\n".join([
            patch["targetVersion"],
            "712 questions",
            f"base_canonical_sha256={patch['baseCanonicalSha256']}",
            f"canonical_sha256={patch['targetCanonicalSha256']}",
            "changes=20",
            "answer_changes=0",
            "question_changes=0",
            "choice_changes=0",
            "",
        ]),
        encoding="utf-8",
    )

    for name in ("app.js", "index.html", "manifest.webmanifest"):
        p = DIST / name
        if p.exists():
            s = p.read_text(encoding="utf-8")
            s = s.replace("v1.65", "v1.66")
            p.write_text(s, encoding="utf-8")

    print(
        "OK: applied v1.66 patch; "
        f"changes=20; answer_changes=0; sha256={after_digest}"
    )

if __name__ == "__main__":
    main()
