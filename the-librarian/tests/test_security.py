"""
Security tests for Cypher injection prevention and path validation.

Tests that security measures are properly enforced to prevent attacks.
"""

import pytest
from unittest.mock import AsyncMock, patch
from src.graph.schema import (
    validate_node_label,
    validate_relationship_type,
    ALLOWED_NODE_LABELS,
    ALLOWED_RELATIONSHIP_TYPES,
)
from src.processing.parser import validate_file_path


class TestCypherInjectionPrevention:
    """Test Cypher injection prevention mechanisms."""

    def test_architecture_label_accepted(self):
        """Test that the Architecture label specifically is accepted."""
        # Tests actual usage - not circular
        validate_node_label("Architecture")

    def test_design_label_accepted(self):
        """Test that the Design label specifically is accepted."""
        validate_node_label("Design")

    def test_chunk_label_accepted(self):
        """Test that the Chunk label specifically is accepted."""
        validate_node_label("Chunk")

    def test_invalid_node_label_rejected(self):
        """Test that invalid node labels are rejected."""
        invalid_labels = [
            "FakeLabel",
            "Architecture; DROP DATABASE",
            "Design') MATCH (n) DETACH DELETE n--",
            "'; DELETE *",
            "UNION SELECT",
        ]

        for label in invalid_labels:
            with pytest.raises(ValueError, match="Invalid node label"):
                validate_node_label(label)

    def test_defines_relationship_accepted(self):
        """Test that the DEFINES relationship specifically is accepted."""
        validate_relationship_type("DEFINES")

    def test_implements_relationship_accepted(self):
        """Test that the IMPLEMENTS relationship specifically is accepted."""
        validate_relationship_type("IMPLEMENTS")

    def test_contains_relationship_accepted(self):
        """Test that the CONTAINS relationship specifically is accepted."""
        validate_relationship_type("CONTAINS")

    def test_invalid_relationship_type_rejected(self):
        """Test that invalid relationship types are rejected."""
        invalid_rels = [
            "FAKE_REL",
            "CREATES; DROP DATABASE",
            "LINKS') MATCH (n) DETACH DELETE n--",
        ]

        for rel_type in invalid_rels:
            with pytest.raises(ValueError, match="Invalid relationship type"):
                validate_relationship_type(rel_type)

    def test_label_whitelist_not_empty(self):
        """Test that label whitelist is not empty (prevents accidental deletion)."""
        assert len(ALLOWED_NODE_LABELS) > 0, "Label whitelist must not be empty"
        assert len(ALLOWED_NODE_LABELS) >= 8, "Label whitelist should contain at least 8 core labels"

    def test_relationship_whitelist_not_empty(self):
        """Test that relationship whitelist is not empty (prevents accidental deletion)."""
        assert len(ALLOWED_RELATIONSHIP_TYPES) > 0, "Relationship whitelist must not be empty"
        assert len(ALLOWED_RELATIONSHIP_TYPES) >= 16, "Relationship whitelist should contain at least 16 core types (including CONTAINS)"

    def test_case_sensitive_label_validation(self):
        """Test that label validation is case-sensitive."""
        # "architecture" (lowercase) should be rejected even though "Architecture" is valid
        with pytest.raises(ValueError, match="Invalid node label"):
            validate_node_label("architecture")

        with pytest.raises(ValueError, match="Invalid node label"):
            validate_node_label("ARCHITECTURE")

    def test_case_sensitive_relationship_validation(self):
        """Test that relationship validation is case-sensitive."""
        # "defines" (lowercase) should be rejected even though "DEFINES" is valid
        with pytest.raises(ValueError, match="Invalid relationship type"):
            validate_relationship_type("defines")

        with pytest.raises(ValueError, match="Invalid relationship type"):
            validate_relationship_type("Defines")


class TestPathTraversalPrevention:
    """Test path traversal attack prevention."""

    def test_valid_paths_accepted(self):
        """Test that valid paths are accepted."""
        valid_paths = [
            "/home/user/docs/test.md",
            "/var/lib/app/documents/architecture.md",
            "docs/design.md",
        ]

        for path in valid_paths:
            # Should not raise exception
            assert validate_file_path(path) is True

    def test_parent_directory_traversal_rejected(self):
        """Test that parent directory traversal is rejected."""
        dangerous_paths = [
            "../../../etc/passwd",
            "docs/../../../etc/passwd",
            "docs/./../../secret",
            "/docs/../../../root/.ssh/id_rsa",
        ]

        for path in dangerous_paths:
            with pytest.raises(ValueError, match="(Path traversal detected|Dangerous pattern)"):
                validate_file_path(path)

    def test_home_directory_expansion_rejected(self):
        """Test that home directory expansion is rejected."""
        with pytest.raises(ValueError, match="Dangerous pattern"):
            validate_file_path("~/secrets/config")

    def test_variable_expansion_rejected(self):
        """Test that variable expansion is rejected."""
        dangerous_paths = [
            "$HOME/secrets",
            "${PWD}/config",
            "docs/$USER/private",
        ]

        for path in dangerous_paths:
            with pytest.raises(ValueError, match="Dangerous pattern"):
                validate_file_path(path)

    def test_command_substitution_rejected(self):
        """Test that command substitution is rejected."""
        with pytest.raises(ValueError, match="Dangerous pattern"):
            validate_file_path("docs/`whoami`.md")

    def test_allowed_directory_enforcement(self):
        """Test that allowed_directories are enforced."""
        allowed_dirs = ["/home/user/docs", "/var/lib/app"]

        # Path within allowed directory
        assert validate_file_path("/home/user/docs/test.md", allowed_dirs) is True

        # Path outside allowed directories
        with pytest.raises(ValueError, match="outside allowed directories"):
            validate_file_path("/etc/passwd", allowed_dirs)

        # Attempt to escape with ..
        with pytest.raises(ValueError, match="(Path traversal detected|Dangerous pattern)"):
            validate_file_path("/home/user/docs/../../../etc/passwd", allowed_dirs)

    def test_windows_path_traversal_rejected(self):
        """Test that Windows-style path traversal is rejected."""
        dangerous_paths = [
            "docs\\..\\..\\windows\\system32",
            "C:\\..\\..\\secrets",
        ]

        for path in dangerous_paths:
            with pytest.raises(ValueError, match="(Path traversal detected|Dangerous pattern)"):
                validate_file_path(path)


