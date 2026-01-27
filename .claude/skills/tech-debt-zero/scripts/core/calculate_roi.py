#!/usr/bin/env python3
"""
ROI Calculator for Tech Debt Prioritization.
Calculates impact × urgency / effort for prioritized remediation.
"""

import json
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class EffortSize(Enum):
    XS = "xs"  # 0-2 hours
    S = "s"    # 2-4 hours
    M = "m"    # 4-16 hours
    L = "l"    # 16-40 hours
    XL = "xl"  # 40-80 hours
    XXL = "xxl"  # 80+ hours


@dataclass
class ImpactFactors:
    """Factors for calculating impact score."""
    exploitability: int = 5  # 1-10: How easily can this be exploited?
    data_sensitivity: int = 5  # 1-10: What data is at risk?
    blast_radius: int = 5  # 1-10: How many users/systems affected?
    compliance: int = 2  # 1-10: Regulatory/audit implications?
    availability: int = 2  # 1-10: Service reliability impact?
    velocity: int = 2  # 1-10: Impact on dev productivity?


@dataclass
class PrioritizedFinding:
    """A finding with calculated ROI."""
    id: str
    category: str
    severity: str
    title: str
    description: str
    file_path: str | None
    line_number: int | None

    # ROI components
    impact_score: float
    urgency_multiplier: float
    effort_score: float
    effort_size: str
    roi: float

    # Factors
    factors: ImpactFactors

    # Categorization
    priority_category: str  # critical, quick_win, high_value, standard, defer

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "roi": {
                "impact": round(self.impact_score, 2),
                "urgency": round(self.urgency_multiplier, 2),
                "effort": round(self.effort_score, 2),
                "effort_size": self.effort_size,
                "score": round(self.roi, 2),
            },
            "priority_category": self.priority_category,
            "factors": {
                "exploitability": self.factors.exploitability,
                "data_sensitivity": self.factors.data_sensitivity,
                "blast_radius": self.factors.blast_radius,
                "compliance": self.factors.compliance,
                "availability": self.factors.availability,
                "velocity": self.factors.velocity,
            },
        }


