"""Validation utilities for news-scraper."""

import re

# Slug pattern: lowercase alphanumeric, hyphens, underscores
# Must start with letter or number
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
SLUG_MAX_LENGTH = 100


class ValidationError(Exception):
    """Raised when validation fails."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


def validate_slug(value: str, field_name: str = "value") -> str:
    """Validate and normalize a slug string.

    Args:
        value: The string to validate.
        field_name: Name of the field for error messages.

    Returns:
        The normalized (lowercase) slug.

    Raises:
        ValidationError: If the value is not a valid slug.
    """
    if not value:
        raise ValidationError(field_name, "cannot be empty")

    # Normalize to lowercase
    normalized = value.lower()

    if len(normalized) > SLUG_MAX_LENGTH:
        raise ValidationError(field_name, f"cannot exceed {SLUG_MAX_LENGTH} characters")

    if not SLUG_PATTERN.match(normalized):
        raise ValidationError(
            field_name,
            "must contain only lowercase letters, numbers, hyphens, and underscores, "
            "and must start with a letter or number",
        )

    return normalized


def is_valid_slug(value: str) -> bool:
    """Check if a string is a valid slug without raising.

    Args:
        value: The string to check.

    Returns:
        True if valid, False otherwise.
    """
    try:
        validate_slug(value)
        return True
    except ValidationError:
        return False
