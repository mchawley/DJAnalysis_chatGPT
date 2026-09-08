# CrateIQ

CrateIQ is a local DJ-library analysis tool. It reads your music files and optional Rekordbox export, then helps you understand the energy, structure, rhythm, and compatibility of the music you already own.

It runs on your own computer. Your music is not uploaded anywhere.

## What CrateIQ can do

- Read common DJ audio formats: MP3, FLAC, WAV, AIFF, and M4A.
- Import metadata, playlists, cues, colours, ratings, BPM, and key from a Rekordbox XML export.
- Reuse available Rekordbox structural/analysis data.
- Build phrase-level fingerprints for energy, bass, rhythm, and spectrum.
- Inspect a track’s sections, waveforms, and similar segments.
- Review playlist flow, spot unusual transitions, and choose the phrases you actually plan to play.

## Before you begin

You need:

1. A computer with **Python 3.12 or newer** installed.
2. Your music files stored locally or on a mounted drive.
3. Optionally, a Rekordbox XML export.

CrateIQ does not modify your audio files, Rekordbox database, or exported XML. It writes its own analysis files into the output folder you choose during Setup.

## First-time installation

Open **Terminal** on macOS (Applications → Utilities → Terminal), then go to the folder containing this project. For example:

```bash
cd /path/to/DJAnalysis_chatGPT
```

Create a private Python environment for CrateIQ:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install the required packages:

```bash
pip install -r requirements.txt
```

You only need to create the environment and install packages once per copy of the project.

## Start CrateIQ

Whenever you want to use CrateIQ, open Terminal, go to the project folder, activate the environment, and start the local app:

```bash
cd /path/to/DJAnalysis_chatGPT
source .venv/bin/activate
python ui.py
```

Terminal will show an address similar to:

```text
CrateIQ Insights: http://127.0.0.1:8765
```

Open that address in your browser. Keep the Terminal window open while using CrateIQ. To stop the app later, return to Terminal and press `Control + C`.

## Set up your library

On the CrateIQ home page, choose **Setup**.

### Music folders

Enter one music-folder path per line. For example:

```text
/Users/your-name/Music
/Volumes/DJ Drive/Music
```

Use the full folder path. If you are unsure of a path on macOS, drag a folder from Finder into Terminal; Terminal will paste its full path.

### Rekordbox XML export

This is optional, but recommended if you use Rekordbox. Export it from Rekordbox, then paste the path to the exported `.xml` file into CrateIQ Setup.

The XML allows CrateIQ to import playlist ordering, ratings, colours, comments, cue points, BPM, and key. CrateIQ only reads this export; it does not change Rekordbox.

### Output location

The default `./output/tracks` is suitable for most users. This is where CrateIQ stores its own track documents, compact raw-feature files, playlist copies, and your segment choices.

If you change this location, choose a folder with plenty of free disk space and do not delete it unless you intentionally want to remove CrateIQ’s analysis.

### Advanced settings

Most users can leave these settings as they are.

- **Workers** controls how many fingerprint tasks can run in parallel. Leave it at `2` if you are unsure.
- **Formats** controls which audio extensions CrateIQ scans.
- **Modules** control which types of data are collected. The default Full Rekordbox setup enables all modules.

Use **Validate paths** before saving. Once everything is valid, choose **Save setup**.

## Run analysis

Open **Analysis** from the home page.

This page shows your saved music folders and lets you choose what to run for this one session. These choices do not change your saved Setup settings.

For a first complete run, leave all modules selected and choose **Start analysis**. Depending on your library size and computer, this can take a long time. You can leave the browser tab open and follow the live stage/log display.

Use **Stop safely** if you need to pause. CrateIQ finishes the current safe unit of work, then stops before starting more work. Previously completed results remain available.

Later runs are incremental: CrateIQ skips work that is already current where possible.

## Use the results

### Track analysis

Open **Tracks** to search your analyzed library.

- Click a coloured section in the timeline to inspect that phrase.
- Use the waveform and energy/rhythm panels to understand the segment.
- Use the play icon to preview only the selected segment.
- The loop icon repeats the selected segment while you compare it.
- Use Include/Exclude to decide which segments are globally playable in playlist analysis. This does not delete any audio or fingerprint data.
- Choose **Find similar segments** to compare the selected phrase with the rest of your library.

### Playlist analysis

Open **Playlists** to view imported Rekordbox playlists or create a local CrateIQ playlist.

- Review energy, bass, rhythm density, brightness, and tempo across the order.
- Look for transition-break or outlier badges.
- Use segment strips to exclude phrases you do not plan to play.
- Reorder, remove, or add tracks to local playlist copies without changing Rekordbox.

## Where your information is stored

Your personal configuration is saved as:

```text
config/config.json
```

It is intentionally ignored by Git, so your local music paths are not shared when you share this project. The safe template is:

```text
config/config.example.json
```

Analysis results are stored under the output folder, normally:

```text
output/tracks
```

Do not add your personal `config/config.json` or `output/` folder to Git.

## Troubleshooting

### “Complete Setup before starting analysis”

Open **Setup**, add at least one real music folder, validate the paths, and save.

### A folder or XML path is invalid

Check that the path exists and is written in full. On macOS, dragging the file or folder from Finder into Terminal is the easiest way to obtain an exact path.

### Browser cannot play a segment

CrateIQ serves the original local file to the browser. MP3, M4A, and WAV are commonly supported; FLAC and AIFF support varies by browser. The analysis itself can still work even when browser preview is unavailable.

### Rekordbox data does not appear

Confirm that the XML path points to a real Rekordbox XML export and that the Rekordbox modules are selected. Tracks must also match by file path, filename, or title and artist.

### Analysis is slow

Fingerprinting requires audio decoding and is the most demanding step. Start with a smaller music folder, use fewer modules, or leave the worker count at `2` to keep the computer responsive.

### I moved my music files

Update the music folders in Setup and run analysis again. CrateIQ will refresh its stored file references where it can.

## Updating CrateIQ

If you pull a newer version from GitHub, activate the virtual environment and run:

```bash
pip install -r requirements.txt
```

Then start `python ui.py` again. Your `config/config.json` and analysis output remain local.