class ROICalculator:
    """Calculate ROI for tech debt findings."""

    # Impact factor weights
    WEIGHTS = {
        "exploitability": 0.25,
        "data_sensitivity": 0.25,
        "blast_radius": 0.20,
        "compliance": 0.15,
        "availability": 0.10,
        "velocity": 0.05,
    }

    # Effort size to score mapping
    EFFORT_SCORES = {
        EffortSize.XS: 1,
        EffortSize.S: 2,
        EffortSize.M: 4,
        EffortSize.L: 7,
        EffortSize.XL: 9,
        EffortSize.XXL: 10,
    }

    # Category-based default factors
    CATEGORY_DEFAULTS = {
        # Security - high exploitability and data sensitivity
        "injection": ImpactFactors(exploitability=9, data_sensitivity=8, blast_radius=8, compliance=7),
        "crypto": ImpactFactors(exploitability=6, data_sensitivity=9, blast_radius=7, compliance=8),
        "session": ImpactFactors(exploitability=7, data_sensitivity=7, blast_radius=6, compliance=5),
        "auth": ImpactFactors(exploitability=8, data_sensitivity=8, blast_radius=8, compliance=7),
        "headers": ImpactFactors(exploitability=5, data_sensitivity=4, blast_radius=6, compliance=3),
        "supply_chain": ImpactFactors(exploitability=7, data_sensitivity=6, blast_radius=9, compliance=6),
        "secrets": ImpactFactors(exploitability=8, data_sensitivity=10, blast_radius=8, compliance=8),
        "privacy": ImpactFactors(exploitability=5, data_sensitivity=9, blast_radius=7, compliance=9),
        "infra_security": ImpactFactors(exploitability=6, data_sensitivity=7, blast_radius=9, compliance=7),

        # Operational - high availability impact
        "observability": ImpactFactors(exploitability=2, data_sensitivity=2, blast_radius=5, compliance=2, availability=6, velocity=5),
        "resilience": ImpactFactors(exploitability=3, data_sensitivity=2, blast_radius=7, compliance=2, availability=9, velocity=4),
        "deployment": ImpactFactors(exploitability=2, data_sensitivity=2, blast_radius=6, compliance=2, availability=7, velocity=6),
        "config": ImpactFactors(exploitability=4, data_sensitivity=3, blast_radius=5, compliance=3, availability=5, velocity=4),
        "slo": ImpactFactors(exploitability=2, data_sensitivity=2, blast_radius=5, compliance=4, availability=7, velocity=3),
        "alerting": ImpactFactors(exploitability=2, data_sensitivity=2, blast_radius=4, compliance=3, availability=6, velocity=4),
        "runbooks": ImpactFactors(exploitability=2, data_sensitivity=2, blast_radius=3, compliance=3, availability=5, velocity=5),
        "build": ImpactFactors(exploitability=2, data_sensitivity=2, blast_radius=4, compliance=2, availability=3, velocity=7),
        "rate_limits": ImpactFactors(exploitability=6, data_sensitivity=3, blast_radius=7, compliance=3, availability=7, velocity=2),

        # Architecture - high velocity impact
        "solid": ImpactFactors(exploitability=2, data_sensitivity=2, blast_radius=4, compliance=2, availability=2, velocity=7),
        "coupling": ImpactFactors(exploitability=2, data_sensitivity=2, blast_radius=5, compliance=2, availability=3, velocity=8),
        "antipatterns": ImpactFactors(exploitability=2, data_sensitivity=2, blast_radius=4, compliance=2, availability=2, velocity=6),
        "domain": ImpactFactors(exploitability=2, data_sensitivity=2, blast_radius=4, compliance=2, availability=2, velocity=6),
        "api_contract": ImpactFactors(exploitability=3, data_sensitivity=3, blast_radius=6, compliance=3, availability=4, velocity=5),
        "schema": ImpactFactors(exploitability=2, data_sensitivity=4, blast_radius=5, compliance=3, availability=5, velocity=5),
        "distributed": ImpactFactors(exploitability=3, data_sensitivity=3, blast_radius=6, compliance=2, availability=7, velocity=6),
        "events": ImpactFactors(exploitability=2, data_sensitivity=3, blast_radius=5, compliance=2, availability=6, velocity=5),
        "legacy": ImpactFactors(exploitability=3, data_sensitivity=3, blast_radius=4, compliance=3, availability=4, velocity=6),
    }

    # Severity to urgency multiplier
    URGENCY_MULTIPLIERS = {
        Severity.CRITICAL: 2.0,
        Severity.HIGH: 1.5,
        Severity.MEDIUM: 1.2,
        Severity.LOW: 1.0,
        Severity.INFO: 0.8,
    }

    def calculate_impact(self, factors: ImpactFactors) -> float:
        """Calculate weighted impact score."""
        total = 0
        total += factors.exploitability * self.WEIGHTS["exploitability"]
        total += factors.data_sensitivity * self.WEIGHTS["data_sensitivity"]
        total += factors.blast_radius * self.WEIGHTS["blast_radius"]
        total += factors.compliance * self.WEIGHTS["compliance"]
        total += factors.availability * self.WEIGHTS["availability"]
        total += factors.velocity * self.WEIGHTS["velocity"]
        return total

    def estimate_effort(self, finding: dict) -> tuple[EffortSize, float]:
        """Estimate effort based on finding characteristics."""
        category = finding.get("category", "")
        severity = finding.get("severity", "medium")

        # Default effort by category type
        if category in ("injection", "secrets", "headers"):
            # Usually quick fixes
            size = EffortSize.S
        elif category in ("auth", "session", "rate_limits"):
            # Medium complexity
            size = EffortSize.M
        elif category in ("coupling", "solid", "antipatterns", "domain"):
            # Refactoring takes time
            size = EffortSize.L
        elif category in ("distributed", "events", "legacy"):
            # Complex changes
            size = EffortSize.XL
        else:
            # Default to medium
            size = EffortSize.M

        # Adjust based on explicit effort_hours if provided
        effort_hours = finding.get("effort_hours")
        if effort_hours:
            if effort_hours <= 2:
                size = EffortSize.XS
            elif effort_hours <= 4:
                size = EffortSize.S
            elif effort_hours <= 16:
                size = EffortSize.M
            elif effort_hours <= 40:
                size = EffortSize.L
            elif effort_hours <= 80:
                size = EffortSize.XL
            else:
                size = EffortSize.XXL

        return size, self.EFFORT_SCORES[size]

    def calculate_urgency(self, finding: dict) -> float:
        """Calculate urgency multiplier."""
        severity_str = finding.get("severity", "medium")
        try:
            severity = Severity(severity_str)
        except ValueError:
            severity = Severity.MEDIUM

        base_urgency = self.URGENCY_MULTIPLIERS[severity]

        # Additional urgency factors
        tags = finding.get("tags", [])
        if "active_exploit" in tags:
            base_urgency = 2.0
        if "compliance_deadline" in tags:
            base_urgency = max(base_urgency, 1.8)
        if "audit_finding" in tags:
            base_urgency = max(base_urgency, 1.5)

        return base_urgency

    def get_factors(self, finding: dict) -> ImpactFactors:
        """Get impact factors for a finding."""
        category = finding.get("category", "")

        # Use category defaults as base
        base_factors = self.CATEGORY_DEFAULTS.get(category, ImpactFactors())

        # Override with explicit metadata if provided
        metadata = finding.get("metadata", {})
        return ImpactFactors(
            exploitability=metadata.get("exploitability", base_factors.exploitability),
            data_sensitivity=metadata.get("data_sensitivity", base_factors.data_sensitivity),
            blast_radius=metadata.get("blast_radius", base_factors.blast_radius),
            compliance=metadata.get("compliance", base_factors.compliance),
            availability=metadata.get("availability", base_factors.availability),
            velocity=metadata.get("velocity", base_factors.velocity),
        )

    def categorize_priority(self, finding: dict, roi: float) -> str:
        """Categorize finding based on severity and ROI."""
        severity = finding.get("severity", "medium")

        # Critical severity always gets top priority
        if severity == "critical":
            return "critical"

        # ROI-based categories
        if roi > 5.0:
            return "quick_win"
        elif roi > 2.0:
            return "high_value"
        elif roi > 1.0:
            return "standard"
        else:
            return "defer"

    def prioritize(self, findings: list[dict]) -> list[PrioritizedFinding]:
        """Calculate ROI and prioritize findings."""
        prioritized = []

        for finding in findings:
            factors = self.get_factors(finding)
            impact = self.calculate_impact(factors)
            urgency = self.calculate_urgency(finding)
            effort_size, effort_score = self.estimate_effort(finding)

            roi = (impact * urgency) / effort_score if effort_score > 0 else 0
            priority_category = self.categorize_priority(finding, roi)

            prioritized.append(PrioritizedFinding(
                id=finding.get("id", "unknown"),
                category=finding.get("category", "unknown"),
                severity=finding.get("severity", "medium"),
                title=finding.get("title", "Untitled"),
                description=finding.get("description", ""),
                file_path=finding.get("file_path"),
                line_number=finding.get("line_number"),
                impact_score=impact,
                urgency_multiplier=urgency,
                effort_score=effort_score,
                effort_size=effort_size.value,
                roi=roi,
                factors=factors,
                priority_category=priority_category,
            ))

        # Sort by: priority category, then ROI descending
        category_order = {"critical": 0, "quick_win": 1, "high_value": 2, "standard": 3, "defer": 4}
        prioritized.sort(key=lambda f: (category_order.get(f.priority_category, 5), -f.roi))

        return prioritized


