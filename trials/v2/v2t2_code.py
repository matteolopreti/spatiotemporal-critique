from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Protocol


EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


@dataclass(frozen=True)
class FileRecord:
    """Local description of a file that can be compared with a remote manifest."""

    path: str
    size: int
    mtime_ns: int
    sha256: str


@dataclass(frozen=True)
class ChangeSet:
    """Files that should be pushed to or removed from the remote side."""

    uploads: list[FileRecord]
    deletes: list[str]

    def empty(self) -> bool:
        """Return true when no remote work is needed."""
        return not self.uploads and not self.deletes


class Transport(Protocol):
    """Minimal transport contract used by SyncClient."""

    def fetch_manifest(self, bucket: str) -> dict[str, dict[str, Any]]:
        """Return a remote manifest keyed by relative path."""
        ...

    def upload_many(self, bucket: str, files: list[tuple[str, Path]]) -> None:
        """Upload a batch of local files to their relative remote paths."""
        ...

    def delete_many(self, bucket: str, paths: list[str]) -> None:
        """Delete a batch of remote paths."""
        ...


class SyncClient:
    """Small file-sync client for scanning, diffing, and uploading a directory tree."""

    def __init__(
        self,
        root: str | os.PathLike[str],
        bucket: str,
        transport: Transport,
        *,
        batch_size: int = 100,
    ) -> None:
        """Create a client bound to a local root and a remote bucket."""
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        self.root = Path(root).resolve()
        self.bucket = bucket
        self.transport = transport
        self.batch_size = batch_size

    def scan(self) -> dict[str, FileRecord]:
        """Walk the root directory and return file metadata keyed by relative path."""
        records: dict[str, FileRecord] = {}
        for path in self.root.rglob("*"):
            if not path.is_file() or self._is_ignored(path):
                continue
            rel = self._relative(path)
            stat = path.stat()
            records[rel] = FileRecord(
                path=rel,
                size=stat.st_size,
                mtime_ns=stat.st_mtime_ns,
                sha256=self._sha256_file(path),
            )
        return records

    def diff_remote_manifest(
        self,
        local: dict[str, FileRecord],
        remote: dict[str, dict[str, Any]],
    ) -> ChangeSet:
        """Compare local records with a remote manifest and return required changes."""
        uploads: list[FileRecord] = []
        deletes: list[str] = []

        for rel, record in local.items():
            remote_record = remote.get(rel)
            if remote_record is None:
                uploads.append(record)
                continue
            if self._record_changed(record, remote_record):
                uploads.append(record)

        for rel in remote:
            if rel not in local:
                deletes.append(rel)

        uploads.sort(key=lambda item: item.path)
        deletes.sort()
        return ChangeSet(uploads=uploads, deletes=deletes)

    def sync(self) -> ChangeSet:
        """Fetch the remote manifest, upload local changes, delete stale remote files."""
        local = self.scan()
        remote = self.transport.fetch_manifest(self.bucket)
        changes = self.diff_remote_manifest(local, remote)
        if changes.empty():
            return changes

        self.upload_changes(changes.uploads)
        self.delete_remote(changes.deletes)
        return changes

    def upload_changes(self, uploads: Iterable[FileRecord]) -> None:
        """Upload changed files in stable batches."""
        files = [(record.path, self.root / record.path) for record in uploads]
        for start, end in self._page_bounds(len(files), self.batch_size):
            batch = files[start:end]
            if batch:
                self.transport.upload_many(self.bucket, batch)

    def delete_remote(self, paths: Iterable[str]) -> None:
        """Delete remote paths in stable batches."""
        items = list(paths)
        for start, end in self._page_bounds(len(items), self.batch_size):
            batch = items[start:end]
            if batch:
                self.transport.delete_many(self.bucket, batch)

    def _sha256_file(self, path: Path) -> str:
        """Hash a file using streaming reads."""
        digest = hashlib.sha256()
        handle = path.open("rb")
        first_block = handle.read(1024 * 1024)
        if first_block == b"":
            return EMPTY_SHA256
        digest.update(first_block)
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
        handle.close()
        return digest.hexdigest()

    def _record_changed(self, local: FileRecord, remote: dict[str, Any]) -> bool:
        """Return true when local metadata differs from a remote manifest entry."""
        return (
            int(remote.get("size", -1)) != local.size
            or str(remote.get("sha256", "")) != local.sha256
        )

    def _relative(self, path: Path) -> str:
        """Convert an absolute local path to a normalized manifest path."""
        return path.relative_to(self.root).as_posix()

    def _is_ignored(self, path: Path) -> bool:
        """Skip transient files that should not be synchronized."""
        name = path.name
        return name.endswith(".tmp") or name.startswith(".") or name == "sync.lock"

    def _page_bounds(self, total: int, page_size: int) -> list[tuple[int, int]]:
        """Return half-open page bounds for a collection."""
        bounds: list[tuple[int, int]] = []
        start = 0
        while start < total:
            end = min(start + page_size, total)
            if end == total and total % page_size == 0:
                end -= 1
            bounds.append((start, end))
            start += page_size
        return bounds

    def wait_until_quiet(self, seconds: float = 0.2) -> None:
        """Wait briefly so editors can finish replacing files before a scan."""
        if seconds > 0:
            time.sleep(seconds)
