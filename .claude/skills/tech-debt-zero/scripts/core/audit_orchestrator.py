#!/usr/bin/env python3
"""
Tech Debt Audit Orchestrator.
Coordinates all 27 category analyzers and produces unified reports.
"""

import asyncio
import importlib.util
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Category(Enum):
    # Security (1-9)
    INJECTION = "injection"
    CRYPTO = "crypto"
    SESSION = "session"
    AUTH = "auth"
    HEADERS = "headers"
    SUPPLY_CHAIN = "supply_chain"
    SECRETS = "secrets"
    PRIVACY = "privacy"
    INFRA_SECURITY = "infra_security"

    # Operational (10-18)
    OBSERVABILITY = "observability"
    RESILIENCE = "resilience"
    DEPLOYMENT = "deployment"
    CONFIG = "config"
    SLO = "slo"
    ALERTING = "alerting"
    RUNBOOKS = "runbooks"
    BUILD = "build"
    RATE_LIMITS = "rate_limits"

    # Architecture (19-27)
    SOLID = "solid"
    COUPLING = "coupling"
    ANTIPATTERNS = "antipatterns"
    DOMAIN = "domain"
    API_CONTRACT = "api_contract"
    SCHEMA = "schema"
    DISTRIBUTED = "distributed"
    EVENTS = "events"
    LEGACY = "legacy"


@dataclass
class Finding:
    """A single tech debt finding."""
    id: str
    category: Category
    severity: Severity
    title: str
    description: str
    file_path: str | None = None
    line_number: int | None = None
    code_snippet: str | None = None
    remediation: str | None = None
    cwe_id: str | None = None
    owasp_id: str | None = None
    effort_hours: float | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "code_snippet": self.code_snippet,
            "remediation": self.remediation,
            "cwe_id": self.cwe_id,
            "owasp_id": self.owasp_id,
            "effort_hours": self.effort_hours,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class AnalyzerResult:
    """Result from a single analyzer."""
    category: Category
    findings: list[Finding]
    duration_ms: float
    error: str | None = None


@dataclass
class AuditReport:
    """Complete audit report."""
    timestamp: str
    project_path: str
    total_findings: int
    findings_by_severity: dict[str, int]
    findings_by_category: dict[str, int]
    findings: list[Finding]
    analyzer_results: list[AnalyzerResult]
    total_duration_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "project_path": self.project_path,
            "summary": {
                "total_findings": self.total_findings,
                "by_severity": self.findings_by_severity,
                "by_category": self.findings_by_category,
            },
            "findings": [f.to_dict() for f in self.findings],
            "performance": {
                "total_duration_ms": self.total_duration_ms,
                "analyzers": [
                    {
                        "category": r.category.value,
                        "duration_ms": r.duration_ms,
                        "findings_count": len(r.findings),
                        "error": r.error,
                    }
                    for r in self.analyzer_results
                ],
            },
        }


class BaseAnalyzer:
    """Base class for all analyzers."""

    category: Category

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.findings: list[Finding] = []
        self._finding_counter = 0

    def create_finding(
        self,
        severity: Severity,
        title: str,
        description: str,
        **kwargs,
    ) -> Finding:
        self._finding_counter += 1
        return Finding(
            id=f"{self.category.value}-{self._finding_counter:04d}",
            category=self.category,
            severity=severity,
            title=title,
            description=description,
            **kwargs,
        )

    async def analyze(self) -> list[Finding]:
        """Override in subclass to perform analysis."""
        raise NotImplementedError


