# CrateIQ

CrateIQ analyzes a local DJ library, imports Rekordbox data, and provides track and playlist insights.

## Quick start

1. Create and activate a Python environment, then run `pip install -r requirements.txt`.
2. Start the local app with `python ui.py`.
3. Open `http://127.0.0.1:8765`, choose **Setup**, and add your music folders and optional Rekordbox XML export.
4. Use **Analysis** to choose modules for a local run. Then explore **Tracks** and **Playlists**.

Your personal paths are written to `config/config.json`, which is deliberately ignored by Git. `config/config.example.json` documents the portable defaults.

The app is local-only and binds to `127.0.0.1`.
