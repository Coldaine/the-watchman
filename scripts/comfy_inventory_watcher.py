#!/usr/bin/env python3
"""Utilities for tracking ComfyUI assets in real time.

This module exposes a CLI entrypoint that keeps an inventory of files inside a
ComfyUI installation and any related download folders.  It is designed to be
run from the directory immediately above ``ComfyUI`` (as requested in
``tasks/Task1.md``) but accepts explicit paths for flexibility.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
from pathlib import Path
from typing import Dict, MutableMapping, Optional

from watchdog.events import DirModifiedEvent, FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from app.utils.comfy_inventory import (
    build_default_watchlist,
    create_inventory_item,
    dump_inventory,
    normalise_path,
    scan_inventory,
)

logger = logging.getLogger("comfy_inventory")


class InventoryEventHandler(FileSystemEventHandler):
    """Watchdog handler that keeps the on-disk inventory in sync."""

    def __init__(
        self,
        inventory: MutableMapping[str, Dict[str, object]],
        lock: threading.Lock,
        base: Optional[Path],
        output_file: Path,
        log_events: bool,
    ) -> None:
        super().__init__()
        self.inventory = inventory
        self.lock = lock
        self.base = base
        self.output_file = output_file
        self.log_events = log_events

    # ``FileSystemEventHandler`` dispatches to both file and directory specific
    # methods.  We treat them uniformly by delegating to helper routines.

    def on_created(self, event: FileSystemEvent) -> None:  # noqa: D401
        """Update the inventory when a file or directory is created."""

        self._handle_creation(event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:  # noqa: D401
        """Update metadata when a file or directory is modified."""

        if isinstance(event, (DirModifiedEvent,)):
            # Directory modifications are extremely noisy and rarely provide
            # useful timestamp updates for ComfyUI assets.
            return
        self._handle_creation(event.src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:  # noqa: D401
        """Remove entries when a path disappears."""

        self._handle_deletion(event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:  # noqa: D401
        """Handle rename/move events."""

        src = getattr(event, "src_path", None)
        dest = getattr(event, "dest_path", None)

        if src:
            self._handle_deletion(src)
        if dest:
            self._handle_creation(dest)

    # Helper routines -----------------------------------------------------------------

    def _handle_creation(self, raw_path: str) -> None:
        path = Path(raw_path)
        item = create_inventory_item(path, self.base)
        if item is None:
            return

        if self.log_events:
            logger.info("Inventory update: %s", item.absolute_path)

        with self.lock:
            self.inventory[item.absolute_path] = item.as_json_ready()
            dump_inventory(self.output_file, self.inventory)

    def _handle_deletion(self, raw_path: str) -> None:
        absolute = str(normalise_path(Path(raw_path)))
        with self.lock:
            removed = self.inventory.pop(absolute, None)
            if removed is None:
                return

            if self.log_events:
                logger.info("Inventory removal: %s", absolute)

            dump_inventory(self.output_file, self.inventory)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(
        description="Monitor ComfyUI assets and maintain an inventory JSON file.",
    )
    parser.add_argument(
        "--comfy-root",
        type=Path,
        default=Path("ComfyUI"),
        help="Path to the ComfyUI installation (default: ./ComfyUI).",
    )
    parser.add_argument(
        "--downloads",
        type=Path,
        action="append",
        default=[],
        help="Additional download directories to track (can be repeated).",
    )
    parser.add_argument(
        "--extra",
        type=Path,
        action="append",
        default=[],
        help="Any extra directories to include in the watchlist.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("comfy_inventory.json"),
        help="Where to write the inventory file.",
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=1.0,
        help="Polling interval for watchdog when in polling mode (seconds).",
    )
    parser.add_argument(
        "--log-events",
        action="store_true",
        help="Emit info logs whenever the inventory changes.",
    )
    parser.add_argument(
        "--base",
        type=Path,
        default=None,
        help=(
            "Optional base directory used to compute relative paths. "
            "Defaults to the parent of --comfy-root if available."
        ),
    )

    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """Entry point for the CLI script."""

    args = parse_args(argv)

    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
        )

    comfy_root = normalise_path(args.comfy_root)
    base = normalise_path(args.base) if args.base else comfy_root.parent

    watchlist = build_default_watchlist(
        comfy_root=comfy_root,
        downloads=args.downloads,
        extras=args.extra,
    )

    if not watchlist:
        logger.error("No valid directories to monitor.")
        return 1

    inventory = scan_inventory(watchlist, base)
    output_file = normalise_path(args.output)

    lock = threading.Lock()
    dump_inventory(output_file, inventory)

    handler = InventoryEventHandler(
        inventory=inventory,
        lock=lock,
        base=base,
        output_file=output_file,
        log_events=args.log_events,
    )

    observers: list[Observer] = []
    for path in watchlist:
        observer = Observer()
        observer.schedule(handler, str(path), recursive=True)
        observer.daemon = True
        observer.start()
        observers.append(observer)
        logger.info("Watching %s", path)

    stop_event = threading.Event()

    def _signal_handler(signum, frame):  # noqa: D401
        logger.info("Received signal %s, shutting down.", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    try:
        while not stop_event.is_set():
            stop_event.wait(args.poll)
    finally:
        for observer in observers:
            observer.stop()
        for observer in observers:
            observer.join()

    logger.info("Inventory watcher stopped.")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI bridge
    sys.exit(main())
