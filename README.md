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

## Telegram bot

A single-user Telegram frontend is included in `bot.py`: send it a SoundCloud URL and it replies with the tracklist once the job finishes.

### Setup

1. Message [@BotFather](https://t.me/BotFather) on Telegram, run `/newbot`, and copy the bot token it gives you.
2. Message [@userinfobot](https://t.me/userinfobot) to get your own numeric Telegram user ID.
3. Create a `.env` file in the repo root (not committed):

   ```
   TELEGRAM_BOT_TOKEN=123456789:your-token-from-botfather
   TELEGRAM_OWNER_ID=your-numeric-telegram-id
   ```

4. `uv sync` to install the bot's dependencies.

### Running

```bash
uv run shazaming-bot
```

Only messages from `TELEGRAM_OWNER_ID` are processed; everyone else is silently ignored. Jobs run one at a time — sending a new URL while one is in progress gets a "busy" reply. Each job writes to `runs/` exactly like the CLI.

### Running as a service (systemd)

Create `/etc/systemd/system/shazaming-bot.service`:

```ini
[Unit]
Description=Shazaming Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=<your-user>
Group=<your-user>
WorkingDirectory=/home/<your-user>/shazaming
EnvironmentFile=/home/<your-user>/shazaming/.env
ExecStart=/home/<your-user>/.local/bin/uv run bot.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now shazaming-bot
sudo systemctl status shazaming-bot
```

## License

MIT
