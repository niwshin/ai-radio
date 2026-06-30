from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from pydantic import ValidationError

from ai_radio.codex_jobs import ensure_job_dirs
from ai_radio.generator_prompt import build_prompt
from ai_radio.models import CodexJobPacket, ScriptOutput


OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["topic_title", "tags", "topic_era", "script", "segments", "sources", "voicevox_text"],
    "properties": {
        "topic_title": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "topic_era": {"type": "string"},
        "script": {"type": "string"},
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "script"],
                "properties": {"title": {"type": "string"}, "script": {"type": "string"}},
            },
            "minItems": 1,
        },
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "url", "published_at", "used_for"],
                "properties": {
                    "title": {"type": "string"},
                    "url": {"type": "string"},
                    "published_at": {"type": ["string", "null"]},
                    "used_for": {"type": ["string", "null"]},
                },
            },
            "minItems": 1,
        },
        "voicevox_text": {"type": "string"},
    },
}


def run_once(data_dir: Path, codex_bin: str = "codex", timeout_seconds: int = 1800) -> bool:
    dirs = ensure_job_dirs(data_dir)
    pending = sorted(dirs["pending"].glob("*.json"))
    if not pending:
        return False

    job_path = pending[0]
    running_path = dirs["running"] / job_path.name
    job_path.rename(running_path)

    try:
        packet = CodexJobPacket.model_validate_json(running_path.read_text(encoding="utf-8"))
        prompt = build_prompt(packet)
        schema_path = dirs["running"] / f"{packet.job_id}.schema.json"
        schema_path.write_text(json.dumps(OUTPUT_SCHEMA, ensure_ascii=False), encoding="utf-8")
        output_path = dirs["completed"] / f"{packet.job_id}.result.json"

        proc = subprocess.run(
            [
                codex_bin,
                "exec",
                "--sandbox",
                "read-only",
                "--ephemeral",
                "--ignore-user-config",
                "--skip-git-repo-check",
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(output_path),
                prompt,
            ],
            cwd=str(dirs["root"]),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr[-4000:] or proc.stdout[-4000:] or f"codex exited {proc.returncode}")

        output = ScriptOutput.model_validate_json(output_path.read_text(encoding="utf-8"))
        output_path.write_text(output.model_dump_json(indent=2), encoding="utf-8")
        running_path.rename(dirs["completed"] / running_path.name)
        return True
    except (Exception, ValidationError) as exc:
        failed_job_path = dirs["failed"] / running_path.name
        if running_path.exists():
            running_path.rename(failed_job_path)
        error_path = dirs["failed"] / f"{job_path.stem}.error.txt"
        error_path.write_text(str(exc), encoding="utf-8")
        return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("./data"))
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval-seconds", type=int, default=20)
    args = parser.parse_args()

    while True:
        did_work = run_once(args.data_dir, args.codex_bin)
        if not args.loop:
            return
        time.sleep(1 if did_work else args.interval_seconds)


if __name__ == "__main__":
    main()
