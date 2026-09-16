#!/usr/bin/env python3
"""Find the latest MEGA file in every Fanbox post and sync missing files.

The script deliberately supports every ``*.txt`` export (not only
``links-*.txt``), while preferring the latter when two exports describe the
same post.  Paths and the lookback window are loaded from ``.env``.

MEGA public files are downloaded through MEGA's public API and decrypted
locally.  Completed and already-existing files are checked against the MAC
embedded in the public link, so an unrelated same-name file is never treated
as a valid match.
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import re
import struct
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import requests
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


LOG = logging.getLogger("fanbox-mega-sync")
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ENV_FILE = SCRIPT_DIR / ".env"

_MEGA_URL_RE = re.compile(
    r"https?://(?:www\.)?mega\.nz/file/[A-Za-z0-9_-]+#[A-Za-z0-9_-]+",
    re.IGNORECASE,
)
_UPDATE_RE = re.compile(r"\bupdate\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)
_UPDATE_DATE_RE = re.compile(
    r"\bupdate\s*([0-9]+(?:\.[0-9]+)?)\s*\(([^)]+)\)", re.IGNORECASE
)
_FOLDER_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:-|$)")
_EXPORT_REVISION_RE = re.compile(r"\s+\((\d+)\)\.txt$", re.IGNORECASE)
_WINDOWS_BAD_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class SyncError(RuntimeError):
    """An expected, user-actionable sync failure."""


@dataclass(frozen=True)
class MegaLink:
    url: str
    handle: str
    raw_key: bytes
    aes_key: bytes
    iv: bytes
    expected_mac: tuple[int, int]


@dataclass(frozen=True)
class LinkCandidate:
    source_file: Path
    post_dir: Path
    title: str
    url: str
    handle: str
    version: Decimal | None
    update_date: date | None
    source_date: date | None
    label_score: int
    source_mtime: float

    @property
    def effective_date(self) -> date | None:
        return self.update_date or self.source_date


@dataclass(frozen=True)
class RemoteFile:
    link: MegaLink
    name: str
    size: int
    download_url: str


def configure_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass


def setup_logging(log_file: Path, verbose: bool = False) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    LOG.setLevel(logging.DEBUG)
    LOG.handlers.clear()
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    LOG.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(fmt)
    LOG.addHandler(console)


def load_env_file(path: Path) -> dict[str, str]:
    """Load a small dotenv-compatible file without adding a dependency."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise SyncError(f"{path}:{line_number}: expected NAME=VALUE")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise SyncError(f"{path}:{line_number}: invalid environment name {key!r}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def env_value(values: dict[str, str], name: str, default: str = "") -> str:
    return os.environ.get(name, values.get(name, default))


def env_bool(values: dict[str, str], name: str, default: bool) -> bool:
    raw = env_value(values, name, "true" if default else "false").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise SyncError(f"{name} must be true/false, got {raw!r}")


def decode_b64url(value: str) -> bytes:
    value = value.strip().replace("\\_", "_").replace("\\-", "-")
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, base64.binascii.Error) as exc:
        raise SyncError("invalid base64 data in MEGA link") from exc


def parse_mega_link(url: str) -> MegaLink:
    normalized = url.strip().rstrip(".,;)").replace("\\_", "_").replace("\\-", "-")
    parsed = urlparse(normalized)
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.netloc.lower() not in {"mega.nz", "www.mega.nz"}:
        raise SyncError(f"unsupported MEGA host in {normalized}")
    if len(parts) != 2 or parts[0].lower() != "file":
        raise SyncError(f"only MEGA public file links are supported: {normalized}")
    if not parsed.fragment:
        raise SyncError(f"MEGA link has no decryption key: {normalized}")

    raw_key = decode_b64url(parsed.fragment)
    if len(raw_key) != 32:
        raise SyncError(
            f"MEGA file key must decode to 32 bytes, got {len(raw_key)}: {normalized}"
        )
    words = struct.unpack(">8I", raw_key)
    aes_key = struct.pack(
        ">4I",
        words[0] ^ words[4],
        words[1] ^ words[5],
        words[2] ^ words[6],
        words[3] ^ words[7],
    )
    iv = struct.pack(">4I", words[4], words[5], 0, 0)
    return MegaLink(
        url=normalized,
        handle=parts[1],
        raw_key=raw_key,
        aes_key=aes_key,
        iv=iv,
        expected_mac=(words[6], words[7]),
    )


