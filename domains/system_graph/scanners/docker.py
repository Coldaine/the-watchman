"""
Docker scanner for System Graph domain.

Discovers Docker containers, volumes, networks, and images.
Creates Container and NetworkEndpoint nodes with relationships.
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

import docker
from docker.errors import DockerException
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.utils.config import get_settings
from app.utils.neo4j_client import get_neo4j_client
from app.utils.helpers import create_network_endpoint_key, parse_docker_image_tag, now_iso


class DockerScanner:
    """Scanner for Docker containers and infrastructure."""

    def __init__(self):
        """Initialize Docker scanner."""
        self.settings = get_settings()
        self.neo4j = get_neo4j_client()

        try:
            self.docker_client = docker.from_env()
            # Test connection
            self.docker_client.ping()
            logger.success("Connected to Docker daemon")
        except DockerException as e:
            logger.error(f"Failed to connect to Docker: {e}")
            self.docker_client = None

    def scan_containers(self) -> int:
        """
        Scan all Docker containers (running and stopped).

        Returns:
            Number of containers scanned
        """
        if not self.docker_client:
            logger.error("Docker client not available")
            return 0

        logger.info("Scanning Docker containers...")

        try:
            containers = self.docker_client.containers.list(all=True)
            logger.info(f"Found {len(containers)} containers")

            for container in containers:
                self.process_container(container)

            return len(containers)

        except Exception as e:
            logger.error(f"Failed to scan containers: {e}")
            return 0

    def process_container(self, container):
        """
        Process a single Docker container.

        Args:
            container: Docker container object
        """
        try:
            # Get container details
            attrs = container.attrs
            container_id = container.id
            name = container.name
            image = attrs.get('Config', {}).get('Image', 'unknown')
            state = container.status
            created = attrs.get('Created')

            # Parse image
            image_info = parse_docker_image_tag(image)

            logger.info(f"Processing container: {name} ({state})")

            # Create Container node
            self.create_container_node(
                container_id=container_id,
                name=name,
                image=image,
                state=state,
                created=created,
                labels=attrs.get('Config', {}).get('Labels', {})
            )

            # Process exposed ports
            self.process_container_ports(container_id, attrs)

            # Process volumes
            self.process_container_volumes(container_id, attrs)

            # Link to project if Compose project detected
            self.link_to_compose_project(container_id, attrs)

            logger.success(f"Container processed: {name}")

        except Exception as e:
            logger.error(f"Failed to process container {container.name}: {e}")

    def create_container_node(
        self,
        container_id: str,
        name: str,
        image: str,
        state: str,
        created: Optional[str],
        labels: Dict[str, str]
    ):
        """
        Create or update Container node in Neo4j.

        Args:
            container_id: Container ID
            name: Container name
            image: Image name
            state: Container state (running, stopped, etc.)
            created: Creation timestamp
            labels: Container labels
        """
        query = """
        MERGE (c:Container {id: $id})
        ON CREATE SET
            c.name = $name,
            c.image = $image,
            c.state = $state,
            c.created = datetime($created),
            c.labels = $labels
        ON MATCH SET
            c.state = $state,
            c.labels = $labels
        RETURN c.id AS id
        """

        try:
            # Convert labels dict to a JSON string for storage
            labels_str = json.dumps(labels)
            self.neo4j.execute_write(query, {
                "id": container_id,
                "name": name,
                "image": image,
                "state": state,
                "created": created,
                "labels": labels_str
            })

        except Exception as e:
            logger.error(f"Failed to create Container node: {e}")
            raise

    def process_container_ports(self, container_id: str, attrs: Dict[str, Any]):
        """
        Process container port mappings and create NetworkEndpoint nodes.

        Args:
            container_id: Container ID
            attrs: Container attributes
        """
        network_settings = attrs.get('NetworkSettings', {})
        ports = network_settings.get('Ports', {})

        if not ports:
            return

        for container_port, bindings in ports.items():
            if not bindings:
                # Port exposed but not bound to host
                continue

            for binding in bindings:
                host_ip = binding.get('HostIp', '0.0.0.0')
                host_port = binding.get('HostPort')

                if not host_port:
                    continue

                # Parse port/protocol
                if '/' in container_port:
                    port_num, protocol = container_port.split('/')
                else:
                    port_num = container_port
                    protocol = 'tcp'

                # Create NetworkEndpoint node
                endpoint_key = create_network_endpoint_key(host_ip, int(host_port), protocol)

                query = """
                MATCH (c:Container {id: $container_id})
                MERGE (e:NetworkEndpoint {key: $key})
                ON CREATE SET
                    e.host = $host,
                    e.port = $port,
                    e.protocol = $protocol
                MERGE (c)-[:EXPOSES]->(e)
                """

                try:
                    self.neo4j.execute_write(query, {
                        "container_id": container_id,
                        "key": endpoint_key,
                        "host": host_ip,
                        "port": int(host_port),
                        "protocol": protocol
                    })

                    logger.debug(f"Created NetworkEndpoint: {endpoint_key}")

                except Exception as e:
                    logger.warning(f"Failed to create NetworkEndpoint: {e}")

    def process_container_volumes(self, container_id: str, attrs: Dict[str, Any]):
        """
        Process container volume mounts and link to Directory nodes.

        Args:
            container_id: Container ID
            attrs: Container attributes
        """
        mounts = attrs.get('Mounts', [])

        for mount in mounts:
            source = mount.get('Source')
            destination = mount.get('Destination')
            mount_type = mount.get('Type', 'bind')

            if not source:
                continue

            # Create Directory node for volume source
            query = """
            MATCH (c:Container {id: $container_id})
            MERGE (d:Directory {path: $source})
            ON CREATE SET d.name = $name
            MERGE (c)-[:USES_VOLUME {
                destination: $destination,
                type: $type
            }]->(d)
            """

            try:
                self.neo4j.execute_write(query, {
                    "container_id": container_id,
                    "source": source,
                    "name": Path(source).name,
                    "destination": destination,
                    "type": mount_type
                })

                logger.debug(f"Linked volume: {source}")

            except Exception as e:
                logger.warning(f"Failed to link volume: {e}")

    def link_to_compose_project(self, container_id: str, attrs: Dict[str, Any]):
        """
        Link container to Compose project if labels indicate it's part of one.

        Args:
            container_id: Container ID
            attrs: Container attributes
        """
        labels = attrs.get('Config', {}).get('Labels', {})

        # Check for Docker Compose labels
        project_name = labels.get('com.docker.compose.project')
        service_name = labels.get('com.docker.compose.service')

        if not project_name:
            return

        # Try to find matching Project node
        query = """
        MATCH (c:Container {id: $container_id})
        MATCH (p:Project)
        WHERE toLower(p.name) = toLower($project_name)
        MERGE (c)-[:PART_OF_PROJECT {service: $service}]->(p)
        """

        try:
            self.neo4j.execute_write(query, {
                "container_id": container_id,
                "project_name": project_name,
                "service": service_name
            })

            logger.debug(f"Linked container to project: {project_name}")

        except Exception as e:
            logger.debug(f"Could not link to project (may not exist yet): {e}")

    def scan_networks(self) -> int:
        """
        Scan Docker networks.

        Returns:
            Number of networks scanned
        """
        if not self.docker_client:
            return 0

        logger.info("Scanning Docker networks...")

        try:
            networks = self.docker_client.networks.list()
            logger.info(f"Found {len(networks)} networks")

            # For now, just log them
            # Could create Network nodes if needed

            return len(networks)

        except Exception as e:
            logger.error(f"Failed to scan networks: {e}")
            return 0

    def scan_volumes(self) -> int:
        """
        Scan Docker volumes.

        Returns:
            Number of volumes scanned
        """
        if not self.docker_client:
            return 0

        logger.info("Scanning Docker volumes...")

        try:
            volumes = self.docker_client.volumes.list()
            logger.info(f"Found {len(volumes)} volumes")

            # Volumes are already handled via container mounts

            return len(volumes)

        except Exception as e:
            logger.error(f"Failed to scan volumes: {e}")
            return 0

    def scan_all(self) -> Dict[str, int]:
        """
        Perform full Docker infrastructure scan.

        Returns:
            Dict with counts of scanned resources
        """
        logger.info("Starting Docker infrastructure scan...")

        results = {
            "containers": self.scan_containers(),
            "networks": self.scan_networks(),
            "volumes": self.scan_volumes()
        }

        logger.success(f"Docker scan complete: {results}")
        return results


def main():
    """Main entry point for standalone execution."""
    logger.info("System Graph - Docker Scanner")

    try:
        scanner = DockerScanner()
        results = scanner.scan_all()

        logger.success(f"Docker scan complete")
        logger.info(f"  Containers: {results['containers']}")
        logger.info(f"  Networks: {results['networks']}")
        logger.info(f"  Volumes: {results['volumes']}")

    except Exception as e:
        logger.error(f"Docker scanner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
