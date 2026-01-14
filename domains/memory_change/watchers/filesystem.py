#!/usr/bin/env python3
"""
File system watcher for Memory & Change domain.

Monitors configured directories for file system changes and creates Event nodes.
Uses watchdog library for cross-platform file system event monitoring.
"""

import sys
import time
from pathlib import Path

from loguru import logger
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.utils.config import get_settings
from app.utils.helpers import generate_uuid, now_iso, should_exclude_path
from app.utils.neo4j_client import get_neo4j_client


class WatchmanEventHandler(FileSystemEventHandler):
    """Custom event handler for file system changes."""

    def __init__(self, neo4j_client):
        """
        Initialize event handler.

        Args:
            neo4j_client: Neo4j client instance
        """
        super().__init__()
        self.neo4j = neo4j_client
        self.excluded_extensions = {".pyc", ".swp", ".tmp", "__pycache__"}

    def should_process(self, path: str) -> bool:
        """
        Check if path should be processed.

        Args:
            path: File path

        Returns:
            True if should process, False otherwise
        """
        path_obj = Path(path)

        # Skip excluded paths
        if should_exclude_path(path_obj):
            return False

        # Skip excluded extensions
        if path_obj.suffix in self.excluded_extensions:
            return False

        return True

    def create_event_node(self, event_type: str, path: str, is_directory: bool):
        """
        Create Event node in Neo4j.

        Args:
            event_type: Type of event (CREATE, MODIFY, DELETE, MOVE)
            path: File/directory path
            is_directory: Whether path is a directory
        """
        event_id = generate_uuid()
        timestamp = now_iso()

        query = """
        CREATE (e:Event {
            id: $id,
            ts: datetime($ts),
            type: $type,
            path: $path,
            is_directory: $is_directory
        })
        RETURN e.id AS id
        """

        try:
            self.neo4j.execute_write(
                query,
                {
                    "id": event_id,
                    "ts": timestamp,
                    "type": event_type,
                    "path": path,
                    "is_directory": is_directory,
                },
            )

            logger.debug(f"Event created: {event_type} {path}")

        except Exception as e:
            logger.warning(f"Failed to create Event node: {e}")

    def link_event_to_file(self, event_id: str, path: str):
        """
        Link Event to File/Directory node if it exists.

        Args:
            event_id: Event node ID
            path: File/directory path
        """
        query = """
        MATCH (e:Event {path: $path})
        WHERE e.id = $event_id
        OPTIONAL MATCH (f:File {path: $path})
        OPTIONAL MATCH (d:Directory {path: $path})
        WITH e, f, d
        WHERE f IS NOT NULL OR d IS NOT NULL
        FOREACH (_ IN CASE WHEN f IS NOT NULL THEN [1] ELSE [] END |
            MERGE (e)-[:ACTED_ON]->(f)
        )
        FOREACH (_ IN CASE WHEN d IS NOT NULL THEN [1] ELSE [] END |
            MERGE (e)-[:ACTED_ON]->(d)
        )
        """

        try:
            self.neo4j.execute_write(query, {"event_id": event_id, "path": path})

        except Exception as e:
            logger.debug(f"Could not link event to file/directory: {e}")

    def on_created(self, event: FileSystemEvent):
        """Handle file/directory creation."""
        if not self.should_process(event.src_path):
            return

        logger.info(f"Created: {event.src_path}")
        self.create_event_node("CREATE", event.src_path, event.is_directory)

    def on_modified(self, event: FileSystemEvent):
        """Handle file/directory modification."""
        if not self.should_process(event.src_path):
            return

        # Skip directory modifications (too noisy)
        if event.is_directory:
            return

        logger.info(f"Modified: {event.src_path}")
        self.create_event_node("MODIFY", event.src_path, event.is_directory)

    def on_deleted(self, event: FileSystemEvent):
        """Handle file/directory deletion."""
        if not self.should_process(event.src_path):
            return

        logger.info(f"Deleted: {event.src_path}")
        self.create_event_node("DELETE", event.src_path, event.is_directory)

    def on_moved(self, event: FileSystemEvent):
        """Handle file/directory move/rename."""
        if not self.should_process(event.src_path):
            return

        logger.info(f"Moved: {event.src_path} -> {event.dest_path}")

        # Create MOVE event with both paths
        event_id = generate_uuid()
        timestamp = now_iso()

        query = """
        CREATE (e:Event {
            id: $id,
            ts: datetime($ts),
            type: 'MOVE',
            path: $src_path,
            dest_path: $dest_path,
            is_directory: $is_directory
        })
        RETURN e.id AS id
        """

        try:
            self.neo4j.execute_write(
                query,
                {
                    "id": event_id,
                    "ts": timestamp,
                    "src_path": event.src_path,
                    "dest_path": event.dest_path,
                    "is_directory": event.is_directory,
                },
            )

        except Exception as e:
            logger.warning(f"Failed to create MOVE event: {e}")


class FileSystemWatcher:
    """File system monitoring orchestrator."""

    def __init__(self):
        """Initialize file system watcher."""
        self.settings = get_settings()
        self.neo4j = get_neo4j_client()

        # Directories to watch
        self.watch_dirs = self._get_watch_directories()

        # Create event handler
        self.event_handler = WatchmanEventHandler(self.neo4j)

        # Create observer
        self.observer = Observer()

        logger.info("File system watcher initialized")
        logger.info(f"Watching directories: {self.watch_dirs}")

    def _get_watch_directories(self) -> set[Path]:
        """
        Get set of directories to watch.

        Returns:
            Set of directory paths
        """
        watch_dirs = set()

        # Watch /etc (if exists and readable)
        etc = Path("/etc")
        if etc.exists() and etc.is_dir():
            watch_dirs.add(etc)

        # Watch project roots
        for root in self.settings.get_project_roots():
            if root.exists() and root.is_dir():
                watch_dirs.add(root)

        # Watch config roots
        for root in self.settings.get_config_roots():
            root_path = Path(root).expanduser()
            if root_path.exists() and root_path.is_dir():
                watch_dirs.add(root_path)

        return watch_dirs

    def start_watching(self):
        """Start watching all configured directories."""
        for watch_dir in self.watch_dirs:
            try:
                self.observer.schedule(self.event_handler, str(watch_dir), recursive=True)
                logger.success(f"Started watching: {watch_dir}")

            except Exception as e:
                logger.error(f"Failed to watch {watch_dir}: {e}")

        # Start observer
        self.observer.start()
        logger.success("File system observer started")

    def stop_watching(self):
        """Stop watching."""
        self.observer.stop()
        self.observer.join()
        logger.info("File system observer stopped")

    def run(self):
        """Run file system watcher continuously."""
        logger.info("Starting file system watcher...")

        try:
            self.start_watching()

            # Keep running
            while True:
                time.sleep(60)

        except KeyboardInterrupt:
            logger.info("Stopping file system watcher...")
            self.stop_watching()


def main():
    """Main entry point."""
    logger.info("Memory & Change - File System Watcher")

    try:
        watcher = FileSystemWatcher()
        watcher.run()

    except KeyboardInterrupt:
        logger.info("File system watcher stopped by user")
    except Exception as e:
        logger.error(f"File system watcher failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
