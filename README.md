# Plex-NFO-Updater

**TODO**: 
- Update the show itself (not only the episodes)
- Change emoji for colors: https://stackoverflow.com/questions/12492810/python-how-can-i-make-the-ansi-escape-codes-to-work-also-in-windows#64222858
- Add verbose option to print more messages and use a custom print message function
- Add reference to Plex Official API: https://developer.plex.tv/pms/
- Review code
- Update README

---

A Python Script that scans local media directories for .nfo and poster files and applies title/summary/poster updates to matching Plex movies or TV episodes.

This README describes what the script does, how to configure it, how to run it, expected NFO format, troubleshooting tips, and one recommended code snippet to make editing metadata more robust.

> ✅ Worked on Linux with my serie with NFO files.

---

## Features

- Recursively scan a provided directory for .nfo files and poster images.
- Match local metadata files to Plex items (movies or TV episodes) by media filename basename.
- Update title and summary (from NFO).
- Upload poster image using plexapi (with an HTTP fallback).
- Interactive selection when multiple Plex candidates are found.
- --dry-run mode to preview changes without applying them.
- Tab completion for path inputs (optional nicety).

---

## Requirements

- Python 3.8+
- pip to install dependencies (script will attempt to auto-install missing third-party packages)
- A working Plex server with a writable token (see Configuration)
- Recommended (but optional): run from a machine that has access to the same filesystem the Plex server uses if you rely on server-side URL poster upload.

### Third-party Python packages used:

- plexapi
- requests
- python-dotenv

---

## Installation

1. Clone or copy the script to a directory.
2. (Recommended) Create a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```
3. Install dependencies (if you prefer not to rely on the script auto-installer):
```bash
pip install plexapi requests python-dotenv
```

---

## Configuration

Create a .env file in the same directory (or export environment variables) with:
```env
# Example .env
PLEX_URL=http://your-plex-host:32400
PLEX_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

- <code>PLEX_URL</code>: full base URL to your Plex server (no trailing / required). Common default: http://<plex-host>:32400.
- <code>PLEX_TOKEN</code>: a Plex token with write permissions; ideally a server/admin token if you expect to edit metadata.

Security note: Never commit .env with your token to public repos.

---

## Usage

Run the script:
```bash
python3 plex_nfo_updater.py
```

Common flags:
```bash
python3 plex_nfo_updater.py --dry-run
```

Interactive flow:

1. Choose whether to limit search to All / TV shows only / Movies only.
2. Enter the directory to operate on (tab completion works if supported).
3. Choose to use detected name, provide name manually, or scan everything under the path.
4. Follow prompts to pick a candidate if multiple Plex matches are found.

---

## Expected NFO format

The script expects simple XML .nfo files containing at least title and plot tags. Minimal example:
```xml
<episodedetails>
  <title>Episode Title</title>
  <plot>This is the episode summary/description.</plot>
  <!-- Other tags are ignored by the script -->
</episodedetails>
```

For movies, a simple movie NFO with title and plot is sufficient:
```xml
<movie>
  <title>Movie Title</title>
  <plot>Movie synopsis.</plot>
</movie>
```