def format_prioritized_text(findings: list[PrioritizedFinding]) -> str:
    """Format prioritized findings as text."""
    lines = [
        "=" * 70,
        "TECH DEBT PRIORITIZATION REPORT",
        "=" * 70,
        "",
    ]

    # Group by priority category
    categories = {}
    for f in findings:
        categories.setdefault(f.priority_category, []).append(f)

    category_names = {
        "critical": "CRITICAL (Address Immediately)",
        "quick_win": "QUICK WINS (ROI > 5.0)",
        "high_value": "HIGH VALUE (ROI 2.0-5.0)",
        "standard": "STANDARD (ROI 1.0-2.0)",
        "defer": "DEFER (ROI < 1.0)",
    }

    for cat_key in ["critical", "quick_win", "high_value", "standard", "defer"]:
        cat_findings = categories.get(cat_key, [])
        if not cat_findings:
            continue

        lines.extend([
            "",
            f"### {category_names[cat_key]}",
            "",
            f"{'#':<4} {'ID':<20} {'Category':<15} {'ROI':>6} {'Effort':>6} {'Title'}",
            "-" * 70,
        ])

        for i, f in enumerate(cat_findings, 1):
            lines.append(
                f"{i:<4} {f.id:<20} {f.category:<15} {f.roi:>6.1f} {f.effort_size:>6} {f.title[:40]}"
            )

    lines.extend([
        "",
        "=" * 70,
        "ROI = (Impact × Urgency) / Effort",
        "Higher ROI = Higher priority for remediation",
    ])

    return "\n".join(lines)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Tech Debt ROI Prioritization")
    parser.add_argument("input", nargs="?", help="JSON file with findings (or stdin)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--top", type=int, help="Show only top N findings")
    parser.add_argument(
        "--category",
        choices=["critical", "quick_win", "high_value", "standard", "defer"],
        help="Filter by priority category",
    )

    args = parser.parse_args()

    # Read input
    if args.input:
        with open(args.input) as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    # Handle both raw findings list and audit report format
    if isinstance(data, list):
        findings = data
    elif isinstance(data, dict) and "findings" in data:
        findings = data["findings"]
    else:
        print("Error: Invalid input format", file=sys.stderr)
        sys.exit(1)

    # Calculate ROI
    calculator = ROICalculator()
    prioritized = calculator.prioritize(findings)

    # Filter
    if args.category:
        prioritized = [f for f in prioritized if f.priority_category == args.category]

    if args.top:
        prioritized = prioritized[:args.top]

    # Output
    if args.json:
        print(json.dumps([f.to_dict() for f in prioritized], indent=2))
    else:
        print(format_prioritized_text(prioritized))


if __name__ == "__main__":
    main()