class TestSecurityDefenseInDepth:
    """Test defense-in-depth security measures."""

    def test_multiple_security_layers(self):
        """Test that multiple security layers are in place."""
        # Layer 1: Label validation
        with pytest.raises(ValueError):
            validate_node_label("MaliciousLabel")

        # Layer 2: Path validation
        with pytest.raises(ValueError):
            validate_file_path("../../../etc/passwd")

    def test_wildcard_patterns_in_paths(self):
        """Test that wildcard patterns in paths are handled safely."""
        # Wildcards could be used for directory traversal in some contexts
        dangerous_paths = [
            "docs/*/../../etc/passwd",
            "../*/secrets",
        ]

        for path in dangerous_paths:
            # Should be rejected due to ../ pattern
            with pytest.raises(ValueError, match="(Path traversal detected|Dangerous pattern)"):
                validate_file_path(path)

    def test_null_byte_injection_rejected(self):
        """Test that null byte injection is rejected."""
        # Null bytes historically used to truncate strings and bypass validation
        path_with_null = "docs/test.md\x00../../etc/passwd"

        # Should be rejected - null bytes are dangerous
        with pytest.raises(ValueError):
            validate_file_path(path_with_null)

    def test_empty_label_rejected(self):
        """Test that empty labels are rejected."""
        with pytest.raises(ValueError, match="Invalid node label"):
            validate_node_label("")

    def test_empty_relationship_rejected(self):
        """Test that empty relationship types are rejected."""
        with pytest.raises(ValueError, match="Invalid relationship type"):
            validate_relationship_type("")

    def test_whitespace_only_label_rejected(self):
        """Test that whitespace-only labels are rejected."""
        with pytest.raises(ValueError, match="Invalid node label"):
            validate_node_label("   ")

        with pytest.raises(ValueError, match="Invalid node label"):
            validate_node_label("\t")

        with pytest.raises(ValueError, match="Invalid node label"):
            validate_node_label("\n")


class TestSecurityIntegration:
    """Test that security validations are actually enforced in real operations."""

    @pytest.mark.asyncio
    async def test_graph_operations_validates_labels(self):
        """Test that GraphOperations.create_node() calls validate_node_label()."""
        from src.graph.operations import GraphOperations
        from src.graph.connection import Neo4jConnection

        # Create mock connection
        mock_conn = AsyncMock(spec=Neo4jConnection)
        ops = GraphOperations(mock_conn)

        # Attempt to create node with malicious label - should fail validation
        with pytest.raises(ValueError, match="Invalid node label"):
            await ops.create_node("Architecture; DROP DATABASE", {"id": "test-001"})

        # Verify the query was NEVER executed (validation prevented it)
        mock_conn.execute_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_graph_operations_accepts_valid_labels(self):
        """Test that GraphOperations.create_node() accepts valid labels."""
        from src.graph.operations import GraphOperations
        from src.graph.connection import Neo4jConnection

        # Create mock connection
        mock_conn = AsyncMock(spec=Neo4jConnection)
        mock_conn.execute_write.return_value = [{"node_id": "test-001"}]
        ops = GraphOperations(mock_conn)

        # Create node with valid label - should succeed
        result = await ops.create_node("Architecture", {"id": "test-001"})

        # Verify validation passed and query WAS executed
        assert result == "test-001"
        mock_conn.execute_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_graph_get_node_validates_labels(self):
        """Test that GraphOperations.get_node() calls validate_node_label()."""
        from src.graph.operations import GraphOperations
        from src.graph.connection import Neo4jConnection

        mock_conn = AsyncMock(spec=Neo4jConnection)
        ops = GraphOperations(mock_conn)

        # Attempt to get node with malicious label - should fail validation
        with pytest.raises(ValueError, match="Invalid node label"):
            await ops.get_node("FakeLabel", "test-001")

        # Verify the query was NEVER executed
        mock_conn.execute_read.assert_not_called()

    @pytest.mark.asyncio
    async def test_graph_update_node_validates_labels(self):
        """Test that GraphOperations.update_node() calls validate_node_label()."""
        from src.graph.operations import GraphOperations
        from src.graph.connection import Neo4jConnection

        mock_conn = AsyncMock(spec=Neo4jConnection)
        ops = GraphOperations(mock_conn)

        # Attempt to update node with malicious label - should fail validation
        with pytest.raises(ValueError, match="Invalid node label"):
            await ops.update_node("Design') MATCH (n) DELETE n--", "test-001", {"title": "x"})

        # Verify the query was NEVER executed
        mock_conn.execute_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_graph_delete_node_validates_labels(self):
        """Test that GraphOperations.delete_node() calls validate_node_label()."""
        from src.graph.operations import GraphOperations
        from src.graph.connection import Neo4jConnection

        mock_conn = AsyncMock(spec=Neo4jConnection)
        ops = GraphOperations(mock_conn)

        # Attempt to delete node with malicious label - should fail validation
        with pytest.raises(ValueError, match="Invalid node label"):
            await ops.delete_node("'; DELETE ALL", "test-001")

        # Verify the query was NEVER executed
        mock_conn.execute_write.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
