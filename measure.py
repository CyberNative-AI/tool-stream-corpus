from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from streamcheck import probe


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+"\n", encoding="utf-8")


def main():
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    fixtures = json.loads(Path(__file__).with_name("fixture.json").read_text())
    counts = {a: {"correct": 0, "unsafe": 0, "missed": 0, "errors": 0} for a in ["eager", "json-ready", "terminal", "whole-buffer-terminal"]}
    records = 0
    units = 0
    raw = []
    for fixture in fixtures:
        blob = fixture["stream"].encode("utf-8")
        partitions = [("whole", [blob]), ("bytewise", [bytes([b]) for b in blob])]
        partitions += [(f"cut-{cut}", [blob[:cut], blob[cut:]]) for cut in range(1, len(blob))]
        for partition, chunks in partitions:
            units += 1
            for arm in counts:
                result = probe(chunks, "terminal" if arm == "whole-buffer-terminal" else arm, reference=arm == "whole-buffer-terminal")
                actual = result["calls"]
                correct = actual == fixture["expected"]
                counts[arm]["correct"] += int(correct)
                counts[arm]["unsafe"] += int(bool(actual) and not correct)
                counts[arm]["missed"] += int(bool(fixture["expected"]) and not correct)
                counts[arm]["errors"] += int(result["error"] is not None)
                raw.append({"fixture": fixture["id"], "partition": partition, "arm": arm, "stream_sha256": hashlib.sha256(blob).hexdigest(), "expected": fixture["expected"], "actual": result, "correct": correct})
                records += 1
    (output/"raw.ndjson").write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True)+"\n" for x in raw), encoding="utf-8")
    write(output/"result.json", {"fixtures": len(fixtures), "units": units, "records": records, "arms": counts, "terminal_correct": counts["terminal"]["correct"], "terminal_failure": units-counts["terminal"]["correct"], "reference_failure": units-counts["whole-buffer-terminal"]["correct"]})


if __name__ == "__main__":
    main()
