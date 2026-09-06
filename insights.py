"""Read-only fingerprint validation and similarity commands."""

import argparse
import json
from pathlib import Path

from modules.fingerprint import FingerprintSimilarityEngine, FingerprintValidator
from modules.fingerprint.storage import FingerprintCompactor


def records(output_root):
    for path in Path(output_root).glob("*.json"):
        document = json.loads(path.read_text())
        for index, fingerprint in enumerate(document.get("analysis", {}).get("fingerprints", [])):
            yield {"track_id": document["system"]["trackId"], "segment_index": index, "fingerprint": fingerprint}


def main():
    parser = argparse.ArgumentParser(description="Inspect CrateIQ fingerprints")
    parser.add_argument("--output", default="output/tracks")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate")
    commands.add_parser("compact")
    similar = commands.add_parser("similar")
    similar.add_argument("track_id")
    similar.add_argument("segment_index", type=int)
    similar.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    if args.command == "compact":
        compactor = FingerprintCompactor(args.output)
        totals = {"migrated": 0, "already": 0, "skipped": 0, "failed": 0}
        before = after = 0
        for path in sorted(Path(args.output).glob("*.json")):
            try:
                result = compactor.compact_path(path)
                totals[result["status"]] += 1
                before += result.get("before_bytes", 0)
                after += result.get("after_bytes", 0)
            except Exception as error:
                totals["failed"] += 1
                print(f"FAILED\t{path.name}\t{type(error).__name__}: {error}")
        print(" ".join(f"{name}: {count}" for name, count in totals.items()))
        if before:
            print(f"Main JSON: {before} B -> {after} B ({100 * (before - after) / before:.1f}% smaller)")
        return

    items = list(records(args.output))

    if args.command == "validate":
        validator = FingerprintValidator()
        invalid = [item for item in items if validator.validate(item["fingerprint"])]
        print(f"Segments: {len(items)}")
        print(f"Invalid: {len(invalid)}")
        return

    engine = FingerprintSimilarityEngine().fit(items)
    target = next((item for item in items if item["track_id"] == args.track_id and item["segment_index"] == args.segment_index), None)
    if target is None:
        raise SystemExit("Target fingerprint was not found")
    for match in engine.nearest_neighbors(target, items, args.limit):
        print(f"{match.score:.3f}\t{match.track_id}\tsegment {match.segment_index}")


if __name__ == "__main__":
    main()
