"""Deterministic, non-mutating ordering proposals for DJ playlists."""

from math import exp


class PlaylistSorter:
    """Balance target energy placement with end-to-start transition quality."""

    BEAM_WIDTH = 160

    def __init__(self, compatible_keys):
        self.compatible_keys = compatible_keys

    def propose(self, tracks, curve):
        # `playable` already accounts for the global segment-selection overlay.
        # Keep unavailable/skipped entries in the result, but never let them
        # distort the energy curve or transition evaluation.
        available = [dict(track) for track in tracks if track.get("playable")]
        unavailable = [track for track in tracks if not track.get("playable")]
        if not available:
            return {"curve": curve, "score": 0.0, "target": [], "tracks": unavailable}
        for track, energy in zip(available, self._normalize([item["features"].get("energy") for item in available])):
            track["_sort_energy"] = energy
        target = self.targets(curve, len(available))
        beams = [([], frozenset(), 0.0)]
        for position, desired in enumerate(target):
            candidates = []
            for ordered, used, score in beams:
                for track in available:
                    entry_id = track.get("entryId", track["id"])
                    if entry_id in used:
                        continue
                    fit = 1 - abs(track["_sort_energy"] - desired)
                    transition = self.transition_detail(ordered[-1], track) if ordered else {"score": 1.0, "reasons": ["Opening track"]}
                    candidates.append((ordered + [track], used | {entry_id}, score + .5 * fit + .5 * transition["score"]))
            beams = sorted(candidates, key=lambda item: (-item[2], tuple(track.get("entryId", track["id"]) for track in item[0])))[:self.BEAM_WIDTH]
        ordered, _used, score = beams[0]
        rows = []
        for position, track in enumerate(ordered):
            previous = ordered[position - 1] if position else None
            transition = self.transition_detail(previous, track) if previous else {"score": 1.0, "reasons": ["Opening track"]}
            rows.append({
                "id": track["id"], "entry_id": track.get("entryId"), "title": track["title"], "artist": track.get("artist", ""),
                "bpm": track.get("bpm"), "camelot": track.get("camelot"), "energy": track["_sort_energy"],
                "target_energy": target[position], "energy_fit": round(1 - abs(track["_sort_energy"] - target[position]), 3),
                "transition": transition,
            })
        rows.extend({"id": track["id"], "entry_id": track.get("entryId"), "title": track["title"], "artist": track.get("artist", ""), "energy": None, "target_energy": None, "energy_fit": None, "transition": {"score": 0.0, "reasons": ["Skipped or analysis unavailable"]}} for track in unavailable)
        return {"curve": curve, "score": round(score / len(available), 3), "target": target, "tracks": rows}

    @staticmethod
    def targets(curve, count):
        if count == 1:
            return [.5]
        positions = [index / (count - 1) for index in range(count)]
        if curve == "u":
            return [.7 - .9 * position if position <= .5 else .25 + 1.5 * (position - .5) for position in positions]
        if curve == "s":
            return [PlaylistSorter._interpolate([(0, .2), (.35, .85), (.65, .42), (1, 1.0)], position) for position in positions]
        return [.2 + .8 * position for position in positions]

    def transition_detail(self, previous, current):
        if previous is None:
            return {"score": 1.0, "reasons": ["Opening track"]}
        exit_to_entry = self._feature_similarity(previous.get("exit", {}), current.get("entry", {}))
        whole_track = self._feature_similarity(previous.get("features", {}), current.get("features", {}))
        bpm_difference = abs((previous.get("bpm") or 0) - (current.get("bpm") or 0))
        bpm_score = exp(-bpm_difference / 8) if previous.get("bpm") and current.get("bpm") else .5
        compatible = self.compatible_keys(previous.get("camelot"), current.get("camelot")) if previous.get("camelot") and current.get("camelot") else None
        key_score = 1.0 if compatible is True else .15 if compatible is False else .5
        reasons = [f"{bpm_difference:.0f} BPM difference" if previous.get("bpm") and current.get("bpm") else "BPM unavailable"]
        if compatible is True: reasons.append("compatible key")
        elif compatible is False: reasons.append("key clash risk")
        if exit_to_entry >= .8: reasons.append("smooth exit-to-entry flow")
        elif exit_to_entry < .45: reasons.append("large exit-to-entry change")
        return {"score": round(.5 * exit_to_entry + .25 * whole_track + .15 * bpm_score + .1 * key_score, 3), "reasons": reasons}

    @staticmethod
    def _feature_similarity(left, right):
        scales = {"energy": .25, "bass": .25, "rhythm": 80.0, "brightness": 3500.0}
        scores = [max(0.0, 1 - abs(left[key] - right[key]) / scale) for key, scale in scales.items() if isinstance(left.get(key), (int, float)) and isinstance(right.get(key), (int, float))]
        return sum(scores) / len(scores) if scores else .5

    @staticmethod
    def _normalize(values):
        valid = [value for value in values if isinstance(value, (int, float))]
        if not valid or max(valid) - min(valid) < 1e-9:
            return [.5 for _ in values]
        minimum, maximum = min(valid), max(valid)
        return [(value - minimum) / (maximum - minimum) if isinstance(value, (int, float)) else .5 for value in values]

    @staticmethod
    def _interpolate(anchors, position):
        for (start_x, start_y), (end_x, end_y) in zip(anchors, anchors[1:]):
            if position <= end_x:
                return start_y + (end_y - start_y) * (position - start_x) / (end_x - start_x)
        return anchors[-1][1]
