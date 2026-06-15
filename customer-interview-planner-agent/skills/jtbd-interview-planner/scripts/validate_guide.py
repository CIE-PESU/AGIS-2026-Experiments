#!/usr/bin/env python3
"""
JTBD Interview Planner - Guide Validator

Checks interview questions for common anti-patterns that compromise research quality.
Detects: leading questions, double-barrels, hypotheticals, closed questions, jargon, 
confirmation bias, and other issues.

Usage:
    python validate_guide.py guide.md
    python validate_guide.py guide.md --fix  # Output corrected version
    python validate_guide.py guide.md --json # Output structured results
"""

import argparse
import re
import json
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum


class Severity(Enum):
    CRITICAL = "critical"  # Must fix
    WARNING = "warning"    # Should fix
    NOTE = "note"          # Consider fixing


@dataclass
class Issue:
    """A detected issue in a question."""
    question: str
    line_number: int
    issue_type: str
    severity: Severity
    description: str
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Complete validation results."""
    file_path: str
    total_questions: int
    questions_with_issues: int
    critical_count: int
    warning_count: int
    note_count: int
    issues: list[Issue] = field(default_factory=list)
    passed: bool = False


# ============================================================================
# DETECTION PATTERNS
# ============================================================================

LEADING_PATTERNS = [
    (r'\bwould you say\b', "Suggests expected answer"),
    (r"\bdon't you think\b", "Suggests expected answer"),
    (r"\bisn't it\b", "Suggests expected answer"),
    (r"\bwouldn't you\b", "Suggests expected answer"),
    (r"\bwould you agree\b", "Asks for agreement"),
    (r'\bhow much do you (?:love|like|enjoy)\b', "Assumes positive sentiment"),
    (r'\bhow (?:frustrating|annoying|difficult|hard|confusing|painful)\b', "Assumes negative experience"),
    (r'\bhow (?:helpful|useful|great|easy|simple)\b', "Assumes positive experience"),
    (r'\bobviously\b', "Contains assumption"),
    (r'\bclearly\b', "Contains assumption"),
    (r'\bright\?\s*$', "Seeks confirmation"),
    (r'\bcorrect\?\s*$', "Seeks confirmation"),
    (r'\byou (?:must|probably|definitely)\b', "Contains assumption about participant"),
]

DOUBLE_BARREL_PATTERNS = [
    (r'\?[^?]+\?', "Multiple question marks detected"),
    (r'\band\s+(?:what|how|why|when|where|did|do|would|will)\b', "Two questions joined with 'and'"),
    (r'\bor\s+(?:what|how|why|when|where|did|do|would|will)\b', "Two questions joined with 'or'"),
]

HYPOTHETICAL_PATTERNS = [
    (r'^would you\b', "Hypothetical - asks about future behavior"),
    (r'^will you\b', "Hypothetical - asks about future behavior"),
    (r'^could you see yourself\b', "Hypothetical - asks about imagined future"),
    (r'\bdo you think you would\b', "Hypothetical - asks about predicted behavior"),
    (r'\bif we (?:built|added|created|made)\b', "Hypothetical - asks about unreleased feature"),
    (r'\bhow likely (?:are|would) you\b', "Hypothetical - asks about probability"),
    (r'\bcan you imagine\b', "Hypothetical - asks about imagination"),
    (r'\bin the future\b', "Hypothetical - asks about future"),
    (r'\bwould you (?:buy|pay|use|recommend|switch)\b', "Hypothetical - predicting future action"),
]

CLOSED_PATTERNS = [
    (r'^did you\b', "Closed yes/no question"),
    (r'^do you\b', "Closed yes/no question"),
    (r'^is it\b', "Closed yes/no question"),
    (r'^are you\b', "Closed yes/no question"),
    (r'^was it\b', "Closed yes/no question"),
    (r'^were you\b', "Closed yes/no question"),
    (r'^have you\b', "Closed yes/no question"),
    (r'^has it\b', "Closed yes/no question"),
    (r'^can you\b(?!.*(?:tell|walk|describe|explain))', "Closed yes/no question"),
]

JARGON_PATTERNS = [
    (r'\b(?:API|SDK|UI|UX|CRM|ERP|SaaS|B2B|B2C|ROI|KPI)\b', "Technical acronym - may need explanation"),
    (r'\bdashboard\b', "Product jargon - consider 'where you check...'"),
    (r'\bworkflow\b', "Business jargon - consider 'how you do...'"),
    (r'\bintegration\b', "Technical jargon - consider 'connecting to...'"),
    (r'\bonboarding\b', "Industry jargon - consider 'getting started'"),
    (r'\bstakeholder\b', "Business jargon - consider 'people involved'"),
    (r'\bleverage\b', "Business jargon - consider simpler word"),
    (r'\bsynergy\b', "Business jargon - avoid"),
    (r'\bthe (?:new )?(?:feature|update|version)\b', "Vague product reference - be specific or let them name it"),
]

CONFIRMATION_BIAS_PATTERNS = [
    (r'\bsince (?:it|you|the|this) (?:is|was|were|are)\b', "Assumes a condition is true"),
    (r'\bgiven that\b', "Pre-frames with assumption"),
    (r'\bwe (?:think|believe|heard|know)\b', "Leads with researcher's belief"),
    (r'\ba lot of (?:people|users|customers) say\b', "Social proof pressure"),
    (r'\bour data shows\b', "Pre-frames with data"),
    (r'\bwhen you (?:struggled|failed|had trouble|got confused)\b', "Assumes negative experience happened"),
]

MULTIPLE_CHOICE_PATTERNS = [
    (r'\bwas it [\w\s]+,\s*[\w\s]+,?\s*or\b', "Provides options - let them answer freely"),
    (r'\bdid you feel [\w\s]+ or [\w\s]+\?', "Provides emotion options - ask openly"),
    (r'\bwhich (?:matters|is) more\b', "Forces ranking - explore both first"),
    (r'\bwould you describe it as [\w\s]+,?\s*[\w\s]+,?\s*or\b', "Provides description options"),
]

COMPOUND_PATTERNS = [
    (r'^so,?\s+(?:given|since|because|as)\b', "Long preamble before question"),
    (r'[.!]\s+(?:so|and|but)\s+(?:what|how|why|when)', "Statement followed by question - separate them"),
]


# ============================================================================
# DETECTION LOGIC
# ============================================================================

def is_question(line: str) -> bool:
    """Check if a line is likely a question."""
    line = line.strip()
    if not line:
        return False
    # Has question mark
    if '?' in line:
        return True
    # Starts with question word
    question_starters = ['what', 'how', 'why', 'when', 'where', 'who', 'which', 
                         'tell', 'describe', 'walk', 'explain', 'can you']
    line_lower = line.lower()
    return any(line_lower.startswith(starter) for starter in question_starters)


def extract_questions(content: str) -> list[tuple[int, str]]:
    """Extract questions from guide content with line numbers."""
    questions = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        # Skip markdown headers, list markers for non-questions
        cleaned = re.sub(r'^[\s*\->#\d.]+', '', line).strip()
        if is_question(cleaned):
            questions.append((i, cleaned))
    
    return questions


def check_patterns(question: str, patterns: list[tuple], 
                   issue_type: str, severity: Severity) -> list[Issue]:
    """Check a question against a list of patterns."""
    issues = []
    question_lower = question.lower()
    
    for pattern, description in patterns:
        if re.search(pattern, question_lower, re.IGNORECASE):
            issues.append(Issue(
                question=question,
                line_number=0,  # Will be filled in later
                issue_type=issue_type,
                severity=severity,
                description=description,
            ))
            break  # One issue per pattern category
    
    return issues


def validate_question(question: str, line_number: int) -> list[Issue]:
    """Validate a single question for all anti-patterns."""
    issues = []
    
    # Check each pattern category
    checks = [
        (LEADING_PATTERNS, "Leading Question", Severity.CRITICAL),
        (CONFIRMATION_BIAS_PATTERNS, "Confirmation Bias", Severity.CRITICAL),
        (DOUBLE_BARREL_PATTERNS, "Double-Barreled", Severity.WARNING),
        (HYPOTHETICAL_PATTERNS, "Hypothetical", Severity.WARNING),
        (CLOSED_PATTERNS, "Closed Question", Severity.WARNING),
        (JARGON_PATTERNS, "Jargon", Severity.NOTE),
        (MULTIPLE_CHOICE_PATTERNS, "Multiple Choice", Severity.WARNING),
        (COMPOUND_PATTERNS, "Compound/Preamble", Severity.NOTE),
    ]
    
    for patterns, issue_type, severity in checks:
        found = check_patterns(question, patterns, issue_type, severity)
        for issue in found:
            issue.line_number = line_number
        issues.extend(found)
    
    return issues


def add_suggestions(issues: list[Issue]) -> list[Issue]:
    """Add fix suggestions to issues."""
    suggestion_map = {
        "Leading Question": "Reframe as open question: 'How would you describe...' or 'What was your experience with...'",
        "Confirmation Bias": "Remove assumption. Ask neutrally: 'What happened when...' or 'Tell me about...'",
        "Double-Barreled": "Split into two separate questions. Ask one thing at a time.",
        "Hypothetical": "Reframe to past behavior: 'Tell me about a time when...' or 'When was the last time you...'",
        "Closed Question": "Convert to open: Start with 'How...', 'What...', 'Tell me about...', or 'Walk me through...'",
        "Jargon": "Consider using participant's language or simpler terms. Flag for researcher review.",
        "Multiple Choice": "Remove options. Let participant generate their own description.",
        "Compound/Preamble": "Ask the question directly without lengthy setup.",
    }
    
    for issue in issues:
        if issue.issue_type in suggestion_map:
            issue.suggestion = suggestion_map[issue.issue_type]
    
    return issues


# ============================================================================
# MAIN VALIDATION
# ============================================================================

def validate_guide(file_path: str) -> ValidationResult:
    """Validate an interview guide file."""
    path = Path(file_path)
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    questions = extract_questions(content)
    
    result = ValidationResult(
        file_path=str(path),
        total_questions=len(questions),
        questions_with_issues=0,
        critical_count=0,
        warning_count=0,
        note_count=0,
    )
    
    questions_flagged = set()
    
    for line_num, question in questions:
        issues = validate_question(question, line_num)
        issues = add_suggestions(issues)
        
        for issue in issues:
            result.issues.append(issue)
            questions_flagged.add(line_num)
            
            if issue.severity == Severity.CRITICAL:
                result.critical_count += 1
            elif issue.severity == Severity.WARNING:
                result.warning_count += 1
            else:
                result.note_count += 1
    
    result.questions_with_issues = len(questions_flagged)
    result.passed = result.critical_count == 0
    
    return result


def format_result_text(result: ValidationResult) -> str:
    """Format validation result as readable text."""
    lines = []
    lines.append("=" * 60)
    lines.append("JTBD INTERVIEW PLANNER - VALIDATION REPORT")
    lines.append("=" * 60)
    lines.append(f"File: {result.file_path}")
    lines.append(f"Total questions found: {result.total_questions}")
    lines.append(f"Questions with issues: {result.questions_with_issues}")
    lines.append("")
    
    if result.passed:
        lines.append("✅ PASSED - No critical issues found")
    else:
        lines.append("❌ FAILED - Critical issues must be fixed")
    
    lines.append("")
    lines.append(f"  🔴 Critical: {result.critical_count}")
    lines.append(f"  🟡 Warning:  {result.warning_count}")
    lines.append(f"  🟢 Note:     {result.note_count}")
    lines.append("")
    
    if result.issues:
        lines.append("-" * 60)
        lines.append("ISSUES FOUND")
        lines.append("-" * 60)
        
        # Group by severity
        for severity in [Severity.CRITICAL, Severity.WARNING, Severity.NOTE]:
            severity_issues = [i for i in result.issues if i.severity == severity]
            if not severity_issues:
                continue
            
            icon = {"critical": "🔴", "warning": "🟡", "note": "🟢"}[severity.value]
            lines.append(f"\n{icon} {severity.value.upper()} ISSUES:\n")
            
            for issue in severity_issues:
                lines.append(f"Line {issue.line_number}: {issue.issue_type}")
                lines.append(f"  Question: \"{issue.question[:80]}{'...' if len(issue.question) > 80 else ''}\"")
                lines.append(f"  Problem: {issue.description}")
                if issue.suggestion:
                    lines.append(f"  Fix: {issue.suggestion}")
                lines.append("")
    
    return "\n".join(lines)


def format_result_json(result: ValidationResult) -> str:
    """Format validation result as JSON."""
    data = {
        "file_path": result.file_path,
        "total_questions": result.total_questions,
        "questions_with_issues": result.questions_with_issues,
        "passed": result.passed,
        "counts": {
            "critical": result.critical_count,
            "warning": result.warning_count,
            "note": result.note_count,
        },
        "issues": [
            {
                "line_number": i.line_number,
                "question": i.question,
                "issue_type": i.issue_type,
                "severity": i.severity.value,
                "description": i.description,
                "suggestion": i.suggestion,
            }
            for i in result.issues
        ]
    }
    return json.dumps(data, indent=2)


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Validate JTBD interview guide for question anti-patterns.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate_guide.py guide.md
  python validate_guide.py guide.md --json
  python validate_guide.py guide.md --strict  # Exit 1 on any warning
        """
    )
    
    parser.add_argument('file', help='Interview guide file to validate')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--strict', action='store_true', 
                        help='Fail on warnings too, not just critical')
    
    args = parser.parse_args()
    
    if not Path(args.file).exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    
    result = validate_guide(args.file)
    
    if args.json:
        print(format_result_json(result))
    else:
        print(format_result_text(result))
    
    # Exit code
    if args.strict:
        sys.exit(0 if result.critical_count == 0 and result.warning_count == 0 else 1)
    else:
        sys.exit(0 if result.passed else 1)


if __name__ == '__main__':
    main()
