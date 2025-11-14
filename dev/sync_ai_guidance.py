#!/usr/bin/env python3
"""Sync AI guidance files from .ai/rules and .ai/commands source files.

This script processes files from .ai/rules/ and .ai/commands/ to generate:
- .cursor/rules/*.mdc (base .mdc files + cursor-specific .mdc files, copied as-is)
- .cursor/commands/*.md (commands from .ai/commands/, copied as-is)
- .claude/CLAUDE.md (base .mdc files + claude-specific .md files, stitched with headers)

The script also removes any old files from .cursor/rules/ and .cursor/commands/
that are no longer present in the source directories.
"""

import argparse
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


def ensure_directories(
    ai_rules_dir: Path,
    ai_commands_dir: Path,
    cursor_rules_dir: Path,
    cursor_commands_dir: Path,
    claude_dir: Path,
) -> None:
    """Ensure all required directories exist."""
    ai_rules_dir.mkdir(parents=True, exist_ok=True)
    (ai_rules_dir / "claude").mkdir(parents=True, exist_ok=True)
    (ai_rules_dir / "cursor").mkdir(parents=True, exist_ok=True)
    ai_commands_dir.mkdir(parents=True, exist_ok=True)
    cursor_rules_dir.mkdir(parents=True, exist_ok=True)
    cursor_commands_dir.mkdir(parents=True, exist_ok=True)
    claude_dir.mkdir(parents=True, exist_ok=True)


def copy_file_with_log(
    source: Path,
    dest: Path,
    project_root: Path,
    *,
    quiet: bool,
) -> None:
    """Copy a file and optionally log the operation."""
    shutil.copy2(source, dest)
    if not quiet:
        print(
            f"Copied: {source.relative_to(project_root)}"
            f" -> {dest.relative_to(project_root)}"
        )


def copy_base_mdc_files(
    ai_rules_dir: Path,
    cursor_rules_dir: Path,
    project_root: Path,
    *,
    quiet: bool,
) -> set[Path]:
    """Copy base .mdc files to .cursor/rules/ and return set of created files."""
    created_files: set[Path] = set()
    base_mdc_files = get_sorted_files(ai_rules_dir, "mdc")
    for mdc_file in base_mdc_files:
        dest_file = cursor_rules_dir / mdc_file.name
        copy_file_with_log(mdc_file, dest_file, project_root, quiet=quiet)
        created_files.add(dest_file)
    return created_files


def copy_cursor_mdc_files(
    ai_rules_dir: Path,
    cursor_rules_dir: Path,
    project_root: Path,
    *,
    quiet: bool,
) -> set[Path]:
    """Copy cursor-specific .mdc files and return set of created files."""
    created_files: set[Path] = set()
    cursor_specific_dir = ai_rules_dir / "cursor"
    cursor_mdc_files = get_sorted_files(cursor_specific_dir, "mdc")
    for mdc_file in cursor_mdc_files:
        dest_file = cursor_rules_dir / mdc_file.name
        copy_file_with_log(mdc_file, dest_file, project_root, quiet=quiet)
        created_files.add(dest_file)
    return created_files


def copy_command_files(
    ai_commands_dir: Path,
    cursor_commands_dir: Path,
    project_root: Path,
    *,
    quiet: bool,
) -> set[Path]:
    """Copy command files and return set of created files."""
    created_files: set[Path] = set()
    if ai_commands_dir.exists():
        command_files = get_sorted_files(ai_commands_dir, "md")
        for cmd_file in command_files:
            dest_file = cursor_commands_dir / cmd_file.name
            copy_file_with_log(cmd_file, dest_file, project_root, quiet=quiet)
            created_files.add(dest_file)
    return created_files


def remove_old_files(
    target_dir: Path,
    created_files: set[Path],
    extension: str,
    project_root: Path,
    *,
    quiet: bool,
) -> None:
    """Remove old files from target directory that are not in created_files."""
    if target_dir.exists():
        existing_files = set(target_dir.glob(f"*.{extension}"))
        old_files = existing_files - created_files
        for old_file in old_files:
            old_file.unlink()
            if not quiet:
                print(f"Removed old file: {old_file.relative_to(project_root)}")


def generate_claude_file(
    ai_rules_dir: Path,
    claude_dir: Path,
    base_mdc_files: list[Path],
    project_root: Path,
    *,
    quiet: bool,
) -> None:
    """Generate CLAUDE.md from base and claude-specific files."""
    base_content = concatenate_mdc_files_for_claude(base_mdc_files)
    claude_specific_dir = ai_rules_dir / "claude"
    claude_md_files = get_sorted_files(claude_specific_dir, "md")
    claude_content = concatenate_md_files(claude_md_files)
    claude_output = claude_dir / "CLAUDE.md"
    claude_output.write_text(base_content + claude_content, encoding="utf-8")
    if not quiet:
        print(f"Generated: {claude_output.relative_to(project_root)}")


def main() -> None:
    """Sync AI guidance files."""
    parser = argparse.ArgumentParser(
        description="Sync AI guidance files from .ai/rules and .ai/commands"
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress output messages",
    )
    args = parser.parse_args()
    quiet = args.quiet

    project_root = Path(__file__).parent.parent
    ai_rules_dir = project_root / ".ai" / "rules"
    ai_commands_dir = project_root / ".ai" / "commands"
    cursor_rules_dir = project_root / ".cursor" / "rules"
    cursor_commands_dir = project_root / ".cursor" / "commands"
    claude_dir = project_root / ".claude"

    ensure_directories(
        ai_rules_dir,
        ai_commands_dir,
        cursor_rules_dir,
        cursor_commands_dir,
        claude_dir,
    )

    base_mdc_files = get_sorted_files(ai_rules_dir, "mdc")
    created_rules_files = copy_base_mdc_files(
        ai_rules_dir, cursor_rules_dir, project_root, quiet=quiet
    )
    created_rules_files.update(
        copy_cursor_mdc_files(ai_rules_dir, cursor_rules_dir, project_root, quiet=quiet)
    )
    created_commands_files = copy_command_files(
        ai_commands_dir, cursor_commands_dir, project_root, quiet=quiet
    )

    remove_old_files(
        cursor_rules_dir, created_rules_files, "mdc", project_root, quiet=quiet
    )
    remove_old_files(
        cursor_commands_dir,
        created_commands_files,
        "md",
        project_root,
        quiet=quiet,
    )

    generate_claude_file(
        ai_rules_dir, claude_dir, base_mdc_files, project_root, quiet=quiet
    )


if __name__ == "__main__":
    main()
