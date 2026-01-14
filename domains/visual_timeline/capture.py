#!/usr/bin/env python3
"""
Screenshot capture worker for Visual Timeline.

Captures screenshots at configured intervals and stores them with metadata.
Handles X11/Wayland display access and window detection.
"""

import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import mss
from loguru import logger
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.utils.config import get_settings
from app.utils.helpers import generate_uuid, now_iso
from app.utils.neo4j_client import get_neo4j_client


class ScreenshotCapture:
    """Screenshot capture manager."""

    def __init__(self):
        """Initialize screenshot capture."""
        self.settings = get_settings()
        self.client = get_neo4j_client()
        self.screenshot_dir = self.settings.screenshot_dir
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Screenshot directory: {self.screenshot_dir}")
        logger.info(f"Capture interval: {self.settings.screenshot_interval}s")

    def get_active_window_info(self) -> tuple[str | None, str | None]:
        """
        Get active window information using xdotool.

        Returns:
            Tuple of (app_name, window_title)
        """
        try:
            # Get active window ID
            result = subprocess.run(
                ["xdotool", "getactivewindow"], capture_output=True, text=True, timeout=2
            )

            if result.returncode != 0:
                logger.warning("xdotool failed, likely no X11 display")
                return None, None

            window_id = result.stdout.strip()

            # Get window name/title
            result = subprocess.run(
                ["xdotool", "getwindowname", window_id], capture_output=True, text=True, timeout=2
            )
            window_title = result.stdout.strip() if result.returncode == 0 else None

            # Get window class (app name)
            result = subprocess.run(
                ["xprop", "-id", window_id, "WM_CLASS"], capture_output=True, text=True, timeout=2
            )

            app_name = None
            if result.returncode == 0:
                # Parse WM_CLASS output: WM_CLASS(STRING) = "app", "App"
                output = result.stdout.strip()
                if '"' in output:
                    parts = output.split('"')
                    if len(parts) >= 2:
                        app_name = parts[1]

            return app_name, window_title

        except Exception as e:
            logger.warning(f"Failed to get window info: {e}")
            return None, None

    def should_capture(self, app_name: str | None) -> bool:
        """
        Check if screenshot should be captured based on privacy rules.

        Args:
            app_name: Active application name

        Returns:
            True if should capture, False otherwise
        """
        if not app_name:
            return True

        exclude_apps = self.settings.get_exclude_apps()

        for excluded in exclude_apps:
            if excluded.lower() in app_name.lower():
                logger.info(f"Skipping capture for excluded app: {app_name}")
                return False

        return True

    def capture_screenshot(self) -> str | None:
        """
        Capture screenshot and save to disk.

        Returns:
            Path to saved screenshot or None if failed
        """
        try:
            # Use mss for cross-platform screenshot
            with mss.mss() as sct:
                # Capture primary monitor
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)

                # Convert to PIL Image
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

                # Generate filename
                timestamp = datetime.now(UTC)
                filename = (
                    f"screenshot_{timestamp.strftime('%Y%m%d_%H%M%S')}_{generate_uuid()[:8]}.png"
                )
                filepath = self.screenshot_dir / filename

                # Save screenshot
                img.save(filepath, "PNG", optimize=True)
                logger.success(f"Screenshot saved: {filepath}")

                return str(filepath)

        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None

    def create_snapshot_node(
        self, filepath: str, app_name: str | None, window_title: str | None
    ) -> str:
        """
        Create Snapshot node in Neo4j.

        Args:
            filepath: Path to screenshot file
            app_name: Active application name
            window_title: Active window title

        Returns:
            Snapshot ID
        """
        snapshot_id = generate_uuid()
        timestamp = now_iso()

        query = """
        CREATE (s:Snapshot {
            id: $id,
            ts: datetime($ts),
            app: $app,
            window: $window,
            path: $path
        })
        RETURN s.id AS id
        """

        try:
            result = self.client.execute_read(
                query,
                {
                    "id": snapshot_id,
                    "ts": timestamp,
                    "app": app_name,
                    "window": window_title,
                    "path": filepath,
                },
            )

            logger.success(f"Created Snapshot node: {snapshot_id}")
            return snapshot_id

        except Exception as e:
            logger.error(f"Failed to create Snapshot node: {e}")
            raise

    def link_snapshot_to_app(self, snapshot_id: str, app_name: str):
        """
        Link snapshot to Software node if app exists.

        Args:
            snapshot_id: Snapshot node ID
            app_name: Application name
        """
        if not app_name:
            return

        query = """
        MATCH (s:Snapshot {id: $snapshot_id})
        MERGE (sw:Software {key: $app_key})
        ON CREATE SET sw.name = $app_name
        MERGE (s)-[:SEEN_APP]->(sw)
        """

        try:
            self.client.execute_write(
                query,
                {
                    "snapshot_id": snapshot_id,
                    "app_key": app_name.lower().replace(" ", "_"),
                    "app_name": app_name,
                },
            )
            logger.debug(f"Linked snapshot to app: {app_name}")

        except Exception as e:
            logger.warning(f"Failed to link snapshot to app: {e}")

    def capture_and_store(self):
        """Main capture workflow: capture screenshot and store metadata."""
        logger.info("Starting screenshot capture...")

        # Get active window info
        app_name, window_title = self.get_active_window_info()
        logger.info(f"Active window: {app_name} - {window_title}")

        # Check privacy rules
        if not self.should_capture(app_name):
            return

        # Capture screenshot
        filepath = self.capture_screenshot()
        if not filepath:
            logger.error("Screenshot capture failed")
            return

        # Create Snapshot node
        snapshot_id = self.create_snapshot_node(filepath, app_name, window_title)

        # Link to app if available
        if app_name:
            self.link_snapshot_to_app(snapshot_id, app_name)

        logger.success(f"Snapshot captured and stored: {snapshot_id}")

    def run(self):
        """Run continuous screenshot capture loop."""
        logger.info("Screenshot capture worker started")

        while True:
            try:
                self.capture_and_store()
            except Exception as e:
                logger.error(f"Capture error: {e}")

            # Sleep until next capture
            time.sleep(self.settings.screenshot_interval)


def main():
    """Main entry point."""
    logger.info("Visual Timeline - Screenshot Capture Worker")

    # Check for X11 display
    if not os.environ.get("DISPLAY"):
        logger.warning("DISPLAY environment variable not set")
        logger.warning("Screenshot capture requires X11 display access")

    try:
        capture = ScreenshotCapture()
        capture.run()
    except KeyboardInterrupt:
        logger.info("Screenshot capture worker stopped by user")
    except Exception as e:
        logger.error(f"Screenshot capture worker failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
