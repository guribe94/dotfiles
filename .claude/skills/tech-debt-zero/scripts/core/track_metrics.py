#!/usr/bin/env python3
"""
Tech Debt Metrics Tracker.
Tracks debt over time and generates trend analysis.
"""

import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass
class DebtSnapshot:
    """A point-in-time snapshot of tech debt."""
    timestamp: str
    project_path: str
    total_findings: int
    by_severity: dict[str, int]
    by_category: dict[str, int]
    roi_score: float  # Average ROI of all findings


@dataclass
class TrendData:
    """Trend analysis data."""
    period_start: str
    period_end: str
    total_change: int  # Positive = debt increased
    severity_changes: dict[str, int]
    category_changes: dict[str, int]
    velocity: float  # Findings per day
    burn_down_estimate: str | None  # Estimated time to zero debt


class MetricsTracker:
    """Track and analyze tech debt metrics over time."""

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            db_path = Path.home() / ".tech-debt-metrics.db"
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                project_path TEXT NOT NULL,
                total_findings INTEGER NOT NULL,
                by_severity TEXT NOT NULL,
                by_category TEXT NOT NULL,
                roi_score REAL NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS findings_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                finding_id TEXT NOT NULL,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                file_path TEXT,
                status TEXT DEFAULT 'open',
                FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_project
            ON snapshots(project_path, timestamp)
        """)

        conn.commit()
        conn.close()

    def record_snapshot(
        self,
        project_path: str,
        findings: list[dict],
        prioritized: list[dict] | None = None,
    ) -> int:
        """Record a new debt snapshot."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Calculate aggregates
        by_severity: dict[str, int] = {}
        by_category: dict[str, int] = {}

        for f in findings:
            sev = f.get("severity", "unknown")
            cat = f.get("category", "unknown")
            by_severity[sev] = by_severity.get(sev, 0) + 1
            by_category[cat] = by_category.get(cat, 0) + 1

        # Calculate average ROI if prioritized data available
        roi_score = 0.0
        if prioritized:
            roi_values = [p.get("roi", {}).get("score", 0) for p in prioritized]
            if roi_values:
                roi_score = sum(roi_values) / len(roi_values)

        # Insert snapshot
        cursor.execute("""
            INSERT INTO snapshots (timestamp, project_path, total_findings, by_severity, by_category, roi_score)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat() + "Z",
            project_path,
            len(findings),
            json.dumps(by_severity),
            json.dumps(by_category),
            roi_score,
        ))

        snapshot_id = cursor.lastrowid

        # Insert individual findings
        for f in findings:
            cursor.execute("""
                INSERT INTO findings_history (snapshot_id, finding_id, category, severity, title, file_path)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                snapshot_id,
                f.get("id", "unknown"),
                f.get("category", "unknown"),
                f.get("severity", "unknown"),
                f.get("title", "Untitled"),
                f.get("file_path"),
            ))

        conn.commit()
        conn.close()

        return snapshot_id

    def get_snapshots(
        self,
        project_path: str,
        days: int = 30,
    ) -> list[DebtSnapshot]:
        """Get snapshots for a project within the specified time range."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"

        cursor.execute("""
            SELECT timestamp, project_path, total_findings, by_severity, by_category, roi_score
            FROM snapshots
            WHERE project_path = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        """, (project_path, cutoff))

        snapshots = []
        for row in cursor.fetchall():
            snapshots.append(DebtSnapshot(
                timestamp=row[0],
                project_path=row[1],
                total_findings=row[2],
                by_severity=json.loads(row[3]),
                by_category=json.loads(row[4]),
                roi_score=row[5],
            ))

        conn.close()
        return snapshots

    def calculate_trend(
        self,
        project_path: str,
        days: int = 30,
    ) -> TrendData | None:
        """Calculate trend data for a project."""
        snapshots = self.get_snapshots(project_path, days)

        if len(snapshots) < 2:
            return None

        first = snapshots[0]
        last = snapshots[-1]

        # Calculate changes
        total_change = last.total_findings - first.total_findings

        severity_changes = {}
        for sev in set(list(first.by_severity.keys()) + list(last.by_severity.keys())):
            severity_changes[sev] = last.by_severity.get(sev, 0) - first.by_severity.get(sev, 0)

        category_changes = {}
        for cat in set(list(first.by_category.keys()) + list(last.by_category.keys())):
            category_changes[cat] = last.by_category.get(cat, 0) - first.by_category.get(cat, 0)

        # Calculate velocity (findings per day)
        first_time = datetime.fromisoformat(first.timestamp.replace("Z", "+00:00"))
        last_time = datetime.fromisoformat(last.timestamp.replace("Z", "+00:00"))
        days_elapsed = max((last_time - first_time).days, 1)
        velocity = total_change / days_elapsed

        # Estimate burn-down time
        burn_down_estimate = None
        if velocity < 0 and last.total_findings > 0:
            days_to_zero = int(last.total_findings / abs(velocity))
            burn_down_estimate = f"{days_to_zero} days"

        return TrendData(
            period_start=first.timestamp,
            period_end=last.timestamp,
            total_change=total_change,
            severity_changes=severity_changes,
            category_changes=category_changes,
            velocity=velocity,
            burn_down_estimate=burn_down_estimate,
        )

    def get_resolved_findings(
        self,
        project_path: str,
        days: int = 30,
    ) -> list[dict]:
        """Get findings that were resolved in the time period."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"

        # Get finding IDs from first snapshot in period
        cursor.execute("""
            SELECT fh.finding_id, fh.category, fh.severity, fh.title
            FROM findings_history fh
            JOIN snapshots s ON fh.snapshot_id = s.id
            WHERE s.project_path = ? AND s.timestamp >= ?
            ORDER BY s.timestamp ASC
            LIMIT 1000
        """, (project_path, cutoff))

        first_findings = {row[0]: {"id": row[0], "category": row[1], "severity": row[2], "title": row[3]}
                         for row in cursor.fetchall()}

        # Get finding IDs from last snapshot
        cursor.execute("""
            SELECT fh.finding_id
            FROM findings_history fh
            JOIN snapshots s ON fh.snapshot_id = s.id
            WHERE s.project_path = ?
            ORDER BY s.timestamp DESC
            LIMIT 1000
        """, (project_path,))

        last_finding_ids = {row[0] for row in cursor.fetchall()}

        conn.close()

        # Resolved = in first but not in last
        resolved = [f for f_id, f in first_findings.items() if f_id not in last_finding_ids]
        return resolved

    def get_new_findings(
        self,
        project_path: str,
        days: int = 30,
    ) -> list[dict]:
        """Get findings that were introduced in the time period."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"

        # Get finding IDs from first snapshot in period
        cursor.execute("""
            SELECT fh.finding_id
            FROM findings_history fh
            JOIN snapshots s ON fh.snapshot_id = s.id
            WHERE s.project_path = ? AND s.timestamp >= ?
            ORDER BY s.timestamp ASC
            LIMIT 1000
        """, (project_path, cutoff))

        first_finding_ids = {row[0] for row in cursor.fetchall()}

        # Get findings from last snapshot
        cursor.execute("""
            SELECT fh.finding_id, fh.category, fh.severity, fh.title
            FROM findings_history fh
            JOIN snapshots s ON fh.snapshot_id = s.id
            WHERE s.project_path = ?
            ORDER BY s.timestamp DESC
            LIMIT 1000
        """, (project_path,))

        last_findings = {row[0]: {"id": row[0], "category": row[1], "severity": row[2], "title": row[3]}
                        for row in cursor.fetchall()}

        conn.close()

        # New = in last but not in first
        new = [f for f_id, f in last_findings.items() if f_id not in first_finding_ids]
        return new


def format_trend_text(
    project_path: str,
    trend: TrendData | None,
    resolved: list[dict],
    new: list[dict],
) -> str:
    """Format trend data as text."""
    lines = [
        "=" * 60,
        "TECH DEBT TREND REPORT",
        "=" * 60,
        f"Project: {project_path}",
    ]

    if not trend:
        lines.extend([
            "",
            "Not enough data for trend analysis.",
            "Run at least 2 audits to see trends.",
        ])
        return "\n".join(lines)

    lines.extend([
        f"Period: {trend.period_start[:10]} to {trend.period_end[:10]}",
        "",
        "OVERALL TREND",
        "-" * 40,
    ])

    if trend.total_change > 0:
        lines.append(f"  Debt INCREASED by {trend.total_change} findings")
    elif trend.total_change < 0:
        lines.append(f"  Debt DECREASED by {abs(trend.total_change)} findings")
    else:
        lines.append("  Debt unchanged")

    lines.append(f"  Velocity: {trend.velocity:+.1f} findings/day")

    if trend.burn_down_estimate:
        lines.append(f"  Estimated time to zero debt: {trend.burn_down_estimate}")

    # Severity changes
    lines.extend([
        "",
        "BY SEVERITY",
        "-" * 40,
    ])

    for sev in ["critical", "high", "medium", "low", "info"]:
        change = trend.severity_changes.get(sev, 0)
        if change != 0:
            lines.append(f"  {sev.upper()}: {change:+d}")

    # Category changes (top movers)
    lines.extend([
        "",
        "TOP CATEGORY CHANGES",
        "-" * 40,
    ])

    sorted_cats = sorted(trend.category_changes.items(), key=lambda x: abs(x[1]), reverse=True)
    for cat, change in sorted_cats[:5]:
        if change != 0:
            lines.append(f"  {cat}: {change:+d}")

    # Recently resolved
    if resolved:
        lines.extend([
            "",
            f"RESOLVED ({len(resolved)})",
            "-" * 40,
        ])
        for f in resolved[:10]:
            lines.append(f"  [{f['severity']}] {f['title'][:50]}")
        if len(resolved) > 10:
            lines.append(f"  ... and {len(resolved) - 10} more")

    # New findings
    if new:
        lines.extend([
            "",
            f"NEW ({len(new)})",
            "-" * 40,
        ])
        for f in new[:10]:
            lines.append(f"  [{f['severity']}] {f['title'][:50]}")
        if len(new) > 10:
            lines.append(f"  ... and {len(new) - 10} more")

    return "\n".join(lines)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Tech Debt Metrics Tracking")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Record command
    record_parser = subparsers.add_parser("record", help="Record a new snapshot")
    record_parser.add_argument("input", help="JSON file with audit results")
    record_parser.add_argument("--project", required=True, help="Project path identifier")

    # Trend command
    trend_parser = subparsers.add_parser("trend", help="Show trend analysis")
    trend_parser.add_argument("--project", required=True, help="Project path identifier")
    trend_parser.add_argument("--days", type=int, default=30, help="Days to analyze")
    trend_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # History command
    history_parser = subparsers.add_parser("history", help="Show snapshot history")
    history_parser.add_argument("--project", required=True, help="Project path identifier")
    history_parser.add_argument("--days", type=int, default=30, help="Days to show")
    history_parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    tracker = MetricsTracker()

    if args.command == "record":
        with open(args.input) as f:
            data = json.load(f)

        findings = data.get("findings", []) if isinstance(data, dict) else data
        prioritized = data.get("prioritized") if isinstance(data, dict) else None

        snapshot_id = tracker.record_snapshot(args.project, findings, prioritized)
        print(f"Recorded snapshot {snapshot_id} with {len(findings)} findings")

    elif args.command == "trend":
        trend = tracker.calculate_trend(args.project, args.days)
        resolved = tracker.get_resolved_findings(args.project, args.days)
        new = tracker.get_new_findings(args.project, args.days)

        if args.json:
            output = {
                "trend": {
                    "period_start": trend.period_start if trend else None,
                    "period_end": trend.period_end if trend else None,
                    "total_change": trend.total_change if trend else 0,
                    "velocity": trend.velocity if trend else 0,
                    "burn_down_estimate": trend.burn_down_estimate if trend else None,
                    "severity_changes": trend.severity_changes if trend else {},
                    "category_changes": trend.category_changes if trend else {},
                } if trend else None,
                "resolved": resolved,
                "new": new,
            }
            print(json.dumps(output, indent=2))
        else:
            print(format_trend_text(args.project, trend, resolved, new))

    elif args.command == "history":
        snapshots = tracker.get_snapshots(args.project, args.days)

        if args.json:
            print(json.dumps([
                {
                    "timestamp": s.timestamp,
                    "total_findings": s.total_findings,
                    "by_severity": s.by_severity,
                    "by_category": s.by_category,
                    "roi_score": s.roi_score,
                }
                for s in snapshots
            ], indent=2))
        else:
            print(f"Snapshot history for {args.project}")
            print("-" * 60)
            for s in snapshots:
                print(f"{s.timestamp[:19]}  Total: {s.total_findings}  "
                      f"Critical: {s.by_severity.get('critical', 0)}  "
                      f"High: {s.by_severity.get('high', 0)}")


if __name__ == "__main__":
    main()
