import argparse
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from mix_shazam import main as shazam_main


def slug_from_url(url: str) -> str:
    """Extract the last path segment from a URL as a filename-safe slug."""
    path = urlparse(url).path.rstrip("/")
    return path.split("/")[-1] or "mix"


def main():
    parser = argparse.ArgumentParser(
        prog="shazaming",
        description="Identify tracks in a SoundCloud mix using Shazam",
    )
    parser.add_argument("url", help="SoundCloud mix URL")
    parser.add_argument(
        "-i", "--interval", type=int, default=1,
        help="minutes between samples (default: 1)",
    )
    parser.add_argument(
        "-d", "--duration", type=int, default=20,
        help="sample duration in seconds (default: 20)",
    )
    parser.add_argument(
        "-o", "--output-dir",
        help="output directory (default: derived from URL slug)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="show all detail in terminal",
    )
    args = parser.parse_args()

    slug = slug_from_url(args.url)
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    out_dir = Path(args.output_dir) if args.output_dir else Path("runs") / f"{timestamp}_{slug}"
    out_dir.mkdir(parents=True, exist_ok=True)

    log_file = out_dir / "shazaming.log"
    output = out_dir / "tracklist.json"
    mp3_path = str(out_dir / "mix.mp3")

    # Console handler — INFO by default, DEBUG with -v
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    console.setFormatter(logging.Formatter("%(message)s"))

    # File handler — always DEBUG
    file_handler = logging.FileHandler(log_file, mode="w")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    )

    logging.basicConfig(level=logging.DEBUG, handlers=[console, file_handler])

    asyncio.run(
        shazam_main(
            args.url,
            interval=args.interval,
            duration=args.duration,
            output=str(output),
            mp3_path=mp3_path,
        )
    )


if __name__ == "__main__":
    main()
