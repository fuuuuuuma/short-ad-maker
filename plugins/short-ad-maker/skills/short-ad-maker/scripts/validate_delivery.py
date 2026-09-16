#!/usr/bin/env python3
"""Validate the observable delivery requirements of a short-ad MP4."""

from __future__ import annotations

import argparse
from array import array
import difflib
import json
import math
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--clean-video", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--srt", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def run_json(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


TIME_LINE = re.compile(
    r"^(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s+-->\s+"
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})$"
)


def seconds(parts: tuple[str, ...]) -> float:
    hour, minute, second, millis = map(int, parts)
    return hour * 3600 + minute * 60 + second + millis / 1000


def normalize_caption_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    return "".join(
        char for char in normalized
        if not char.isspace() and not unicodedata.category(char).startswith("P")
    )


def check_captions(
    script_path: Path,
    srt_path: Path,
    errors: list[str],
    checks: dict[str, Any],
) -> tuple[float, list[float]]:
    if not script_path.is_file():
        errors.append(f"narration script not found: {script_path}")
        return 0.0, []
    if not srt_path.is_file():
        errors.append(f"SRT not found: {srt_path}")
        return 0.0, []
    script = normalize_caption_text(script_path.read_text(encoding="utf-8"))
    blocks = re.split(r"\r?\n\s*\r?\n", srt_path.read_text(encoding="utf-8").strip())
    cue_texts: list[str] = []
    previous_end = 0.0
    final_end = 0.0
    cue_midpoints: list[float] = []
    for number, block in enumerate(blocks, 1):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timing_index = next((i for i, line in enumerate(lines) if "-->" in line), -1)
        if timing_index < 0:
            errors.append(f"SRT cue {number} has no timing line")
            continue
        match = TIME_LINE.match(lines[timing_index])
        if not match:
            errors.append(f"SRT cue {number} has invalid timing")
            continue
        start = seconds(match.groups()[:4])
        end = seconds(match.groups()[4:])
        if start >= end:
            errors.append(f"SRT cue {number} has a non-positive duration")
        if start < previous_end - 0.02:
            errors.append(f"SRT cue {number} overlaps the previous cue")
        previous_end = end
        final_end = max(final_end, end)
        cue_midpoints.append((start + end) / 2)
        cue_texts.extend(lines[timing_index + 1:])
    captions = normalize_caption_text("".join(cue_texts))
    ratio = difflib.SequenceMatcher(None, script, captions).ratio() if script else 0.0
    checks["caption_text_similarity"] = round(ratio, 4)
    checks["caption_cues"] = len(blocks)
    checks["caption_end_seconds"] = round(final_end, 3)
    if not script:
        errors.append("narration script is empty")
    elif script != captions:
        errors.append(f"caption text does not exactly cover the narration script: {ratio:.1%}")
    return final_end, cue_midpoints


def decode_audio(ffmpeg: str, path: Path, rate: int = 8000) -> array:
    completed = subprocess.run(
        [ffmpeg, "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"],
        check=True,
        capture_output=True,
    )
    samples = array("h")
    samples.frombytes(completed.stdout)
    return samples