def parse_date_text(raw: str) -> date | None:
    value = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", raw.strip())
    value = re.sub(r"\s+", " ", value)
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def parse_version(line: str) -> Decimal | None:
    match = _UPDATE_RE.search(line)
    if not match:
        return None
    try:
        return Decimal(match.group(1))
    except InvalidOperation:
        return None


def version_label(version: Decimal | None) -> str:
    if version is None:
        return "original"
    return f"Update{version.normalize()}"


def post_title(post_dir: Path, text: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line and not line.startswith("http") and len(line) <= 180:
            return line
    return _FOLDER_DATE_RE.sub("", post_dir.name).lstrip("-") or post_dir.name


def label_score(line: str, source_file: Path) -> int:
    prefix = line.split("https://", 1)[0].lower()
    score = 0
    if "update" in prefix:
        score += 8
    if re.search(r"\b(?:mod\s*)?dl\b|download", prefix):
        score += 5
    if source_file.name.lower().startswith("links-"):
        score += 1
    return score


def parse_text_export(path: Path) -> list[LinkCandidate]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="replace")
    post_dir = path.parent
    title = post_title(post_dir, text)

    source_date = None
    folder_match = _FOLDER_DATE_RE.match(post_dir.name)
    if folder_match:
        source_date = parse_date_text(folder_match.group(1))

    update_dates: dict[Decimal, date] = {}
    for version_raw, date_raw in _UPDATE_DATE_RE.findall(text):
        try:
            version = Decimal(version_raw)
        except InvalidOperation:
            continue
        parsed_date = parse_date_text(date_raw)
        if parsed_date:
            update_dates[version] = parsed_date

    # A URL is commonly printed once at the top and again on a labelled DL
    # line. Merge those occurrences and retain the best available metadata.
    by_url: dict[str, LinkCandidate] = {}
    mtime = path.stat().st_mtime
    for raw_line in text.splitlines():
        line = raw_line.replace("\\_", "_").replace("\\-", "-")
        for match in _MEGA_URL_RE.finditer(line):
            url = match.group(0).rstrip(".,;)")
            try:
                parsed_link = parse_mega_link(url)
            except SyncError as exc:
                LOG.warning("Skipping malformed link in %s: %s", path, exc)
                continue
            version = parse_version(line)
            candidate = LinkCandidate(
                source_file=path,
                post_dir=post_dir,
                title=title,
                url=parsed_link.url,
                handle=parsed_link.handle,
                version=version,
                update_date=update_dates.get(version) if version is not None else None,
                source_date=source_date,
                label_score=label_score(line, path),
                source_mtime=mtime,
            )
            previous = by_url.get(parsed_link.url)
            if previous is None or candidate_sort_key(candidate) > candidate_sort_key(previous):
                by_url[parsed_link.url] = candidate
    return list(by_url.values())


def candidate_sort_key(candidate: LinkCandidate) -> tuple:
    return (
        candidate.version if candidate.version is not None else Decimal("-1"),
        candidate.update_date or date.min,
        candidate.label_score,
        candidate.source_mtime,
    )


def export_snapshot_sort_key(path: Path) -> tuple[int, float, int, str]:
    """Prefer links-* exports, then the newest snapshot and its (N) suffix.

    ``(1)``, ``(2)``, etc. are export snapshot revisions, not mod Update
    numbers. Modification time remains authoritative when a base file is
    refreshed in place; the suffix breaks ties when copied timestamps match.
    """
    revision_match = _EXPORT_REVISION_RE.search(path.name)
    revision = int(revision_match.group(1)) if revision_match else 0
    return (
        1 if path.name.lower().startswith("links-") else 0,
        path.stat().st_mtime,
        revision,
        path.name.casefold(),
    )


