"""Local file cache for INTERLIS model repositories."""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional, Union
from urllib.parse import ParseResult, urljoin, urlparse
from urllib.request import urlopen

logger = logging.getLogger(__name__)


_INVALID_CHARS = set('<>:"\\|?*%&')
_INVALID_CHARS_WITH_SLASH = _INVALID_CHARS | {"/"}


class RepositoryCache:
    """A cache that mirrors remote repository files onto the local file system."""

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        hashed_filenames: Optional[bool] = None,
    ) -> None:
        env_dir = os.getenv("ILI_CACHE")
        if base_dir is None:
            if env_dir:
                base_dir = Path(env_dir)
            else:
                base_dir = Path.home() / ".ilicache"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        env_hash = os.getenv("ILI_CACHE_FILENAME")
        if hashed_filenames is None:
            hashed_filenames = env_hash and env_hash.upper() == "MD5"
        self.hashed_filenames = bool(hashed_filenames)

    def fetch(
        self,
        uri: Optional[str],
        relative_path: Optional[str],
        ttl_seconds: Optional[float],
        md5: Optional[str] = None,
    ) -> Optional[Path]:
        """Return the local path to ``relative_path`` inside ``uri``.

        ``uri`` may be an HTTP(S) URL or a local directory. ``relative_path`` may
        be ``None`` if the URI already points to a file.
        """

        if uri is None:
            if relative_path is None:
                return None
            return Path(relative_path)

        parsed = urlparse(uri)
        if parsed.scheme in {"http", "https"}:
            return self._fetch_http(parsed, relative_path, ttl_seconds, md5)

        # Treat anything else as a local path.
        base = Path(uri)
        if relative_path:
            base = base / relative_path
        if not base.exists():
            return None
        return base

    # ------------------------------------------------------------------
    # HTTP helpers

    def _fetch_http(
        self,
        parsed_uri,
        relative_path: Optional[str],
        ttl_seconds: Optional[float],
        md5: Optional[str],
    ) -> Optional[Path]:
        base_string = self._cache_key(parsed_uri)
        target_folder = self.base_dir / base_string
        target_path = target_folder
        if relative_path:
            safe_relative = self._sanitize_relative(relative_path)
            target_path = target_folder / safe_relative
        should_fetch = True
        if target_path.exists():
            should_fetch = False
            if ttl_seconds is None:
                pass
            elif ttl_seconds == 0:
                should_fetch = True
            else:
                if target_path.stat().st_mtime + ttl_seconds < time.time():
                    should_fetch = True
            if not should_fetch and md5:
                digest = self._calc_md5(target_path)
                if digest != md5.lower():
                    should_fetch = True
        if should_fetch:
            url = parsed_uri.geturl()
            if relative_path:
                if not url.endswith("/"):
                    url += "/"
                url = urljoin(url, "/".join(self._sanitize_relative(relative_path).parts))
            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with urlopen(url, timeout=40) as response:
                    if getattr(response, "status", 200) >= 400:
                        if target_path.exists():
                            logger.warning("Using cached copy for %%s because the server returned %%s", url, response.status)
                            return target_path
                        return None
                    with tempfile.NamedTemporaryFile(delete=False, dir=target_path.parent) as tmp:
                        shutil.copyfileobj(response, tmp)
                    os.replace(tmp.name, target_path)
            except FileNotFoundError:
                return None
            except Exception as exc:  # pragma: no cover - defensive logging
                if target_path.exists():
                    logger.warning("Using cached copy for %%s because fetching failed: %%s", url, exc)
                    return target_path
                raise
        return target_path

    # ------------------------------------------------------------------
    # Utility helpers

    def _cache_key(self, value: Union[str, ParseResult]) -> Union[str, Path]:
        if isinstance(value, ParseResult):
            parsed = value
        else:
            parsed = urlparse(value)

        url_for_hash = parsed.geturl()
        if self.hashed_filenames:
            return hashlib.md5(url_for_hash.encode("utf-8")).hexdigest()

        parts = []
        if parsed.netloc:
            parts.append(self._escape(parsed.netloc, include_path=False))

        for part in parsed.path.split("/"):
            if part in {"", ".", ".."}:
                continue
            parts.append(self._escape(part, include_path=True))

        if not parts:
            return Path(self._escape(url_for_hash, include_path=False))

        return Path(*parts)

    def _sanitize_relative(self, relative_path: str) -> Path:
        parts = []
        for part in Path(relative_path).parts:
            if part in ("", "."):
                continue
            if part == "..":
                continue
            parts.append(part)
        if not parts:
            return Path(".")
        if self.hashed_filenames:
            return Path(*parts)
        escaped_parts = [self._escape(part, include_path=True) for part in parts]
        return Path(*escaped_parts)

    @staticmethod
    def _escape(value: str, include_path: bool) -> str:
        invalid = _INVALID_CHARS_WITH_SLASH if include_path else _INVALID_CHARS
        builder = []
        for ch in value:
            if ch in invalid:
                builder.append("&%04x" % ord(ch))
            else:
                builder.append(ch)
        return "".join(builder)

    @staticmethod
    def _calc_md5(path: Path) -> str:
        digest = hashlib.md5()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
