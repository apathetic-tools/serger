#!/usr/bin/env python3
"""Generate AI rules files from .ai/rules source files.

This script processes files from .ai/rules/ to generate:
- .cursor/rules/*.mdc (base .mdc files + cursor-specific .mdc files, copied as-is)
- .cursor/commands/*.md (commands from .ai/commands/, copied as-is)
- .claude/CLAUDE.md (base .mdc files + claude-specific .md files, stitched with headers)

The script also removes any old files from .cursor/rules/ and .cursor/commands/
that are no longer present in the source directories.
"""

import re
import shutil
from pathlib import Path


def read_file_content(file_path: Path) -> str:
    """Read file content, returning empty string if file doesn't exist."""
    if file_path.exists():
        return file_path.read_text(encoding="utf-8")
    return ""


def get_sorted_files(directory: Path, extension: str) -> list[Path]:
    """Get all files with given extension in directory, sorted by name."""
    if not directory.exists():
        return []
    return sorted(directory.glob(f"*.{extension}"))


def extract_mdc_content(mdc_content: str) -> str:
    """Extract content from .mdc file, removing frontmatter."""
    # Match YAML frontmatter between --- markers
    frontmatter_pattern = r"^---\s*\n(?:.*?\n)*?---\s*\n"
    content = re.sub(frontmatter_pattern, "", mdc_content, flags=re.MULTILINE)
    return content.strip()


def format_header(filename: str) -> str:
    """Format filename as a markdown header."""
    # Remove .mdc or .md extension
    name = filename.removesuffix(".mdc").removesuffix(".md")
    # Replace underscores with spaces and capitalize
    header_text = name.replace("_", " ").title()
    return f"# {header_text}\n\n"


def concatenate_mdc_files_for_claude(files: list[Path]) -> str:
    """Concatenate .mdc files with headers, extracting content."""
    result: list[str] = []
    for file_path in files:
        content = read_file_content(file_path)
        if content.strip():
            # Extract content without frontmatter
            extracted = extract_mdc_content(content)
            if extracted:
                # Add header based on filename
                result.append(format_header(file_path.name))
                result.append(extracted)
                if not extracted.endswith("\n"):
                    result.append("\n")
                result.append("\n")
    return "".join(result)


def concatenate_md_files(files: list[Path]) -> str:
    """Concatenate .md files with headers based on filename."""
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
    ai_commands_dir = project_root / ".ai" / "commands"
    cursor_rules_dir = project_root / ".cursor" / "rules"
    cursor_commands_dir = project_root / ".cursor" / "commands"
    claude_dir = project_root / ".claude"

    # Ensure directories exist
    ai_rules_dir.mkdir(parents=True, exist_ok=True)
    (ai_rules_dir / "claude").mkdir(parents=True, exist_ok=True)
    (ai_rules_dir / "cursor").mkdir(parents=True, exist_ok=True)
    ai_commands_dir.mkdir(parents=True, exist_ok=True)
    cursor_rules_dir.mkdir(parents=True, exist_ok=True)
    cursor_commands_dir.mkdir(parents=True, exist_ok=True)
    claude_dir.mkdir(parents=True, exist_ok=True)

    # Track files we create to clean up old ones later
    created_rules_files: set[Path] = set()
    created_commands_files: set[Path] = set()

    # Get base .mdc files (rules/*.mdc)
    base_mdc_files = get_sorted_files(ai_rules_dir, "mdc")

    # Copy base .mdc files to .cursor/rules/ as-is
    for mdc_file in base_mdc_files:
        dest_file = cursor_rules_dir / mdc_file.name
        shutil.copy2(mdc_file, dest_file)
        created_rules_files.add(dest_file)
        print(
            f"Copied: {mdc_file.relative_to(project_root)}"
            f" -> {dest_file.relative_to(project_root)}"
        )

    # Get cursor-specific .mdc files (rules/cursor/*.mdc)
    cursor_specific_dir = ai_rules_dir / "cursor"
    cursor_mdc_files = get_sorted_files(cursor_specific_dir, "mdc")

    # Copy cursor-specific .mdc files to .cursor/rules/ as-is
    for mdc_file in cursor_mdc_files:
        dest_file = cursor_rules_dir / mdc_file.name
        shutil.copy2(mdc_file, dest_file)
        created_rules_files.add(dest_file)
        print(
            f"Copied: {mdc_file.relative_to(project_root)}"
            f" -> {dest_file.relative_to(project_root)}",
        )

    # Copy command files from .ai/commands/ to .cursor/commands/
    if ai_commands_dir.exists():
        command_files = get_sorted_files(ai_commands_dir, "md")
        for cmd_file in command_files:
            dest_file = cursor_commands_dir / cmd_file.name
            shutil.copy2(cmd_file, dest_file)
            created_commands_files.add(dest_file)
            print(
                f"Copied: {cmd_file.relative_to(project_root)}"
                f" -> {dest_file.relative_to(project_root)}"
            )

    # Remove old files from .cursor/rules/ that are no longer in source
    if cursor_rules_dir.exists():
        existing_rules = set(cursor_rules_dir.glob("*.mdc"))
        old_rules = existing_rules - created_rules_files
        for old_file in old_rules:
            old_file.unlink()
            print(f"Removed old file: {old_file.relative_to(project_root)}")

    # Remove old files from .cursor/commands/ that are no longer in source
    if cursor_commands_dir.exists():
        existing_commands = set(cursor_commands_dir.glob("*.md"))
        old_commands = existing_commands - created_commands_files
        for old_file in old_commands:
            old_file.unlink()
            print(f"Removed old file: {old_file.relative_to(project_root)}")

    # Generate CLAUDE.md from base .mdc files (extracting content)
    base_content = concatenate_mdc_files_for_claude(base_mdc_files)

    # Read Claude-specific .md files (rules/claude/*.md)
    claude_specific_dir = ai_rules_dir / "claude"
    claude_md_files = get_sorted_files(claude_specific_dir, "md")
    claude_content = concatenate_md_files(claude_md_files)

    # Generate CLAUDE.md
    claude_output = claude_dir / "CLAUDE.md"
    claude_output.write_text(base_content + claude_content, encoding="utf-8")
    print(f"Generated: {claude_output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
