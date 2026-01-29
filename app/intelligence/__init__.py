"""
Intelligence Layer

This module contains the accumulated expertise, quality rubrics, and domain knowledge
that makes each department truly intelligent. Think of these as the "souls" of our agents.

Structure:
- departments/  - Deep expertise for each department role
- formats/      - Platform and format-specific best practices
- quality/      - Self-evaluation rubrics
- brand/        - Brand application logic

Usage:
    from app.intelligence import load_department, load_format, load_rubric

    writer_expertise = load_department("writer")
    tiktok_rules = load_format("tiktok")
    copy_rubric = load_rubric("copy")
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from functools import lru_cache

INTELLIGENCE_DIR = Path(__file__).parent


@lru_cache(maxsize=50)
def load_department(name: str) -> str:
    """
    Load department expertise.

    Args:
        name: Department name (writer, designer, strategist, etc.)

    Returns:
        The department's system prompt / expertise content
    """
    path = INTELLIGENCE_DIR / "departments" / f"{name}.md"
    if path.exists():
        return path.read_text()
    return ""


@lru_cache(maxsize=50)
def load_format(name: str) -> str:
    """
    Load format-specific expertise.

    Args:
        name: Format name (tiktok, instagram, email, blog, etc.)

    Returns:
        Platform/format-specific rules and best practices
    """
    path = INTELLIGENCE_DIR / "formats" / f"{name}.md"
    if path.exists():
        return path.read_text()
    return ""


@lru_cache(maxsize=20)
def load_rubric(name: str) -> str:
    """
    Load quality evaluation rubric.

    Args:
        name: Rubric name (copy, visual, strategy, etc.)

    Returns:
        Quality evaluation criteria
    """
    path = INTELLIGENCE_DIR / "quality" / f"{name}.md"
    if path.exists():
        return path.read_text()
    return ""


def load_brand_application() -> str:
    """Load brand application guidelines."""
    path = INTELLIGENCE_DIR / "brand" / "application.md"
    if path.exists():
        return path.read_text()
    return ""


def get_department_prompt(
    department: str,
    format_type: Optional[str] = None,
    include_rubric: bool = True
) -> str:
    """
    Build a complete department prompt with all relevant expertise.

    Args:
        department: The department name
        format_type: Optional format (tiktok, email, etc.) for additional context
        include_rubric: Whether to include self-evaluation rubric

    Returns:
        Complete system prompt with all relevant expertise
    """
    parts = []

    # Core department expertise
    dept_content = load_department(department)
    if dept_content:
        parts.append(dept_content)

    # Format-specific rules
    if format_type:
        format_content = load_format(format_type)
        if format_content:
            parts.append(f"\n\n## Format-Specific Rules: {format_type.upper()}\n\n{format_content}")

    # Quality rubric
    if include_rubric:
        # Map department to rubric type
        rubric_map = {
            "writer": "copy",
            "designer": "visual",
            "video": "visual",
            "strategist": "strategy",
            "concept_developer": "strategy",
            "creative_director": "strategy",
            "researcher": "research",
        }
        rubric_name = rubric_map.get(department, "general")
        rubric_content = load_rubric(rubric_name)
        if rubric_content:
            parts.append(f"\n\n## Quality Self-Evaluation\n\n{rubric_content}")

    # Brand application
    brand_content = load_brand_application()
    if brand_content:
        parts.append(f"\n\n## Brand Application\n\n{brand_content}")

    return "\n".join(parts)


def clear_cache():
    """Clear all cached intelligence content."""
    load_department.cache_clear()
    load_format.cache_clear()
    load_rubric.cache_clear()
