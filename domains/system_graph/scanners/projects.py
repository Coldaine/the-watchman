"""
Project scanner for System Graph domain.

Scans configured directories to discover code projects and their structure.
Creates Project, Directory, and File nodes with appropriate relationships.
"""

import sys
from datetime import datetime
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.utils.config import get_settings
from app.utils.helpers import (
    detect_project_type,
    generate_uuid,
    is_hidden,
    now_iso,
    should_exclude_path,
)
from app.utils.neo4j_client import get_neo4j_client


class ProjectScanner:
    """Scanner for discovering code projects."""

    def __init__(self):
        """Initialize project scanner."""
        self.settings = get_settings()
        self.neo4j = get_neo4j_client()
        self.project_roots = self.settings.get_project_roots()

        # Important project files to track
        self.key_files = {
            "package.json",
            "Cargo.toml",
            "go.mod",
            "requirements.txt",
            "pyproject.toml",
            "pom.xml",
            "build.gradle",
            "Gemfile",
            "composer.json",
            "docker-compose.yml",
            "docker-compose.yaml",
            "Dockerfile",
            ".env",
            "README.md",
            "Makefile",
        }

        logger.info(f"Project scanner initialized with roots: {self.project_roots}")

    def is_project_root(self, directory: Path) -> bool:
        """
        Check if directory is a project root.

        A directory is considered a project root if it contains
        project marker files like package.json, Cargo.toml, etc.

        Args:
            directory: Directory to check

        Returns:
            True if project root, False otherwise
        """
        if not directory.is_dir():
            return False

        # Check for project marker files
        for file in directory.iterdir():
            if file.is_file() and file.name in self.key_files:
                return True

        # Check for .git directory
        if (directory / ".git").exists():
            return True

        return False

    def scan_for_projects(self, root: Path, max_depth: int = 3) -> list[Path]:
        """
        Recursively scan directory for projects.

        Args:
            root: Root directory to scan
            max_depth: Maximum recursion depth

        Returns:
            List of project directories
        """
        projects = []

        def _scan_recursive(current: Path, depth: int):
            """Recursive scanner helper."""
            if depth > max_depth:
                return

            if not current.exists() or not current.is_dir():
                return

            # Skip hidden and excluded paths
            if is_hidden(current) or should_exclude_path(current):
                return

            # Check if current directory is a project
            if self.is_project_root(current):
                projects.append(current)
                logger.info(f"Found project: {current}")
                return  # Don't recurse into project subdirectories

            # Recurse into subdirectories
            try:
                for item in current.iterdir():
                    if item.is_dir():
                        _scan_recursive(item, depth + 1)
            except PermissionError:
                logger.warning(f"Permission denied: {current}")

        logger.info(f"Scanning {root} for projects...")
        _scan_recursive(root, 0)
        logger.success(f"Found {len(projects)} projects in {root}")

        return projects

    def create_project_node(self, project_path: Path) -> str:
        """
        Create Project node in Neo4j.

        Args:
            project_path: Path to project directory

        Returns:
            Project ID
        """
        project_id = generate_uuid()
        project_name = project_path.name
        project_type = detect_project_type(project_path)
        path_str = str(project_path.absolute())
        timestamp = now_iso()

        query = """
        MERGE (p:Project {path: $path})
        ON CREATE SET
            p.id = $id,
            p.name = $name,
            p.type = $type,
            p.created_at = datetime($timestamp),
            p.last_scan = datetime($timestamp)
        ON MATCH SET
            p.last_scan = datetime($timestamp),
            p.type = COALESCE($type, p.type)
        RETURN p.id AS id
        """

        try:
            result = self.neo4j.execute_read(
                query,
                {
                    "id": project_id,
                    "path": path_str,
                    "name": project_name,
                    "type": project_type,
                    "timestamp": timestamp,
                },
            )

            if result:
                returned_id = result[0].get("id", project_id)
                logger.success(f"Created/updated Project: {project_name}")
                return returned_id
            else:
                return project_id

        except Exception as e:
            logger.error(f"Failed to create Project node: {e}")
            raise

    def create_directory_node(self, dir_path: Path) -> bool:
        """
        Create Directory node in Neo4j.

        Args:
            dir_path: Path to directory

        Returns:
            True if successful
        """
        path_str = str(dir_path.absolute())
        name = dir_path.name

        query = """
        MERGE (d:Directory {path: $path})
        ON CREATE SET d.name = $name
        RETURN d.path AS path
        """

        try:
            self.neo4j.execute_write(query, {"path": path_str, "name": name})
            return True

        except Exception as e:
            logger.warning(f"Failed to create Directory node for {dir_path}: {e}")
            return False

    def create_file_node(self, file_path: Path) -> bool:
        """
        Create File node in Neo4j.

        Args:
            file_path: Path to file

        Returns:
            True if successful
        """
        path_str = str(file_path.absolute())
        name = file_path.name

        try:
            stat = file_path.stat()
            size = stat.st_size
            modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
        except Exception as e:
            logger.warning(f"Failed to stat file {file_path}: {e}")
            size = None
            modified = None

        query = """
        MERGE (f:File {path: $path})
        ON CREATE SET
            f.name = $name,
            f.size = $size,
            f.last_modified = datetime($modified)
        ON MATCH SET
            f.size = $size,
            f.last_modified = datetime($modified)
        RETURN f.path AS path
        """

        try:
            self.neo4j.execute_write(
                query, {"path": path_str, "name": name, "size": size, "modified": modified}
            )
            return True

        except Exception as e:
            logger.warning(f"Failed to create File node for {file_path}: {e}")
            return False

    def link_project_to_directory(self, project_path: Path):
        """
        Link Project to its Directory.

        Args:
            project_path: Project directory path
        """
        path_str = str(project_path.absolute())

        query = """
        MATCH (p:Project {path: $project_path})
        MERGE (d:Directory {path: $project_path})
        MERGE (p)-[:LOCATED_IN]->(d)
        """

        try:
            self.neo4j.execute_write(query, {"project_path": path_str})
        except Exception as e:
            logger.warning(f"Failed to link project to directory: {e}")

    def index_project_files(self, project_path: Path):
        """
        Index key files in project and link to Project node.

        Args:
            project_path: Project directory path
        """
        project_path_str = str(project_path.absolute())
        indexed_count = 0

        for file in project_path.iterdir():
            if not file.is_file():
                continue

            # Only index key files
            if file.name not in self.key_files:
                continue

            # Create File node
            if self.create_file_node(file):
                # Link to Project
                file_path_str = str(file.absolute())
                query = """
                MATCH (p:Project {path: $project_path})
                MATCH (f:File {path: $file_path})
                MERGE (p)-[:CONTAINS]->(f)
                """

                try:
                    self.neo4j.execute_write(
                        query, {"project_path": project_path_str, "file_path": file_path_str}
                    )
                    indexed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to link file to project: {e}")

        if indexed_count > 0:
            logger.info(f"Indexed {indexed_count} files for {project_path.name}")

    def scan_project(self, project_path: Path):
        """
        Scan a single project and create graph nodes.

        Args:
            project_path: Path to project directory
        """
        logger.info(f"Scanning project: {project_path}")

        try:
            # Create Project node
            project_id = self.create_project_node(project_path)

            # Create Directory node
            self.create_directory_node(project_path)

            # Link Project to Directory
            self.link_project_to_directory(project_path)

            # Index key files
            self.index_project_files(project_path)

            logger.success(f"Project scan complete: {project_path.name}")

        except Exception as e:
            logger.error(f"Failed to scan project {project_path}: {e}")

    def scan_all(self):
        """Scan all configured project roots."""
        logger.info("Starting full project scan...")

        all_projects = []

        for root in self.project_roots:
            if not root.exists():
                logger.warning(f"Project root does not exist: {root}")
                continue

            # Find projects in this root
            projects = self.scan_for_projects(root)
            all_projects.extend(projects)

        logger.info(f"Found {len(all_projects)} total projects")

        # Scan each project
        for project_path in all_projects:
            self.scan_project(project_path)

        logger.success(f"Project scan complete: {len(all_projects)} projects indexed")

        return len(all_projects)


def main():
    """Main entry point for standalone execution."""
    logger.info("System Graph - Project Scanner")

    try:
        scanner = ProjectScanner()
        count = scanner.scan_all()
        logger.success(f"Scan complete: {count} projects")

    except Exception as e:
        logger.error(f"Project scanner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
