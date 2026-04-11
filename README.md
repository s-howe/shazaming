# shazaming

Automatically identify tracks in a SoundCloud mix using Shazam.

Give it a SoundCloud URL and it downloads the mix, samples it at regular intervals, and builds a timestamped tracklist by fingerprinting each chunk against the Shazam API.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [ffmpeg](https://ffmpeg.org/download.html) (`brew install ffmpeg` or `apt install ffmpeg`)

## Installation

```bash
git clone https://github.com/s-howe/shazaming
cd shazaming
uv sync
```

## Usage

```bash
uv run shazaming <soundcloud-url>
```

```bash
uv run shazaming https://soundcloud.com/awkscl/awkwardly-cast-063-ecki-pirates
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `-i`, `--interval` | `1` | Minutes between samples |
| `-d`, `--duration` | `20` | Sample duration in seconds |
| `-o`, `--output-dir` | auto | Override the output directory |
| `-v`, `--verbose` | off | Show all detail in the terminal |

## Output

Each run creates a timestamped directory under `runs/`:

```
runs/
  2026-04-10T14-30-00_flying-saucer-fm-w-enchanted-rhythms/
    mix.mp3          # downloaded audio
    tracklist.json   # full results with timestamps, artist, label, URLs
    shazaming.log    # verbose debug log
```

`tracklist.json` includes every sampled chunk — matched, unmatched, and errored — with Shazam and Apple Music URLs where available.

## Tips

- Shazam works best on clean sections of a track, not transitions. If you're getting few matches, try a **shorter interval** (`-i 1` or `-i 0.5`) to sample more frequently.
- Increasing the **sample duration** (`-d 25`) gives Shazam more signal on harder-to-identify tracks.
- Use `-v` to see every chunk result in the terminal while it runs.

## License

MIT
