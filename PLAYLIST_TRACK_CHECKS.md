# Playlist Track Checks

CrateIQ evaluates a playlist as an ordered DJ sequence. It does not score a
track in isolation.

## Inputs

For every analyzed track, the deck uses the mean of its fingerprint segments
for energy, bass, rhythm density, and brightness. Tempo is taken from the
Rekordbox library value and the musical key is converted to Camelot notation.
Tracks without fingerprints remain visible but are excluded from checks that
require analysis data.

## Trend charts

Each chart has one point per playlist track. Values are normalized only within
the current playlist so the movement is easy to compare. The source value is
never removed or averaged away: every point remains in the SVG path and shows
its raw value on hover. Curves are smoothed visually with a cubic path through
those same points; smoothing does not alter stored fingerprint data.

## Transition breaks

Transition checks are directional: a track is compared only with the track
immediately before it. The first track has no incoming transition.

A transition is flagged when one or more of these thresholds are exceeded:

- Energy changes by more than `0.12`.
- Bass changes by more than `0.18`.
- Rhythm density changes by more than `20`.
- Spectral-centroid brightness changes by more than `900 Hz`.
- Tempo changes by more than `8 BPM`.
- The Camelot transition is outside the supported harmonic moves.

The UI lists the specific contributing reasons. A transition with three or
more reasons is high severity; one or two reasons is medium severity.

## Camelot compatibility

The compatibility check accepts the relationship types shown in the supplied
Camelot wheel:

- Same key (perfect mix).
- Same mode: one step either direction, `+2` energy boost, `+7` Jaw's mix.
- Opposite mode: same number (scale change), `-1` diagonal mix, or `+3` mood
  shifter.

Numbers wrap around the wheel, so `12A → 1A` is valid. In particular,
`11A → 12A` is a valid `+1` transition and must not be reported as a key clash.

## Playlist outliers

Outliers are separate from transition breaks. A track is compared with the
whole playlist using the robust median and median absolute deviation for
energy, bass, rhythm, and brightness. A feature more than `3.5` robust
standard deviations from the playlist centre is reported as unusual. At least
three analyzed tracks are required before this check is shown.
