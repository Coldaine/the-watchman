"""
Service-level test for the DockerScanner.

This test follows the Pragmatic Test Architect philosophy:
- It's a large-span test, verifying the entire flow from scanning to data persistence.
- It uses real dependencies (Testcontainers for Neo4j, real Docker daemon) to provide high confidence.
- It tests observable outcomes (data in the graph) rather than implementation details.
- It tells a complete story: "When the scanner runs, it accurately maps running containers."
"""

import sys
import pytest
import docker
import json
from pathlib import Path
from docker.models.containers import Container
from neo4j import GraphDatabase
from testcontainers.neo4j import Neo4jContainer

# Add project root to path to allow absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from domains.system_graph.scanners.docker import DockerScanner
from app.utils.neo4j_client import Neo4jClient

# A simple, lightweight container to use as our test subject
TEST_CONTAINER_IMAGE = "nginx:1.25-alpine"
TEST_CONTAINER_NAME = "watchman-test-subject-nginx"
TEST_HOST_PORT = 8088

@pytest.fixture(scope="module")
def docker_client() -> docker.DockerClient:
    """Provides a Docker client for test setup."""
    return docker.from_env()

@pytest.fixture(scope="module")
def test_subject_container(docker_client: docker.DockerClient) -> Container:
    """
    Starts and manages a "test subject" container for the scanner to find.
    This fixture ensures the container is running before tests execute
    and is cleaned up afterward.
    """
    print(f"Starting test subject container: {TEST_CONTAINER_NAME}")
    try:
        # Clean up any previous instances
        existing = docker_client.containers.get(TEST_CONTAINER_NAME)
        existing.remove(force=True)
        print(f"Removed existing test container: {TEST_CONTAINER_NAME}")
    except docker.errors.NotFound:
        pass # It's fine if it doesn't exist

    container = docker_client.containers.run(
        TEST_CONTAINER_IMAGE,
        name=TEST_CONTAINER_NAME,
        ports={'80/tcp': TEST_HOST_PORT},
        labels={"com.watchman.test": "true", "owner": "test-suite"},
        detach=True,
    )
    yield container
    print(f"Stopping and removing test subject container: {TEST_CONTAINER_NAME}")
    container.remove(force=True)


def test_docker_scanner_maps_container_to_graph(test_subject_container: Container, monkeypatch):
    """
    Verifies the DockerScanner can find a running container and correctly
    represent it and its exposed ports in a Neo4j graph.
    """
    with Neo4jContainer("neo4j:5.14-community") as neo4j:
        print(f"Test Neo4j container is running at: {neo4j.get_connection_url()}")

        # --- Test Setup ---

        # 1. Create a Neo4j client connected to our test container
        test_neo4j_client = Neo4jClient(
            uri=neo4j.get_connection_url(),
            user=neo4j.username,
            password=neo4j.password
        )

        # 2. Use monkeypatch to force the DockerScanner to use our test DB
        #    instead of the production one from settings. This is a crucial
        #    seam that allows for isolated, large-span testing.
        monkeypatch.setattr(
            "domains.system_graph.scanners.docker.get_neo4j_client",
            lambda: test_neo4j_client
        )

        # --- Act ---

        # 3. Instantiate and run the scanner. It will now talk to our test DB.
        scanner = DockerScanner()
        scan_result = scanner.scan_containers()

        # --- Assert ---

        # 4. Verify the scanner reported finding at least our container
        assert scan_result > 0

        # 5. Query the test graph to verify the scanner created the correct nodes and relationships.
        #    This is the "External Observer" check. We are looking at the final,
        #    observable state of the system, not the scanner's internal workings.
        with test_neo4j_client.driver.session() as session:
            # Check for the Container node
            container_result = session.run(
                "MATCH (c:Container {name: $name}) RETURN c",
                name=TEST_CONTAINER_NAME
            ).single()

            assert container_result is not None, "Container node was not created"
            container_node = container_result["c"]
            assert container_node["image"] == TEST_CONTAINER_IMAGE
            assert container_node["state"] == "running"

            # Labels are stored as a JSON string, so we need to parse it
            labels = json.loads(container_node["labels"])
            assert labels["com.watchman.test"] == "true"
            assert labels["owner"] == "test-suite"

            # Check for the exposed NetworkEndpoint and the relationship
            endpoint_result = session.run(
                """
                MATCH (c:Container {name: $name})-[:EXPOSES]->(e:NetworkEndpoint)
                RETURN e
                """,
                name=TEST_CONTAINER_NAME
            ).single()

            assert endpoint_result is not None, "EXPOSES relationship or NetworkEndpoint node not created"
            endpoint_node = endpoint_result["e"]
            assert endpoint_node["port"] == TEST_HOST_PORT
            assert endpoint_node["host"] == "0.0.0.0"
            assert endpoint_node["protocol"] == "tcp"

            print("Verification successful: Container and NetworkEndpoint found in graph.")

        # --- Teardown ---
        test_neo4j_client.close()
        print("Test finished and client closed.")