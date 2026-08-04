"""Read-only fingerprint validation and similarity commands."""

import argparse
import json
from pathlib import Path

from modules.fingerprint import FingerprintSimilarityEngine, FingerprintValidator


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
    similar = commands.add_parser("similar")
    similar.add_argument("track_id")
    similar.add_argument("segment_index", type=int)
    similar.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
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
