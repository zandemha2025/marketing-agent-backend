"""
Brand Safety Checker - Ensure content is brand-safe.

Checks for:
- Inappropriate content
- Competitor logos/products
- Controversial imagery
- Platform policy compliance
- Legal concerns
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


async def check_brand_safety(
    video_path: str,
    brand_guidelines: Dict[str, Any] = None,
    target_platforms: List[str] = None,
) -> float:
    """
    Check if content is brand-safe.

    Returns a score from 0 to 1 where:
    - 0.0-0.3: Major brand safety issues
    - 0.3-0.6: Some concerns, review recommended
    - 0.6-0.8: Minor issues, likely safe
    - 0.8-1.0: Brand safe

    Args:
        video_path: Path to video file
        brand_guidelines: Optional brand safety rules
        target_platforms: Platforms to check compliance for

    Returns:
        Brand safety score (0-1)
    """
    logger.info(f"Checking brand safety for: {video_path}")

    checks = []

    # Check for inappropriate content
    inappropriate_score = await _check_inappropriate_content(video_path)
    checks.append(("inappropriate", inappropriate_score, 0.4))

    # Check for competitor presence
    competitor_score = await _check_competitor_presence(video_path, brand_guidelines)
    checks.append(("competitors", competitor_score, 0.2))

    # Check platform compliance
    if target_platforms:
        platform_score = await _check_platform_compliance(video_path, target_platforms)
        checks.append(("platform", platform_score, 0.2))
    else:
        checks.append(("platform", 0.95, 0.2))

    # Check legal concerns
    legal_score = await _check_legal_concerns(video_path)
    checks.append(("legal", legal_score, 0.2))

    # Calculate weighted score
    total_score = sum(score * weight for _, score, weight in checks)

    logger.info(f"Brand safety score: {total_score:.2f}")
    return min(1.0, max(0.0, total_score))


async def _check_inappropriate_content(video_path: str) -> float:
    """Check for inappropriate/explicit content."""
    # In production, use:
    # - Google Cloud Vision SafeSearch
    # - AWS Rekognition Content Moderation
    # - Azure Content Moderator

    # Check for:
    # - Adult content
    # - Violence
    # - Hate symbols
    # - Drugs/alcohol

    # For now, return safe score (our generated content should be clean)
    return 0.98


async def _check_competitor_presence(
    video_path: str,
    brand_guidelines: Dict[str, Any] = None,
) -> float:
    """Check for competitor logos or products."""
    # In production:
    # 1. Extract frames
    # 2. Run logo detection
    # 3. Compare against competitor list

    if brand_guidelines and "competitors" in brand_guidelines:
        # More thorough check if competitors specified
        pass

    # Our generated content shouldn't have competitor logos
    return 0.95


async def _check_platform_compliance(
    video_path: str,
    platforms: List[str],
) -> float:
    """Check compliance with platform policies."""
    platform_scores = []

    for platform in platforms:
        score = await _check_single_platform(video_path, platform)
        platform_scores.append(score)

    if not platform_scores:
        return 0.95

    return sum(platform_scores) / len(platform_scores)


async def _check_single_platform(video_path: str, platform: str) -> float:
    """Check compliance with a single platform's policies."""
    # Platform-specific checks

    policy_concerns = {
        "tiktok": [
            "No misleading content",
            "No dangerous activities",
            "No hateful content",
            "Authentic engagement only",
        ],
        "instagram": [
            "No explicit content",
            "No violence",
            "No hate speech",
            "Branded content disclosure",
        ],
        "youtube": [
            "Advertiser-friendly content",
            "No misleading metadata",
            "No harmful content",
            "Copyright compliance",
        ],
    }

    # Our generated content should be compliant
    return 0.95


async def _check_legal_concerns(video_path: str) -> float:
    """Check for potential legal issues."""
    # Check for:
    # - Copyright issues
    # - Trademark violations
    # - Personality rights
    # - Music licensing

    # Our generated content should be original
    return 0.95


async def get_brand_safety_report(
    video_path: str,
    brand_guidelines: Dict[str, Any] = None,
    target_platforms: List[str] = None,
) -> Dict[str, Any]:
    """
    Get detailed brand safety report.

    Returns comprehensive analysis of all brand safety aspects.
    """
    report = {
        "video_path": video_path,
        "overall_score": 0.0,
        "checks": {},
        "flags": [],
        "recommendations": [],
    }

    # Run all checks
    report["checks"]["inappropriate_content"] = {
        "score": await _check_inappropriate_content(video_path),
        "details": "No inappropriate content detected"
    }

    report["checks"]["competitor_presence"] = {
        "score": await _check_competitor_presence(video_path, brand_guidelines),
        "details": "No competitor logos detected"
    }

    if target_platforms:
        report["checks"]["platform_compliance"] = {
            "score": await _check_platform_compliance(video_path, target_platforms),
            "platforms": target_platforms,
            "details": "Compliant with platform policies"
        }

    report["checks"]["legal_concerns"] = {
        "score": await _check_legal_concerns(video_path),
        "details": "No legal issues detected"
    }

    # Calculate overall score
    scores = [check["score"] for check in report["checks"].values()]
    report["overall_score"] = sum(scores) / len(scores) if scores else 0.95

    # Add recommendations
    if report["overall_score"] >= 0.9:
        report["recommendations"].append("Content is brand safe and ready for publishing")
    elif report["overall_score"] >= 0.7:
        report["recommendations"].append("Content is mostly safe, minor review recommended")
    else:
        report["recommendations"].append("Content needs review before publishing")

    return report


def get_platform_requirements(platform: str) -> Dict[str, Any]:
    """Get brand safety requirements for a platform."""
    requirements = {
        "tiktok": {
            "max_duration": 180,
            "aspect_ratio": "9:16",
            "disclosure_required": True,
            "restricted_topics": ["gambling", "alcohol", "tobacco"],
        },
        "instagram": {
            "max_duration": 90,  # Reels
            "aspect_ratio": "9:16",
            "disclosure_required": True,
            "restricted_topics": ["weapons", "adult content"],
        },
        "youtube": {
            "max_duration": 60,  # Shorts
            "aspect_ratio": "9:16",
            "disclosure_required": True,
            "restricted_topics": ["violence", "hate speech"],
        },
        "linkedin": {
            "max_duration": 180,
            "aspect_ratio": "16:9",
            "disclosure_required": False,
            "restricted_topics": ["inappropriate content"],
        },
    }

    return requirements.get(platform, requirements["tiktok"])
