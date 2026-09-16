#!/usr/bin/env python3
"""Validate the observable delivery requirements of a short-ad MP4."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def run_json(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def check_receipt(receipt: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    if receipt.get("caption_coverage") != 1.0:
        errors.append("caption_coverage must be 1.0")
    if receipt.get("caption_timing_source") != "final_audio_stt":
        errors.append("caption_timing_source must be final_audio_stt")
    if receipt.get("narration_continuous") is not True:
        errors.append("narration_continuous must be true")
    speed = receipt.get("voice_speed")
    if not isinstance(speed, (int, float)):
        errors.append("voice_speed must be numeric")
    elif speed > 1.08:
        warnings.append(f"voice_speed is {speed}; listen for clipped phrase boundaries")
    hook = receipt.get("hook_end_seconds")
    if not isinstance(hook, (int, float)) or hook > 3.0:
        errors.append("hook_end_seconds must be at most 3.0")
    median = receipt.get("median_shot_seconds")
    if not isinstance(median, (int, float)) or median <= 0:
        errors.append("median_shot_seconds must be a positive number")
    elif median < 0.8:
        warnings.append("median shot length is below 0.8s; review for over-cutting")
    for key in ("rights_checked", "facts_checked", "visual_reviewed"):
        if receipt.get(key) is not True:
            errors.append(f"{key} must be true")


def main() -> int:
    args = parse_args()
    video = args.video.expanduser().resolve()
    receipt_path = args.receipt.expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}

    if not video.is_file():
        raise SystemExit(f"Video not found: {video}")
    if not receipt_path.is_file():
        raise SystemExit(f"Receipt not found: {receipt_path}")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    check_receipt(receipt, errors, warnings)

    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        probe = run_json([
            ffprobe,
            "-v", "error",
            "-show_entries", "stream=codec_type,width,height,duration:format=duration",
            "-of", "json",
            str(video),
        ])
        streams = probe.get("streams", [])
        videos = [stream for stream in streams if stream.get("codec_type") == "video"]
        audios = [stream for stream in streams if stream.get("codec_type") == "audio"]
        if not videos:
            errors.append("MP4 has no video stream")
        if not audios:
            errors.append("MP4 has no audio stream")
        if videos:
            width = int(videos[0].get("width") or 0)
            height = int(videos[0].get("height") or 0)
            checks["dimensions"] = [width, height]
            if not width or not height or height / width < 1.6:
                errors.append(f"video is not vertical enough: {width}x{height}")
        duration = float(probe.get("format", {}).get("duration") or 0)
        checks["duration_seconds"] = round(duration, 3)
        if not 5 <= duration <= 61:
            errors.append(f"duration is outside 5–61 seconds: {duration:.3f}")
        if videos and audios:
            video_duration = float(videos[0].get("duration") or duration)
            audio_duration = float(audios[0].get("duration") or duration)
            delta = abs(video_duration - audio_duration)
            checks["av_duration_delta_seconds"] = round(delta, 3)
            if delta > 0.12:
                errors.append(f"audio/video duration mismatch: {delta:.3f}s")
    else:
        warnings.append("ffprobe is unavailable; stream and duration checks were skipped")

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        decoded = subprocess.run(
            [ffmpeg, "-v", "error", "-i", str(video), "-f", "null", "-"],
            capture_output=True,
            text=True,
        )
        checks["full_decode"] = decoded.returncode == 0
        if decoded.returncode != 0:
            errors.append("full MP4 decode failed")
            warnings.append(decoded.stderr.strip()[-500:])
    else:
        warnings.append("ffmpeg is unavailable; full decode was skipped")

    report = {
        "status": "pass" if not errors else "fail",
        "video": str(video),
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        report_path = args.report.expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