class AuditOrchestrator:
    """Orchestrates all tech debt analyzers."""

    # Map categories to their analyzer module names
    ANALYZER_MAP = {
        # Security
        Category.INJECTION: "analyze_injection",
        Category.CRYPTO: "analyze_crypto",
        Category.SESSION: "analyze_session",
        Category.AUTH: "analyze_auth",
        Category.HEADERS: "analyze_headers",
        Category.SUPPLY_CHAIN: "analyze_supply_chain",
        Category.SECRETS: "analyze_secrets",
        Category.PRIVACY: "analyze_privacy",
        Category.INFRA_SECURITY: "analyze_infra_security",
        # Operational
        Category.OBSERVABILITY: "analyze_observability",
        Category.RESILIENCE: "analyze_resilience",
        Category.DEPLOYMENT: "analyze_deployment",
        Category.CONFIG: "analyze_config",
        Category.SLO: "analyze_slo",
        Category.ALERTING: "analyze_alerting",
        Category.RUNBOOKS: "analyze_runbooks",
        Category.BUILD: "analyze_build",
        Category.RATE_LIMITS: "analyze_rate_limits",
        # Architecture
        Category.SOLID: "analyze_solid",
        Category.COUPLING: "analyze_coupling",
        Category.ANTIPATTERNS: "analyze_antipatterns",
        Category.DOMAIN: "analyze_domain",
        Category.API_CONTRACT: "analyze_api_contract",
        Category.SCHEMA: "analyze_schema",
        Category.DISTRIBUTED: "analyze_distributed",
        Category.EVENTS: "analyze_events",
        Category.LEGACY: "analyze_legacy",
    }

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.analyzers_path = Path(__file__).parent.parent / "analyzers"

    def _load_analyzer(self, category: Category) -> type[BaseAnalyzer] | None:
        """Dynamically load an analyzer module."""
        module_name = self.ANALYZER_MAP.get(category)
        if not module_name:
            return None

        module_path = self.analyzers_path / f"{module_name}.py"
        if not module_path.exists():
            return None

        try:
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # Analyzer class should be named like InjectionAnalyzer, CryptoAnalyzer, etc.
                class_name = "".join(word.title() for word in module_name.replace("analyze_", "").split("_")) + "Analyzer"
                return getattr(module, class_name, None)
        except Exception as e:
            print(f"Error loading analyzer {module_name}: {e}", file=sys.stderr)
            return None

    async def run_analyzer(self, category: Category) -> AnalyzerResult:
        """Run a single analyzer."""
        start_time = time.time()

        analyzer_class = self._load_analyzer(category)
        if not analyzer_class:
            return AnalyzerResult(
                category=category,
                findings=[],
                duration_ms=0,
                error=f"Analyzer not found for {category.value}",
            )

        try:
            analyzer = analyzer_class(self.project_path)
            findings = await analyzer.analyze()
            duration_ms = (time.time() - start_time) * 1000

            return AnalyzerResult(
                category=category,
                findings=findings,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return AnalyzerResult(
                category=category,
                findings=[],
                duration_ms=duration_ms,
                error=str(e),
            )

    async def run_all(
        self,
        categories: list[Category] | None = None,
        parallel: bool = True,
    ) -> AuditReport:
        """Run all or specified analyzers."""
        start_time = time.time()
        categories = categories or list(Category)

        if parallel:
            tasks = [self.run_analyzer(cat) for cat in categories]
            results = await asyncio.gather(*tasks)
        else:
            results = []
            for cat in categories:
                result = await self.run_analyzer(cat)
                results.append(result)

        # Aggregate findings
        all_findings = []
        for result in results:
            all_findings.extend(result.findings)

        # Calculate summaries
        findings_by_severity = {}
        findings_by_category = {}

        for finding in all_findings:
            sev = finding.severity.value
            cat = finding.category.value
            findings_by_severity[sev] = findings_by_severity.get(sev, 0) + 1
            findings_by_category[cat] = findings_by_category.get(cat, 0) + 1

        total_duration_ms = (time.time() - start_time) * 1000

        return AuditReport(
            timestamp=datetime.utcnow().isoformat() + "Z",
            project_path=str(self.project_path),
            total_findings=len(all_findings),
            findings_by_severity=findings_by_severity,
            findings_by_category=findings_by_category,
            findings=all_findings,
            analyzer_results=list(results),
            total_duration_ms=total_duration_ms,
        )


def format_report_text(report: AuditReport) -> str:
    """Format report as human-readable text."""
    lines = [
        "=" * 60,
        "TECH DEBT AUDIT REPORT",
        "=" * 60,
        f"Project: {report.project_path}",
        f"Timestamp: {report.timestamp}",
        f"Total Findings: {report.total_findings}",
        "",
        "SUMMARY BY SEVERITY",
        "-" * 40,
    ]

    severity_order = ["critical", "high", "medium", "low", "info"]
    for sev in severity_order:
        count = report.findings_by_severity.get(sev, 0)
        if count > 0:
            lines.append(f"  {sev.upper()}: {count}")

    lines.extend([
        "",
        "SUMMARY BY CATEGORY",
        "-" * 40,
    ])

    for cat, count in sorted(report.findings_by_category.items()):
        lines.append(f"  {cat}: {count}")

    # Group findings by severity
    lines.extend([
        "",
        "FINDINGS",
        "=" * 60,
    ])

    for sev in severity_order:
        sev_findings = [f for f in report.findings if f.severity.value == sev]
        if not sev_findings:
            continue

        lines.extend([
            "",
            f"--- {sev.upper()} ({len(sev_findings)}) ---",
        ])

        for finding in sev_findings:
            lines.extend([
                "",
                f"[{finding.id}] {finding.title}",
                f"  Category: {finding.category.value}",
            ])
            if finding.file_path:
                loc = finding.file_path
                if finding.line_number:
                    loc += f":{finding.line_number}"
                lines.append(f"  Location: {loc}")
            lines.append(f"  {finding.description}")
            if finding.remediation:
                lines.append(f"  Fix: {finding.remediation}")

    lines.extend([
        "",
        "=" * 60,
        f"Analysis completed in {report.total_duration_ms:.0f}ms",
    ])

    return "\n".join(lines)


async def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Tech Debt Audit")
    parser.add_argument("path", nargs="?", default=".", help="Project path to audit")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--category",
        action="append",
        help="Specific category to analyze (can repeat)",
    )
    parser.add_argument(
        "--severity",
        choices=["critical", "high", "medium", "low", "info"],
        help="Minimum severity to report",
    )
    parser.add_argument(
        "--fail-on",
        choices=["critical", "high", "medium", "low"],
        help="Exit with error if findings at this severity or above",
    )
    parser.add_argument("--sequential", action="store_true", help="Run analyzers sequentially")

    args = parser.parse_args()
    project_path = Path(args.path).resolve()

    if not project_path.exists():
        print(f"Error: Path does not exist: {project_path}", file=sys.stderr)
        sys.exit(1)

    # Parse categories
    categories = None
    if args.category:
        try:
            categories = [Category(c) for c in args.category]
        except ValueError as e:
            print(f"Error: Invalid category: {e}", file=sys.stderr)
            sys.exit(1)

    # Run audit
    orchestrator = AuditOrchestrator(project_path)
    report = await orchestrator.run_all(
        categories=categories,
        parallel=not args.sequential,
    )

    # Filter by severity if specified
    if args.severity:
        severity_order = ["critical", "high", "medium", "low", "info"]
        min_index = severity_order.index(args.severity)
        report.findings = [
            f for f in report.findings
            if severity_order.index(f.severity.value) <= min_index
        ]
        report.total_findings = len(report.findings)

    # Output
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(format_report_text(report))

    # Exit code based on findings
    if args.fail_on:
        severity_order = ["critical", "high", "medium", "low"]
        fail_index = severity_order.index(args.fail_on)
        for finding in report.findings:
            if finding.severity.value in severity_order[:fail_index + 1]:
                sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
