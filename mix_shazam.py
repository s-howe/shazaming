#!/usr/bin/env python3
"""
mix_shazam.py — Download a SoundCloud mix and identify tracks via Shazam

Dependencies:
    pip install shazamio yt-dlp pydub
    apt install ffmpeg  (or brew install ffmpeg)
"""

import asyncio
import json
import logging
import os
import sys
from contextlib import contextmanager
from pathlib import Path
import subprocess

from pydub import AudioSegment
from shazamio import Shazam

logger = logging.getLogger(__name__)


@contextmanager
def _suppress_stderr():
    """Temporarily redirect fd 2 to /dev/null to silence subprocess stderr."""
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(old_stderr)


def download_mix(url: str, output_path: str = "mix.mp3") -> str:
    """Download SoundCloud URL to mp3 via yt-dlp."""
    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "0",
        "--force-overwrites",
        "--quiet",
        "--progress",
        "-o",
        output_path,
        url,
    ]
    logger.info(f"Downloading: {url}")
    subprocess.run(cmd, check=True)
    return output_path


def slice_mix(
    mp3_path: str, chunk_every_minutes: int = 2, chunk_duration_ms: int = 12_000
):
    """Yield (offset_seconds, AudioSegment) for each sample point."""
    logger.debug(f"Loading audio: {mp3_path}")
    with _suppress_stderr():
        audio = AudioSegment.from_mp3(mp3_path)
    step_ms = chunk_every_minutes * 60 * 1000
    offset_ms = 0
    while offset_ms < len(audio):
        chunk = audio[offset_ms : offset_ms + chunk_duration_ms]
        yield offset_ms // 1000, chunk
        offset_ms += step_ms


async def recognize_chunk(
    shazam: Shazam,
    chunk: AudioSegment,
    offset_sec: int,
    tmp_path: str,
):
    """Export chunk to tmp file and send to Shazam."""
    with _suppress_stderr():
        chunk.export(tmp_path, format="mp3")
        result = await shazam.recognize(tmp_path)
    return result


def format_tracklist(results: list[dict]) -> str:
    """Render a deduplicated tracklist as human-readable text."""
    lines = ["--- TRACKLIST ---"]
    seen = set()
    for r in results:
        if r.get("title") and r["title"] not in seen:
            seen.add(r["title"])
            lines.append(f"[{r['timestamp']}] {r['artist']} - {r['title']}")
    return "\n".join(lines)


def format_timestamp(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def extract_track_info(result: dict) -> dict | None:
    """Pull the relevant fields out of the Shazam response."""
    track = result.get("track")
    if not track:
        return None
    sections = track.get("sections") or []
    metadata = sections[0].get("metadata") if sections else []
    actions = track.get("hub", {}).get("actions", [])
    return {
        "title": track.get("title"),
        "artist": track.get("subtitle"),
        "label": metadata[0].get("text") if metadata else None,
        "shazam_url": track.get("url"),
        "apple_music_url": next((a.get("uri") for a in actions if a.get("uri")), None),
    }


async def main(
    url: str,
    *,
    interval: int = 1,
    duration: int = 20,
    output: str = "tracklist.json",
    mp3_path: str = "mix.mp3",
):
    download_mix(url, output_path=mp3_path)
    shazam = Shazam()
    results = []
    seen_titles = set()
    tmp_chunk_path = str(Path(mp3_path).with_name("chunk.mp3"))

    for offset_sec, chunk in slice_mix(
        mp3_path, chunk_every_minutes=interval, chunk_duration_ms=duration * 1000
    ):
        ts = format_timestamp(offset_sec)
        logger.debug(f"[{ts}] Recognizing...")

        try:
            result = await recognize_chunk(shazam, chunk, offset_sec, tmp_chunk_path)
            info = extract_track_info(result)
        except Exception as e:
            logger.error(f"[{ts}] ERROR: {e}")
            results.append({"timestamp": ts, "offset_sec": offset_sec, "error": str(e)})
            continue

        if info:
            key = f"{info['artist']} - {info['title']}"
            if key not in seen_titles:
                seen_titles.add(key)
                logger.info(f"[{ts}] ✓ {key}")
            else:
                logger.debug(f"[{ts}] (same: {key})")
            results.append({"timestamp": ts, "offset_sec": offset_sec, **info})
        else:
            logger.debug(f"[{ts}] ✗ no match")
            results.append(
                {
                    "timestamp": ts,
                    "offset_sec": offset_sec,
                    "title": None,
                    "artist": None,
                }
            )

    with open(output, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"Done. Results saved to {output}")

    print(f"\n{format_tracklist(results)}")

    return results
