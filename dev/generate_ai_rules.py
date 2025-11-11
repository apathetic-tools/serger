#!/usr/bin/env python3
"""Generate AI rules files from .ai/rules source files.

This script concatenates files from .ai/rules/ to generate:
- .claude/CLAUDE.md (base + claude-specific)
- .cursor/rules/CURSOR.md (base + cursor-specific)
"""

from pathlib import Path


def read_file_content(file_path: Path) -> str:
    """Read file content, returning empty string if file doesn't exist."""
    if file_path.exists():
        return file_path.read_text(encoding="utf-8")
    return ""


def get_sorted_md_files(directory: Path) -> list[Path]:
    """Get all .md files in directory, sorted by name."""
    if not directory.exists():
        return []
    return sorted(directory.glob("*.md"))


def format_header(filename: str) -> str:
    """Format filename as a markdown header."""
    # Remove .md extension
    name = filename.removesuffix(".md")
    # Replace underscores with spaces and capitalize
    header_text = name.replace("_", " ").title()
    return f"# {header_text}\n\n"


def concatenate_files(files: list[Path]) -> str:
    """Concatenate files with headers based on filename."""
    result: list[str] = []
    for file_path in files:
        content = read_file_content(file_path)
        if content.strip():
            # Add header based on filename
            result.append(format_header(file_path.name))
            result.append(content)
            if not content.endswith("\n"):
                result.append("\n")
            result.append("\n")
    return "".join(result)


def main() -> None:
    """Generate AI rules files."""
    project_root = Path(__file__).parent.parent
    ai_rules_dir = project_root / ".ai" / "rules"

    # Ensure directories exist
    ai_rules_dir.mkdir(parents=True, exist_ok=True)
    (ai_rules_dir / "claude").mkdir(parents=True, exist_ok=True)
    (ai_rules_dir / "cursor").mkdir(parents=True, exist_ok=True)

    # Ensure base.md exists (create empty if missing)
    base_file = ai_rules_dir / "base.md"
    if not base_file.exists():
        base_file.write_text("", encoding="utf-8")

    # Read base files (rules/*.md)
    base_files = get_sorted_md_files(ai_rules_dir)
    base_content = concatenate_files(base_files)

    # Read Claude-specific files (rules/claude/*.md)
    claude_dir = ai_rules_dir / "claude"
    claude_files = get_sorted_md_files(claude_dir)
    claude_content = concatenate_files(claude_files)

    # Read Cursor-specific files (rules/cursor/*.md)
    cursor_dir = ai_rules_dir / "cursor"
    cursor_files = get_sorted_md_files(cursor_dir)
    cursor_content = concatenate_files(cursor_files)

    # Generate CLAUDE.md
    claude_output = project_root / ".claude" / "CLAUDE.md"
    claude_output.parent.mkdir(parents=True, exist_ok=True)
    claude_output.write_text(base_content + claude_content, encoding="utf-8")
    print(f"Generated: {claude_output.relative_to(project_root)}")

    # Generate CURSOR.md
    cursor_output = project_root / ".cursor" / "rules" / "CURSOR.md"
    cursor_output.parent.mkdir(parents=True, exist_ok=True)
    cursor_output.write_text(base_content + cursor_content, encoding="utf-8")
    print(f"Generated: {cursor_output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
