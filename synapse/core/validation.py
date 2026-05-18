"""Object Validation — Schema validation for research objects.

Validates required fields, enum ranges, and structural integrity.
"""

from __future__ import annotations

from synapse.core.schemas.base import BaseSchema


def validate_object(obj: BaseSchema) -> list[str]:
    """Validate a research object.

    Checks:
    - id is non-empty
    - schema_version is set
    - status is a valid enum value
    - source_type is a valid enum value
    - created_by is a valid enum value

    Args:
        obj: Research object to validate.

    Returns:
        List of validation error messages. Empty if valid.
    """
    errors: list[str] = []

    if not obj.id:
        errors.append("id is required and must be non-empty")

    if not obj.schema_version:
        errors.append("schema_version is required")

    # Validate enum fields (would raise ValueError if invalid)
    try:
        _ = obj.status.value
    except AttributeError:
        errors.append(f"Invalid status: {obj.status!r}")

    try:
        _ = obj.source_type.value
    except AttributeError:
        errors.append(f"Invalid source_type: {obj.source_type!r}")

    try:
        _ = obj.created_by.value
    except AttributeError:
        errors.append(f"Invalid created_by: {obj.created_by!r}")

    # Validate market_context
    mc = obj.market_context
    if not mc.research_date:
        errors.append("market_context.research_date is required")
    if not mc.market_date:
        errors.append("market_context.market_date is required")

    return errors


def validate_required_fields(obj: BaseSchema, required_fields: list[str]) -> list[str]:
    """Validate that specific fields are non-empty on an object.

    Args:
        obj: Research object to validate.
        required_fields: List of field names that must be non-empty.

    Returns:
        List of validation error messages. Empty if valid.
    """
    errors: list[str] = []
    for field_name in required_fields:
        value = getattr(obj, field_name, None)
        if value is None or value == "" or value == []:
            errors.append(f"{field_name} is required and must be non-empty")
    return errors