def max_normalized_correlation(left: array, right: array, max_lag: int = 800) -> float:
    length = min(len(left), len(right))
    if length < 4000:
        return 0.0
    stride = max(1, length // 50000)
    left_values = [float(left[i]) for i in range(0, length, stride)]
    right_values = [float(right[i]) for i in range(0, length, stride)]
    mean_left = sum(left_values) / len(left_values)
    mean_right = sum(right_values) / len(right_values)
    left_values = [value - mean_left for value in left_values]
    right_values = [value - mean_right for value in right_values]
    lag_limit = max(1, max_lag // stride)
    lag_step = max(1, 32 // stride)
    best = 0.0
    for lag in range(-lag_limit, lag_limit + 1, lag_step):
        if lag >= 0:
            a, b = left_values[lag:], right_values[:len(left_values) - lag]
        else:
            a, b = left_values[:len(left_values) + lag], right_values[-lag:]
        if not a or not b:
            continue
        dot = sum(x * y for x, y in zip(a, b))
        norm = math.sqrt(sum(x * x for x in a) * sum(y * y for y in b))
        if norm:
            best = max(best, abs(dot / norm))
    return best


def check_audio_mix(
    ffmpeg: str,
    final_video: Path,
    components: list[Path],
    errors: list[str],
    checks: dict[str, Any],
) -> None:
    final_audio = decode_audio(ffmpeg, final_video)
    correlations: dict[str, float] = {}
    for component in components:
        correlation = max_normalized_correlation(final_audio, decode_audio(ffmpeg, component))
        correlations[component.stem] = round(correlation, 4)
        if correlation < 0.015:
            errors.append(f"audio component is not detectably present in final mix: {component.name}")
    checks["audio_component_correlations"] = correlations


def frame_bytes(ffmpeg: str, path: Path, at: float) -> bytes:
    completed = subprocess.run(
        [ffmpeg, "-v", "error", "-ss", f"{at:.3f}", "-i", str(path), "-vf", "scale=180:320,format=gray", "-frames:v", "1", "-f", "rawvideo", "-"],
        check=True,
        capture_output=True,
    )
    return completed.stdout


def check_caption_burn(
    ffmpeg: str,
    clean_video: Path,
    final_video: Path,
    cue_midpoints: list[float],
    errors: list[str],
    checks: dict[str, Any],
) -> None:
    if not cue_midpoints:
        errors.append("no caption cues available for burn verification")
        return
    sample_times = cue_midpoints if len(cue_midpoints) <= 8 else cue_midpoints[::max(1, len(cue_midpoints) // 8)][:8]
    changed = 0
    differences: list[float] = []
    for at in sample_times:
        clean = frame_bytes(ffmpeg, clean_video, at)
        final = frame_bytes(ffmpeg, final_video, at)
        if not clean or len(clean) != len(final):
            errors.append(f"could not compare caption frame at {at:.3f}s")
            continue
        mean_difference = sum(abs(a - b) for a, b in zip(clean, final)) / len(clean)
        differences.append(round(mean_difference, 4))
        if mean_difference >= 0.35:
            changed += 1
    checks["caption_frame_mean_differences"] = differences
    checks["caption_frames_changed"] = changed
    required = max(1, math.ceil(len(sample_times) * 0.75))
    if changed < required:
        errors.append(f"caption burn is not visible in enough sampled frames: {changed}/{len(sample_times)}")


def check_audio_components(
    receipt: dict[str, Any],
    project_root: Path,
    errors: list[str],
    checks: dict[str, Any],
) -> list[Path]:
    components = receipt.get("audio_components")
    if not isinstance(components, dict):
        errors.append("audio_components must list narration, bgm, and sfx")
        return []
    found: list[Path] = []
    for name in ("narration", "bgm", "sfx"):
        relative = components.get(name)
        if not isinstance(relative, str) or not relative:
            errors.append(f"audio_components.{name} is missing")
            continue
        candidate = (project_root / relative).resolve()
        try:
            candidate.relative_to(project_root)
        except ValueError:
            errors.append(f"audio_components.{name} points outside the project")
            continue
        if not candidate.is_file() or candidate.stat().st_size < 64:
            errors.append(f"audio component is missing or empty: {name}")
            continue
        found.append(candidate)
    checks["audio_components_found"] = len(found)
    return found


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
    clean_video = args.clean_video.expanduser().resolve()
    receipt_path = args.receipt.expanduser().resolve()
    script_path = args.script.expanduser().resolve()
    srt_path = args.srt.expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}

    if not video.is_file():
        raise SystemExit(f"Video not found: {video}")
    if not clean_video.is_file():
        raise SystemExit(f"Clean video not found: {clean_video}")
    if not receipt_path.is_file():
        raise SystemExit(f"Receipt not found: {receipt_path}")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    check_receipt(receipt, errors, warnings)
    caption_end, cue_midpoints = check_captions(script_path, srt_path, errors, checks)
    project_root = receipt_path.parent.parent.resolve()
    audio_components = check_audio_components(receipt, project_root, errors, checks)

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
        if caption_end > duration + 0.12:
            errors.append("the final caption ends after the MP4")
        if videos and audios:
            video_duration = float(videos[0].get("duration") or duration)
            audio_duration = float(audios[0].get("duration") or duration)
            delta = abs(video_duration - audio_duration)
            checks["av_duration_delta_seconds"] = round(delta, 3)
            if delta > 0.12:
                errors.append(f"audio/video duration mismatch: {delta:.3f}s")
        for component in audio_components:
            component_probe = run_json([
                ffprobe, "-v", "error", "-show_entries", "stream=codec_type:format=duration",
                "-of", "json", str(component),
            ])
            if not any(stream.get("codec_type") == "audio" for stream in component_probe.get("streams", [])):
                errors.append(f"audio component has no audio stream: {component.name}")
    else:
        errors.append("ffprobe is required for delivery validation")

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
        check_audio_mix(ffmpeg, video, audio_components, errors, checks)
        check_caption_burn(ffmpeg, clean_video, video, cue_midpoints, errors, checks)
    else:
        errors.append("ffmpeg is required for delivery validation")

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
