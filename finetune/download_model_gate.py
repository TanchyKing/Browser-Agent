"""Bounded, resumable model-download Gate with frozen shard verification."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any


def emit(event: str, **fields: Any) -> None:
    print(json.dumps({"event": event, "time": time.time(), **fields}, ensure_ascii=False), flush=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def configure_environment(args: argparse.Namespace) -> None:
    os.environ["HF_HOME"] = str(args.hf_home)
    os.environ["HF_ENDPOINT"] = args.endpoint
    os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = str(args.download_timeout)
    os.environ.pop("HF_HUB_OFFLINE", None)
    if args.direct:
        for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            os.environ.pop(name, None)
        os.environ["NO_PROXY"] = "*"
        os.environ["no_proxy"] = "*"
    else:
        os.environ["HTTP_PROXY"] = args.proxy
        os.environ["HTTPS_PROXY"] = args.proxy
        os.environ.pop("NO_PROXY", None)
        os.environ.pop("no_proxy", None)
    if args.disable_xet:
        os.environ["HF_HUB_DISABLE_XET"] = "1"
    else:
        os.environ.pop("HF_HUB_DISABLE_XET", None)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--hf-home", required=True, type=Path)
    parser.add_argument("--runtime-dir", required=True, type=Path)
    parser.add_argument("--route", required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--proxy", default="http://127.0.0.1:7897")
    parser.add_argument("--direct", action="store_true")
    parser.add_argument("--disable-xet", action="store_true")
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--max-attempts-per-file", type=int, default=5)
    parser.add_argument("--download-timeout", type=int, default=300)
    args = parser.parse_args()

    if args.max_workers not in (1, 2):
        raise ValueError("CORRECTION-2 permits only max_workers 1 or 2")
    if args.max_attempts_per_file <= 0:
        raise ValueError("max-attempts-per-file must be positive")
    configure_environment(args)

    # Import after all Hugging Face environment variables are fixed.
    from huggingface_hub import hf_hub_download

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    args.runtime_dir.mkdir(parents=True, exist_ok=True)
    shards = {item["filename"]: item for item in manifest["shards"]}
    targets = list(shards) + list(manifest["required_metadata_files"])
    proxy_map = None if args.direct else {"http": args.proxy, "https": args.proxy}
    resolved: dict[str, Path] = {}

    emit(
        "gate_start",
        route=args.route,
        endpoint=args.endpoint,
        direct=args.direct,
        max_workers=args.max_workers,
        max_attempts_per_file=args.max_attempts_per_file,
        hf_home=str(args.hf_home),
        revision=manifest["revision"],
        disable_xet=args.disable_xet,
    )

    def download_one(filename: str) -> tuple[str, Path]:
        last_error: Exception | None = None
        for attempt in range(1, args.max_attempts_per_file + 1):
            emit("download_attempt", filename=filename, attempt=attempt, route=args.route)
            try:
                path = Path(
                    hf_hub_download(
                        repo_id=manifest["repo_id"],
                        filename=filename,
                        revision=manifest["revision"],
                        endpoint=args.endpoint,
                        proxies=proxy_map,
                        etag_timeout=60,
                        resume_download=True,
                    )
                )
                emit("download_file_complete", filename=filename, path=str(path), size=path.stat().st_size)
                return filename, path
            except Exception as exc:  # bounded process-level retry is intentional here
                last_error = exc
                emit(
                    "download_attempt_failed",
                    filename=filename,
                    attempt=attempt,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                if attempt < args.max_attempts_per_file:
                    time.sleep(min(30, 2**attempt))
        assert last_error is not None
        raise RuntimeError(f"exhausted attempts for {filename}") from last_error

    failures: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        future_to_name = {executor.submit(download_one, filename): filename for filename in targets}
        for future in concurrent.futures.as_completed(future_to_name):
            filename = future_to_name[future]
            try:
                name, path = future.result()
                resolved[name] = path
            except Exception as exc:
                failures.append(filename)
                emit("download_file_exhausted", filename=filename, error_type=type(exc).__name__, error=str(exc))

    if failures:
        status = {"status": "download_failed", "route": args.route, "failed_files": sorted(failures)}
        (args.runtime_dir / f"status_{args.route}.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        emit("gate_failed", **status)
        return 2

    verified: list[dict[str, Any]] = []
    total_size = 0
    verification_failed = False
    for filename, expected in shards.items():
        path = resolved[filename]
        actual_size = path.stat().st_size
        actual_sha256 = sha256_file(path)
        ok = actual_size == expected["size"] and actual_sha256 == expected["sha256"]
        total_size += actual_size
        verified.append(
            {
                "filename": filename,
                "path": str(path),
                "expected_size": expected["size"],
                "actual_size": actual_size,
                "expected_sha256": expected["sha256"],
                "actual_sha256": actual_sha256,
                "ok": ok,
            }
        )
        emit("verify_file", filename=filename, size=actual_size, sha256=actual_sha256, ok=ok)
        verification_failed = verification_failed or not ok

    expected_file_bytes = manifest["expected_total_shard_file_bytes"]
    total_file_bytes_ok = total_size == expected_file_bytes
    index = json.loads(resolved["model.safetensors.index.json"].read_text(encoding="utf-8"))
    actual_tensor_bytes = index.get("metadata", {}).get("total_size")
    expected_tensor_bytes = manifest["expected_total_tensor_bytes_from_index"]
    total_tensor_bytes_ok = actual_tensor_bytes == expected_tensor_bytes
    status = {
        "status": (
            "passed"
            if not verification_failed and total_file_bytes_ok and total_tensor_bytes_ok
            else "verification_failed"
        ),
        "route": args.route,
        "repo_id": manifest["repo_id"],
        "revision": manifest["revision"],
        "hf_home": str(args.hf_home),
        "expected_total_shard_file_bytes": expected_file_bytes,
        "actual_total_shard_file_bytes": total_size,
        "total_shard_file_bytes_ok": total_file_bytes_ok,
        "expected_total_tensor_bytes_from_index": expected_tensor_bytes,
        "actual_total_tensor_bytes_from_index": actual_tensor_bytes,
        "total_tensor_bytes_ok": total_tensor_bytes_ok,
        "verified_shards": verified,
    }
    (args.runtime_dir / f"status_{args.route}.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    emit(
        "gate_complete",
        status=status["status"],
        total_file_bytes=total_size,
        total_file_bytes_ok=total_file_bytes_ok,
        total_tensor_bytes=actual_tensor_bytes,
        total_tensor_bytes_ok=total_tensor_bytes_ok,
    )
    return 0 if status["status"] == "passed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
