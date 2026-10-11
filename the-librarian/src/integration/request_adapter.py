"""
Request adapter for converting documents to validation requests.

Transforms ParsedDocument objects into AgentRequest format for validation,
handling metadata mapping and reference extraction.
"""

from typing import Dict, Any, List
import hashlib
from datetime import datetime
import logging

from ..processing.models import ParsedDocument
from ..validation.agent_models import AgentRequest

logger = logging.getLogger(__name__)


class RequestAdapter:
    """Adapter for converting documents to validation requests."""

    def document_to_request(
        self,
        document: ParsedDocument,
        agent_id: str = "ingestion_pipeline",
        action: str = "create",
        session_id: str = None,
        target_id: str = None
    ) -> AgentRequest:
        """
        Convert a ParsedDocument to an AgentRequest for validation.

        Args:
            document: Parsed document to convert
            agent_id: ID of the agent making the request
            action: Action type (create/update/delete)
            session_id: Optional session context
            target_id: Optional target ID for updates

        Returns:
            AgentRequest ready for validation

        Raises:
            ValueError: If required document fields are missing
        """
        # Validate required frontmatter
        if "id" not in document.frontmatter:
            raise ValueError("Document missing required 'id' in frontmatter")

        # Generate request ID
        request_id = self._generate_request_id(document, action)

        # Extract references from content
        references = self._extract_references(document)

        # Build content dictionary
        content = self._build_content(document)

        # Generate rationale
        rationale = self._generate_rationale(document, action)

        # Determine target type
        target_type = self._get_target_type(document.doc_type)

        # Create request
        request = AgentRequest(
            id=request_id,
            agent_id=agent_id,
            action=action,
            target_type=target_type,
            content=content,
            rationale=rationale,
            references=references,
            timestamp=datetime.now(),
            session_id=session_id,
            target_id=target_id or document.frontmatter.get("id"),
            metadata={
                "source_path": document.path,
                "content_hash": document.hash,
                "doc_type": document.doc_type,
                "size_bytes": document.size_bytes,
                "section_count": len(document.sections)
            }
        )

        logger.debug(f"Created validation request: {request_id}")
        return request

    def _generate_request_id(self, document: ParsedDocument, action: str) -> str:
        """
        Generate unique request ID.

        Args:
            document: Document being processed
            action: Action type

        Returns:
            Unique request identifier
        """
        doc_id = document.frontmatter.get("id", "unknown")
        timestamp = datetime.now().isoformat()
        id_string = f"{action}:{doc_id}:{timestamp}:{document.hash[:8]}"

        # Generate short hash
        return hashlib.sha256(id_string.encode()).hexdigest()[:16]

    def _extract_references(self, document: ParsedDocument) -> List[str]:
        """
        Extract document references from content and frontmatter.

        Looks for:
        - Frontmatter 'references' field
        - Frontmatter 'architecture_ref' field
        - Markdown links to other specs: [text](spec:ID)

        Args:
            document: Document to extract from

        Returns:
            List of reference IDs
        """
        references = []

        # From frontmatter
        if "references" in document.frontmatter:
            refs = document.frontmatter["references"]
            if isinstance(refs, list):
                references.extend(refs)
            else:
                references.append(str(refs))

        # Architecture reference for design docs
        if "architecture_ref" in document.frontmatter:
            arch_ref = document.frontmatter["architecture_ref"]
            if arch_ref and arch_ref not in references:
                references.append(str(arch_ref))

        # Extract from content (basic pattern matching)
        # Look for patterns like: [[ARCH-001]] or [ARCH-001]
        import re
        patterns = [
            r'\[\[([A-Z]+-[0-9]+)\]\]',  # [[ARCH-001]]
            r'\[([A-Z]+-[0-9]+)\]',      # [ARCH-001]
            r'spec:([A-Z]+-[0-9]+)',     # spec:ARCH-001
        ]

        for pattern in patterns:
            matches = re.findall(pattern, document.content)
            for match in matches:
                if match not in references:
                    references.append(match)

        # Deduplicate while preserving order
        seen = set()
        unique_refs = []
        for ref in references:
            if ref not in seen:
                seen.add(ref)
                unique_refs.append(ref)

        logger.debug(f"Extracted {len(unique_refs)} references from document")
        return unique_refs

    def _build_content(self, document: ParsedDocument) -> Dict[str, Any]:
        """
        Build content dictionary for validation request.

        Includes all relevant document information for validation rules.

        Args:
            document: Document to convert

        Returns:
            Content dictionary
        """
        content = {
            # Core identification
            "id": document.frontmatter.get("id"),
            "title": document.frontmatter.get("title", ""),
            "doc_type": document.doc_type,

            # Metadata
            "subsystem": document.frontmatter.get("subsystem", ""),
            "version": document.frontmatter.get("version", "1.0.0"),
            "status": document.frontmatter.get("status", "draft"),
            "owners": document.frontmatter.get("owners", []),

            # Content
            "content": document.content,
            "content_hash": document.hash,

            # File info
            "path": document.path,
            "size_bytes": document.size_bytes,
            "modified_at": document.modified_at.isoformat() if document.modified_at else None,

            # Structure
            "sections": document.sections,
            "section_count": len(document.sections),

            # Frontmatter
            "frontmatter": document.frontmatter
        }

        # Add architecture-specific fields
        if document.doc_type == "architecture":
            content["compliance_level"] = document.frontmatter.get(
                "compliance_level", "strict"
            )
            content["drift_tolerance"] = document.frontmatter.get(
                "drift_tolerance", "none"
            )

        # Add design-specific fields
        if document.doc_type == "design":
            content["component"] = document.frontmatter.get("component", "")
            content["architecture_ref"] = document.frontmatter.get(
                "architecture_ref", ""
            )

        return content

    def _generate_rationale(
        self,
        document: ParsedDocument,
        action: str
    ) -> str:
        """
        Generate rationale for the validation request.

        Args:
            document: Document being validated
            action: Action type

        Returns:
            Rationale string
        """
        doc_id = document.frontmatter.get("id", "unknown")
        doc_type = document.doc_type
        status = document.frontmatter.get("status", "draft")

        rationales = {
            "create": (
                f"Creating new {doc_type} document '{doc_id}' with status '{status}'. "
                f"Validating compliance with documentation standards, "
                f"architecture alignment, and required field presence."
            ),
            "update": (
                f"Updating {doc_type} document '{doc_id}' to status '{status}'. "
                f"Validating changes for compatibility, drift detection, "
                f"and continued compliance with established standards."
            ),
            "delete": (
                f"Requesting deletion of {doc_type} document '{doc_id}'. "
                f"Validating that removal will not break dependencies "
                f"or violate architectural constraints."
            )
        }

        return rationales.get(action, f"{action.capitalize()} {doc_type} document {doc_id}")

    def _get_target_type(self, doc_type: str) -> str:
        """
        Map document type to target type for validation.

        Args:
            doc_type: Document type

        Returns:
            Target type string
        """
        # Normalize and validate
        type_mapping = {
            "architecture": "architecture",
            "design": "design",
            "code": "code",
            "research": "research",
            "tasks": "tasks"
        }

        return type_mapping.get(doc_type.lower(), doc_type.lower())

    def extract_validation_metadata(self, document: ParsedDocument) -> Dict[str, Any]:
        """
        Extract metadata specifically useful for validation.

        Args:
            document: Document to extract from

        Returns:
            Dictionary of validation-relevant metadata
        """
        return {
            "has_title": "title" in document.frontmatter,
            "has_owners": bool(document.frontmatter.get("owners")),
            "owner_count": len(document.frontmatter.get("owners", [])),
            "has_version": "version" in document.frontmatter,
            "section_count": len(document.sections),
            "content_length": len(document.content),
            "has_references": len(self._extract_references(document)) > 0,
            "reference_count": len(self._extract_references(document)),
            "compliance_level": document.frontmatter.get("compliance_level"),
            "drift_tolerance": document.frontmatter.get("drift_tolerance"),
        }
