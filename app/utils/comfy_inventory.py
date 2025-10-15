"""Shared helpers for ComfyUI inventory tracking."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, MutableMapping, Optional

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class InventoryItem:
    """Normalized description of a tracked filesystem object."""

    absolute_path: str
    relative_path: Optional[str]
    kind: str
    size: int
    modified: float

    def as_json_ready(self) -> Dict[str, object]:
        """Return a JSON serialisable payload for the inventory file."""

        payload = asdict(self)
        payload["modified"] = time.strftime(
            "%Y-%m-%dT%H:%M:%S%z", time.localtime(self.modified)
        )
        return payload


def normalise_path(path: Path) -> Path:
    """Return a resolved version of ``path`` without forcing existence."""

    try:
        return path.expanduser().resolve()
    except FileNotFoundError:
        return path.expanduser().absolute()


def relative_to_base(path: Path, base: Optional[Path]) -> Optional[str]:
    """Return ``path`` relative to ``base`` when possible."""

    if base is None:
        return None

    try:
        return str(path.relative_to(base))
    except ValueError:
        return None


def create_inventory_item(path: Path, base: Optional[Path]) -> Optional[InventoryItem]:
    """Build inventory metadata for ``path``."""

    path = normalise_path(path)

    if not path.exists():
        return None

    stats = path.stat()
    kind = "directory" if path.is_dir() else "file"

    return InventoryItem(
        absolute_path=str(path),
        relative_path=relative_to_base(path, base),
        kind=kind,
        size=0 if path.is_dir() else stats.st_size,
        modified=stats.st_mtime,
    )


def scan_inventory(
    roots: Iterable[Path],
    base: Optional[Path],
) -> Dict[str, Dict[str, object]]:
    """Build an inventory dictionary for the provided ``roots``."""

    inventory: Dict[str, Dict[str, object]] = {}

    for root in roots:
        root = normalise_path(root)
        if not root.exists():
            logger.warning("Skipping missing path: %s", root)
            continue

        for current in _iter_existing_paths(root):
            item = create_inventory_item(current, base)
            if item is None:
                continue
            inventory[item.absolute_path] = item.as_json_ready()

    return inventory


def _iter_existing_paths(root: Path) -> Iterator[Path]:
    """Yield ``root`` and all descendants."""

    yield root
    if root.is_dir():
        for child in root.rglob("*"):
            yield child


def dump_inventory(path: Path, inventory: MutableMapping[str, Dict[str, object]]) -> None:
    """Persist ``inventory`` as prettified JSON."""

    ordered_items = sorted(
        (item for item in inventory.values()),
        key=lambda item: (
            item.get("kind", ""),
            item.get("relative_path") or item.get("absolute_path"),
        ),
    )

    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text(json.dumps(ordered_items, indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)


def build_default_watchlist(
    comfy_root: Path,
    downloads: Iterable[Path],
    extras: Iterable[Path],
) -> list[Path]:
    """Return the set of directories that should be monitored."""

    watchlist: list[Path] = []
    comfy_root = normalise_path(comfy_root)

    candidates = [
        comfy_root,
        comfy_root / "models",
        comfy_root / "models" / "checkpoints",
        comfy_root / "models" / "vae",
        comfy_root / "models" / "loras",
        comfy_root / "custom_nodes",
        comfy_root / "input",
        comfy_root / "output",
    ]

    for candidate in candidates:
        if candidate.exists():
            watchlist.append(candidate)
        else:
            logger.debug("Optional path missing: %s", candidate)

    for dl in downloads:
        watchlist.append(normalise_path(dl))

    for extra in extras:
        watchlist.append(normalise_path(extra))

    return watchlist
