#!/usr/bin/env python3
"""Generate all manifest audio with bounded concurrency, cache, and retries."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from anki_common import atomic_write_json, configure_utf8_stdio, looks_like_mp3, read_json


async def synthesize_one(
    edge_tts: Any,
    entry: dict[str, Any],
    settings: dict[str, Any],
    media_dir: Path,
    semaphore: asyncio.Semaphore,
    retries: int,
) -> dict[str, Any]:
    target = media_dir / str(entry["filename"])
    if looks_like_mp3(target):
        return {"filename": target.name, "status": "cached", "attempts": 0}

    temp = target.with_name(f".{target.name}.part")
    last_error = ""
    for attempt in range(1, retries + 1):
        try:
            if temp.exists():
                temp.unlink()
            async with semaphore:
                communicate = edge_tts.Communicate(
                    text=str(entry["speech_text"]),
                    voice=str(settings.get("voice", "ja-JP-NanamiNeural")),
                    rate=str(settings.get("rate", "+0%")),
                    volume=str(settings.get("volume", "+0%")),
                    pitch=str(settings.get("pitch", "+0Hz")),
                )
                await communicate.save(temp.as_posix())
            if not looks_like_mp3(temp):
                raise RuntimeError("synthesized file is missing, too small, or not recognizable as MP3")
            os.replace(temp, target)
            return {"filename": target.name, "status": "generated", "attempts": attempt}
        except Exception as exc:  # edge_tts exposes several transport exception types
            last_error = str(exc)
            if temp.exists():
                temp.unlink()
            if attempt < retries:
                await asyncio.sleep((2 ** (attempt - 1)) + random.random() * 0.25)
    return {
        "filename": target.name,
        "status": "failed",
        "attempts": retries,
        "error": last_error,
    }


def promote_package(package_dir: Path, manifest: dict[str, Any], results: list[dict[str, Any]]) -> None:
    pending = package_dir / str(manifest["pending_tsv"])
    final = package_dir / str(manifest["final_tsv"])
    if pending.exists():
        if final.exists():
            raise RuntimeError("final TSV already exists while pending TSV is present")
        os.replace(pending, final)
    elif not final.exists():
        raise RuntimeError("neither pending nor final TSV exists")

    manifest["status"] = "complete"
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
    manifest["audio_summary"] = {
        "total": len(results),
        "generated": sum(result["status"] == "generated" for result in results),
        "cached": sum(result["status"] == "cached" for result in results),
    }
    atomic_write_json(package_dir / "manifest.json", manifest)


async def run(args: argparse.Namespace) -> int:
    package_dir = args.package_dir.resolve()
    manifest_path = package_dir / "manifest.json"
    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise RuntimeError("unsupported or malformed manifest")
    entries = manifest.get("audio_entries")
    settings = manifest.get("audio_settings")
    if not isinstance(entries, list) or not isinstance(settings, dict):
        raise RuntimeError("manifest is missing audio entries or settings")
    if settings.get("backend") != "edge":
        raise RuntimeError("only the edge audio backend is implemented")

    media_dir = package_dir / str(manifest.get("media_dir", "media"))
    media_dir.mkdir(parents=True, exist_ok=True)
    cached: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for entry in entries:
        target = media_dir / str(entry["filename"])
        if looks_like_mp3(target):
            cached.append({"filename": target.name, "status": "cached", "attempts": 0})
        else:
            missing.append(entry)

    generated_results: list[dict[str, Any]] = []
    if missing:
        try:
            import edge_tts  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "edge-tts is not installed for this Python interpreter; run: python -m pip install edge-tts"
            ) from exc

        concurrency = args.concurrency or int(settings.get("concurrency", 4))
        retries = args.retries or int(settings.get("retries", 3))
        if not 1 <= concurrency <= 12:
            raise RuntimeError("concurrency must be between 1 and 12")
        if not 1 <= retries <= 6:
            raise RuntimeError("retries must be between 1 and 6")
        semaphore = asyncio.Semaphore(concurrency)
        tasks = [
            asyncio.create_task(
                synthesize_one(edge_tts, entry, settings, media_dir, semaphore, retries)
            )
            for entry in missing
        ]
        for completed in asyncio.as_completed(tasks):
            result = await completed
            generated_results.append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)

    results = cached + generated_results
    failed = [result for result in results if result["status"] == "failed"]
    report = {
        "status": "incomplete" if failed else "complete",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "total": len(entries),
        "generated": sum(result["status"] == "generated" for result in results),
        "cached": sum(result["status"] == "cached" for result in results),
        "failed": failed,
        "results": sorted(results, key=lambda value: value["filename"]),
    }
    atomic_write_json(package_dir / "audio_report.json", report)
    if failed:
        return 2
    if len(results) != len(entries):
        raise RuntimeError("audio result count does not match manifest")
    promote_package(package_dir, manifest, results)
    print(
        json.dumps(
            {
                "status": "complete",
                "final_tsv": str(package_dir / str(manifest["final_tsv"])),
                "media_dir": str(media_dir),
                "audio": len(results),
            },
            ensure_ascii=False,
        )
    )
    return 0


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_dir", type=Path)
    parser.add_argument("--concurrency", type=int)
    parser.add_argument("--retries", type=int)
    args = parser.parse_args()
    try:
        return asyncio.run(run(args))
    except (OSError, ValueError, KeyError, json.JSONDecodeError, RuntimeError) as exc:
        print(json.dumps({"status": "error", "errors": [str(exc)]}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