def discover_latest_candidates(source_dir: Path) -> list[LinkCandidate]:
    text_files = sorted(
        source_dir.rglob("*.txt"),
        key=lambda path: (
            0 if path.name.lower().startswith("links-") else 1,
            str(path).casefold(),
        ),
    )
    LOG.info("Scanning %d text export(s) under %s", len(text_files), source_dir)

    files_by_post: dict[str, list[Path]] = {}
    for path in text_files:
        files_by_post.setdefault(str(path.parent.resolve()).casefold(), []).append(path)

    latest_by_post: list[LinkCandidate] = []
    for post_files in files_by_post.values():
        # If the newest preferred snapshot contains no public file link, fall
        # back through earlier snapshots instead of dropping the post.
        for path in sorted(post_files, key=export_snapshot_sort_key, reverse=True):
            candidates = parse_text_export(path)
            if candidates:
                latest_by_post.append(max(candidates, key=candidate_sort_key))
                break
    return sorted(
        latest_by_post,
        key=lambda item: (item.effective_date or date.min, item.title.casefold()),
        reverse=True,
    )


def decrypt_attributes(encoded: str, aes_key: bytes) -> dict:
    encrypted = decode_b64url(encoded)
    if len(encrypted) % 16:
        raise SyncError("MEGA attribute ciphertext is not block-aligned")
    decryptor = Cipher(algorithms.AES(aes_key), modes.CBC(b"\0" * 16)).decryptor()
    plain = (decryptor.update(encrypted) + decryptor.finalize()).rstrip(b"\0")
    if not plain.startswith(b"MEGA"):
        raise SyncError("MEGA attribute decryption failed; the public key may be stale")
    try:
        attributes = json.loads(plain[4:].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SyncError("MEGA returned invalid encrypted attributes") from exc
    if not isinstance(attributes, dict):
        raise SyncError("MEGA attributes are not an object")
    return attributes


def safe_windows_filename(remote_name: str) -> str:
    name = _WINDOWS_BAD_CHARS_RE.sub("_", Path(remote_name).name).rstrip(" .")
    if not name or name in {".", ".."}:
        raise SyncError(f"unsafe or empty remote filename: {remote_name!r}")
    return name


def fetch_remote_file(
    session: requests.Session, link: MegaLink, retries: int = 3
) -> RemoteFile:
    endpoint = f"https://g.api.mega.co.nz/cs?id={int(time.time() * 1000)}"
    payload = [{"a": "g", "g": 1, "p": link.handle}]
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = session.post(endpoint, json=payload, timeout=(15, 60))
            response.raise_for_status()
            body = response.json()
            result = body[0] if isinstance(body, list) and body else body
            if isinstance(result, int) and result < 0:
                raise SyncError(f"MEGA API error {result} for file {link.handle}")
            if not isinstance(result, dict):
                raise SyncError(f"unexpected MEGA API response for file {link.handle}")
            attributes = decrypt_attributes(str(result.get("at", "")), link.aes_key)
            remote_name = safe_windows_filename(str(attributes.get("n", "")))
            size = int(result.get("s", -1))
            download_url = str(result.get("g", ""))
            parsed_download = urlparse(download_url)
            hostname = (parsed_download.hostname or "").lower()
            if parsed_download.scheme == "http":
                # MEGA currently returns an http:// CDN URL even though the
                # same endpoint supports HTTPS. Upgrade it before any bytes
                # (including Range-resume bytes) are requested.
                download_url = parsed_download._replace(scheme="https").geturl()
                parsed_download = urlparse(download_url)
            if (
                size < 0
                or parsed_download.scheme != "https"
                or not hostname.endswith(".userstorage.mega.co.nz")
            ):
                raise SyncError(f"MEGA response is missing size/download URL for {link.handle}")
            return RemoteFile(link=link, name=remote_name, size=size, download_url=download_url)
        except (requests.RequestException, ValueError, SyncError) as exc:
            last_error = exc
            if attempt < retries:
                delay = 2 ** (attempt - 1)
                LOG.warning("MEGA metadata attempt %d/%d failed: %s", attempt, retries, exc)
                time.sleep(delay)
    raise SyncError(f"could not read MEGA metadata after {retries} attempts: {last_error}")


def xor_block(left: bytes, right: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(left, right, strict=True))


def iter_mega_chunk_sizes(total_size: int) -> Iterable[int]:
    position = 0
    chunk_size = 0x20000
    while position + chunk_size < total_size:
        yield chunk_size
        position += chunk_size
        if chunk_size < 0x100000:
            chunk_size += 0x20000
    if position < total_size:
        yield total_size - position


def calculate_mega_mac(path: Path, link: MegaLink) -> tuple[int, int]:
    words = struct.unpack(">8I", link.raw_key)
    chunk_seed = struct.pack(">4I", words[4], words[5], words[4], words[5])
    file_mac = b"\0" * 16
    ecb = Cipher(algorithms.AES(link.aes_key), modes.ECB()).encryptor()

    with path.open("rb") as source:
        for chunk_size in iter_mega_chunk_sizes(path.stat().st_size):
            chunk = source.read(chunk_size)
            if len(chunk) != chunk_size:
                raise SyncError(f"file changed while verifying: {path}")
            if len(chunk) % 16:
                chunk += b"\0" * (-len(chunk) % 16)
            cbc = Cipher(algorithms.AES(link.aes_key), modes.CBC(chunk_seed)).encryptor()
            encrypted = cbc.update(chunk) + cbc.finalize()
            chunk_mac = encrypted[-16:]
            file_mac = ecb.update(xor_block(file_mac, chunk_mac))
    ecb.finalize()
    mac_words = struct.unpack(">4I", file_mac)
    return mac_words[0] ^ mac_words[1], mac_words[2] ^ mac_words[3]


def verify_local_file(path: Path, remote: RemoteFile, verify_mac: bool) -> tuple[bool, str]:
    try:
        actual_size = path.stat().st_size
    except OSError as exc:
        return False, f"cannot stat file: {exc}"
    if actual_size != remote.size:
        return False, f"size mismatch ({actual_size} != {remote.size})"
    if not verify_mac:
        return True, "matching name and size"
    try:
        actual_mac = calculate_mega_mac(path, remote.link)
    except (OSError, SyncError) as exc:
        return False, f"MAC check failed: {exc}"
    if actual_mac != remote.link.expected_mac:
        return False, "MEGA content MAC mismatch"
    return True, "matching name, size, and MEGA content MAC"


def build_file_index(target_dir: Path) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = {}
    for path in target_dir.rglob("*"):
        if path.is_file() and not path.name.endswith(".part"):
            index.setdefault(path.name.casefold(), []).append(path)
    return index


def download_remote_file(
    session: requests.Session, remote: RemoteFile, destination: Path
) -> None:
    part = destination.with_name(destination.name + ".part")
    offset = part.stat().st_size if part.exists() else 0
    if offset > remote.size:
        raise SyncError(
            f"partial file is larger than the remote file; inspect or remove it: {part}"
        )
    if offset % 16:
        aligned = offset - (offset % 16)
        LOG.warning("Truncating incomplete cipher block in partial file: %d -> %d", offset, aligned)
        with part.open("r+b") as output:
            output.truncate(aligned)
        offset = aligned

    if offset == remote.size:
        ok, reason = verify_local_file(part, remote, verify_mac=True)
        if not ok:
            raise SyncError(f"completed partial file is invalid ({reason}): {part}")
        os.replace(part, destination)
        return

    headers = {"Range": f"bytes={offset}-"} if offset else {}
    response = session.get(remote.download_url, headers=headers, stream=True, timeout=(20, 120))
    if offset and response.status_code != 206:
        response.close()
        raise SyncError(
            f"MEGA server did not accept resume at byte {offset}; inspect or remove {part}"
        )
    response.raise_for_status()

    counter = (int.from_bytes(remote.link.iv, "big") + offset // 16).to_bytes(16, "big")
    decryptor = Cipher(algorithms.AES(remote.link.aes_key), modes.CTR(counter)).decryptor()
    mode = "ab" if offset else "wb"
    written = offset
    started = time.monotonic()
    last_report = started
    try:
        with part.open(mode) as output:
            for encrypted in response.iter_content(chunk_size=4 * 1024 * 1024):
                if not encrypted:
                    continue
                plain = decryptor.update(encrypted)
                output.write(plain)
                written += len(plain)
                now = time.monotonic()
                if now - last_report >= 5:
                    percent = (written / remote.size * 100) if remote.size else 100.0
                    speed = (written - offset) / max(now - started, 0.001) / 1024 / 1024
                    LOG.info("  %.1f%% — %.1f MiB / %.1f MiB — %.1f MiB/s", percent,
                             written / 1024 / 1024, remote.size / 1024 / 1024, speed)
                    last_report = now
            final_plain = decryptor.finalize()
            if final_plain:
                output.write(final_plain)
                written += len(final_plain)
            output.flush()
            os.fsync(output.fileno())
    finally:
        response.close()

    if written != remote.size:
        raise SyncError(
            f"incomplete download ({written} of {remote.size} bytes); partial kept at {part}"
        )
    ok, reason = verify_local_file(part, remote, verify_mac=True)
    if not ok:
        raise SyncError(f"download failed integrity verification ({reason}); partial kept at {part}")
    os.replace(part, destination)


def make_parser(env: dict[str, str], env_path: Path) -> argparse.ArgumentParser:
    source_default = env_value(env, "FANBOX_SOURCE_DIR")
    target_default = env_value(env, "MEGA_TARGET_DIR")
    recent_default = env_value(env, "MEGA_SYNC_RECENT_DAYS").strip()
    if recent_default:
        try:
            recent_days: int | None = int(recent_default)
        except ValueError as exc:
            raise SyncError(
                f"MEGA_SYNC_RECENT_DAYS must be an integer, got {recent_default!r}"
            ) from exc
    else:
        recent_days = None

    parser = argparse.ArgumentParser(
        description="Sync the latest MEGA file found in every Fanbox post."
    )
    parser.add_argument("--env", default=str(env_path), help="dotenv file (default: script directory/.env)")
    parser.add_argument("--source", default=source_default, help="Fanbox export root")
    parser.add_argument("--target", default=target_default, help="directory containing downloaded mods")
    parser.add_argument(
        "--recent-days",
        type=int,
        default=recent_days,
        help="optional date filter; omitted by default so every post is checked",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="check every post even when MEGA_SYNC_RECENT_DAYS is set in the env file",
    )
    parser.add_argument("--dry-run", action="store_true", help="check and report without downloading")
    parser.add_argument(
        "--no-verify-existing",
        action="store_true",
        help="trust matching name and byte size instead of checking the MEGA content MAC",
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--log",
        default=env_value(env, "MEGA_SYNC_LOG_FILE", str(SCRIPT_DIR / "fanbox_mega_sync.log")),
    )
    return parser


def parse_args(argv: list[str] | None = None) -> tuple[argparse.Namespace, dict[str, str]]:
    argv = list(sys.argv[1:] if argv is None else argv)
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--env", default=str(DEFAULT_ENV_FILE))
    preliminary, _ = pre_parser.parse_known_args(argv)
    env_path = Path(preliminary.env).expanduser().resolve()
    env = load_env_file(env_path)
    parser = make_parser(env, env_path)
    args = parser.parse_args(argv)
    args.env = str(env_path)
    return args, env


def run(args: argparse.Namespace, env: dict[str, str]) -> int:
    if not args.source:
        raise SyncError("FANBOX_SOURCE_DIR is not set in .env and --source was not supplied")
    if not args.target:
        raise SyncError("MEGA_TARGET_DIR is not set in .env and --target was not supplied")
    if args.recent_days is not None and args.recent_days < 1:
        raise SyncError("--recent-days must be at least 1")

    source_dir = Path(args.source).expanduser()
    target_dir = Path(args.target).expanduser()
    if not source_dir.is_dir():
        raise SyncError(f"source directory does not exist: {source_dir}")
    if not target_dir.is_dir():
        if args.dry_run:
            raise SyncError(f"target directory does not exist: {target_dir}")
        target_dir.mkdir(parents=True, exist_ok=True)

    latest = discover_latest_candidates(source_dir)
    if args.all or args.recent_days is None:
        selected = latest
        cutoff = None
    else:
        cutoff = date.today() - timedelta(days=args.recent_days - 1)
        selected = [item for item in latest if item.effective_date and item.effective_date >= cutoff]

    LOG.info(
        "Selected the latest link from %d post(s)%s",
        len(selected),
        "" if cutoff is None else f" dated {cutoff.isoformat()} or later",
    )
    if not selected:
        LOG.info("Nothing to check.")
        return 0

    file_index = build_file_index(target_dir)
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
            )
        }
    )
    verify_existing = not args.no_verify_existing and env_bool(
        env, "MEGA_SYNC_VERIFY_EXISTING", True
    )

    present = 0
    downloaded = 0
    missing_dry_run = 0
    failures = 0
    for number, candidate in enumerate(selected, start=1):
        date_text = candidate.effective_date.isoformat() if candidate.effective_date else "unknown-date"
        LOG.info(
            "[%d/%d] %s — %s — %s",
            number,
            len(selected),
            candidate.title,
            version_label(candidate.version),
            date_text,
        )
        try:
            link = parse_mega_link(candidate.url)
            remote = fetch_remote_file(session, link)
            LOG.info("  Remote: %s (%.1f MiB)", remote.name, remote.size / 1024 / 1024)
            local_candidates = file_index.get(remote.name.casefold(), [])
            valid_path = None
            invalid_reasons: list[str] = []
            for local_path in local_candidates:
                ok, reason = verify_local_file(local_path, remote, verify_existing)
                if ok:
                    valid_path = local_path
                    LOG.info("  Present: %s (%s)", local_path, reason)
                    break
                invalid_reasons.append(f"{local_path}: {reason}")

            if valid_path:
                present += 1
                continue
            if invalid_reasons:
                raise SyncError(
                    "same-name local file exists but is invalid; refusing to overwrite:\n    "
                    + "\n    ".join(invalid_reasons)
                )

            destination = target_dir / remote.name
            if args.dry_run:
                missing_dry_run += 1
                LOG.warning("  Missing (dry run, not downloaded): %s", destination)
                continue

            LOG.info("  Downloading to %s", destination)
            download_remote_file(session, remote, destination)
            LOG.info("  Downloaded and verified: %s", destination)
            file_index.setdefault(remote.name.casefold(), []).append(destination)
            downloaded += 1
        except (OSError, requests.RequestException, SyncError) as exc:
            failures += 1
            LOG.error("  Failed: %s", exc)

    LOG.info(
        "Summary: %d present, %d downloaded, %d missing in dry-run, %d failed",
        present,
        downloaded,
        missing_dry_run,
        failures,
    )
    return 1 if failures or missing_dry_run else 0


def main(argv: list[str] | None = None) -> int:
    configure_utf8_console()
    try:
        args, env = parse_args(argv)
        setup_logging(Path(args.log).expanduser(), verbose=args.verbose)
        LOG.debug("Using env file: %s", args.env)
        return run(args, env)
    except (OSError, SyncError) as exc:
        if LOG.handlers:
            LOG.error("Fatal: %s", exc)
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
