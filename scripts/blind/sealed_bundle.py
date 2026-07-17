"""Windows-DPAPI sealing for evaluator-only blind artifacts.

The encrypted blobs are safe to commit.  The optional entropy is deliberately
kept outside the repository so ordinary agent/root workflows cannot unseal the
suite accidentally.  DPAPI additionally binds ciphertext to the current
Windows user account.
"""

from __future__ import annotations

import ctypes
import hashlib
import os
from ctypes import wintypes
from pathlib import Path


MAGIC = b"P3BLIND-DPAPI-V1\x00"
CRYPTPROTECT_UI_FORBIDDEN = 0x1


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def default_secret_root() -> Path:
    override = os.environ.get("P3_BLIND_SECRET_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is unavailable; set P3_BLIND_SECRET_ROOT")
    return Path(local_app_data) / "p3" / "blind" / "final_v1"


def entropy_path(secret_root: Path | None = None) -> Path:
    return (secret_root or default_secret_root()) / "dpapi_optional_entropy.bin"


def create_entropy(secret_root: Path | None = None) -> Path:
    path = entropy_path(secret_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"Blind entropy already exists: {path}")
    path.write_bytes(os.urandom(32))
    return path


def load_entropy(secret_root: Path | None = None) -> bytes:
    path = entropy_path(secret_root)
    value = path.read_bytes()
    if len(value) != 32:
        raise ValueError("Blind entropy must be exactly 32 bytes")
    return value


def protect(plaintext: bytes, entropy: bytes) -> bytes:
    encrypted = _crypt_protect(plaintext, entropy)
    return MAGIC + encrypted


def unprotect(ciphertext: bytes, entropy: bytes) -> bytes:
    if not ciphertext.startswith(MAGIC):
        raise ValueError("Not a P3 blind DPAPI bundle")
    return _crypt_unprotect(ciphertext[len(MAGIC) :], entropy)


def _blob(value: bytes) -> tuple[_DataBlob, ctypes.Array[ctypes.c_char]]:
    buffer = ctypes.create_string_buffer(value, len(value))
    return (
        _DataBlob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))),
        buffer,
    )


def _crypt_protect(plaintext: bytes, entropy: bytes) -> bytes:
    if os.name != "nt":
        raise OSError("Phase 2 blind bundles require Windows DPAPI")
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    in_blob, in_buffer = _blob(plaintext)
    entropy_blob, entropy_buffer = _blob(entropy)
    out_blob = _DataBlob()
    ok = crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        "P3 Phase 2 final blind",
        ctypes.byref(entropy_blob),
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    )
    _ = in_buffer, entropy_buffer
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)


def _crypt_unprotect(ciphertext: bytes, entropy: bytes) -> bytes:
    if os.name != "nt":
        raise OSError("Phase 2 blind bundles require Windows DPAPI")
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    in_blob, in_buffer = _blob(ciphertext)
    entropy_blob, entropy_buffer = _blob(entropy)
    out_blob = _DataBlob()
    description = wintypes.LPWSTR()
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        ctypes.byref(description),
        ctypes.byref(entropy_blob),
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    )
    _ = in_buffer, entropy_buffer
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        if description:
            kernel32.LocalFree(description)
        kernel32.LocalFree(out_blob.pbData)
