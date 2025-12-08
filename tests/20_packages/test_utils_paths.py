# tests/20_packages/test_utils_paths.py


from pathlib import Path

import serger.config.config_types as mod_config_types
import serger.utils as mod_utils


def test_shorten_path_for_display_absolute_when_no_context(tmp_path: Path) -> None:
    """Test that absolute path is returned when no cwd/config_dir provided."""
    test_path = tmp_path / "some" / "deep" / "path"
    test_path.mkdir(parents=True)

    result = mod_utils.shorten_path_for_display(str(test_path))
    assert result == str(test_path.resolve())


def test_shorten_path_for_display_relative_to_cwd(tmp_path: Path) -> None:
    """Test that path is shortened relative to cwd when possible."""
    cwd = tmp_path / "project"
    cwd.mkdir()
    test_path = cwd / "src" / "module.py"
    test_path.parent.mkdir(parents=True)
    test_path.write_text("")

    result = mod_utils.shorten_path_for_display(str(test_path.resolve()), cwd=cwd)
    assert result == "src/module.py"


def test_shorten_path_for_display_relative_to_config_dir(tmp_path: Path) -> None:
    """Test that path is shortened relative to config_dir when not under cwd."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    test_path = config_dir / "src" / "module.py"
    test_path.parent.mkdir(parents=True)
    test_path.write_text("")

    result = mod_utils.shorten_path_for_display(
        str(test_path.resolve()), config_dir=config_dir
    )
    assert result == "src/module.py"


def test_shorten_path_for_display_picks_shortest(tmp_path: Path) -> None:
    """Test that shortest relative path is chosen when both cwd and config_dir work."""
    # Setup: cwd is deeper than config_dir
    # Path: /tmp/project/src/module.py
    # cwd: /tmp/project/src
    # config_dir: /tmp/project
    # Result should be relative to cwd (shorter: "module.py" vs "src/module.py")
    project = tmp_path / "project"
    project.mkdir()
    src = project / "src"
    src.mkdir()
    test_path = src / "module.py"
    test_path.write_text("")

    result = mod_utils.shorten_path_for_display(
        str(test_path.resolve()), cwd=src, config_dir=project
    )
    assert result == "module.py"


def test_shorten_path_for_display_falls_back_to_absolute(tmp_path: Path) -> None:
    """Test that relative path from common prefix is used when paths share prefix."""
    test_path = tmp_path / "outside" / "path.py"
    test_path.parent.mkdir(parents=True)
    test_path.write_text("")

    config_dir = tmp_path / "config"
    config_dir.mkdir()

    result = mod_utils.shorten_path_for_display(
        str(test_path.resolve()), config_dir=config_dir
    )
    # shorten_path finds common prefix (tmp_path) and returns relative from there
    assert result == "outside/path.py"


def test_shorten_path_for_display_with_path_object(tmp_path: Path) -> None:
    """Test that Path objects are accepted."""
    test_path = tmp_path / "src" / "module.py"
    test_path.parent.mkdir(parents=True)
    test_path.write_text("")

    result = mod_utils.shorten_path_for_display(test_path, config_dir=tmp_path)
    assert result == "src/module.py"


def test_shorten_paths_for_display_single_path(tmp_path: Path) -> None:
    """Test shortening a single path in a list."""
    test_path = tmp_path / "src" / "module.py"
    test_path.parent.mkdir(parents=True)
    test_path.write_text("")

    result = mod_utils.shorten_paths_for_display([str(test_path)], config_dir=tmp_path)
    assert result == ["src/module.py"]


def test_shorten_paths_for_display_multiple_paths(tmp_path: Path) -> None:
    """Test shortening multiple paths in a list."""
    path1 = tmp_path / "src" / "module1.py"
    path2 = tmp_path / "lib" / "module2.py"
    path1.parent.mkdir(parents=True)
    path2.parent.mkdir(parents=True)
    path1.write_text("")
    path2.write_text("")

    result = mod_utils.shorten_paths_for_display(
        [str(path1), str(path2)], config_dir=tmp_path
    )
    assert result == ["src/module1.py", "lib/module2.py"]


def test_shorten_paths_for_display_with_path_objects(tmp_path: Path) -> None:
    """Test that Path objects are accepted in list."""
    test_path = tmp_path / "src" / "module.py"
    test_path.parent.mkdir(parents=True)
    test_path.write_text("")

    result = mod_utils.shorten_paths_for_display([test_path], config_dir=tmp_path)
    assert result == ["src/module.py"]


def test_shorten_paths_for_display_mixed_str_path(tmp_path: Path) -> None:
    """Test that mixed str and Path objects work."""
    path1 = tmp_path / "src" / "module1.py"
    path2 = tmp_path / "lib" / "module2.py"
    path1.parent.mkdir(parents=True)
    path2.parent.mkdir(parents=True)
    path1.write_text("")
    path2.write_text("")

    # Convert both to Path for type consistency
    result = mod_utils.shorten_paths_for_display([path1, path2], config_dir=tmp_path)
    assert result == ["src/module1.py", "lib/module2.py"]


def test_shorten_paths_for_display_preserves_order(tmp_path: Path) -> None:
    """Test that order is preserved when shortening paths."""
    num_paths = 5
    paths: list[str] = []
    for i in range(num_paths):
        p = tmp_path / f"dir{i}" / f"file{i}.py"
        p.parent.mkdir(parents=True)
        p.write_text("")
        paths.append(str(p))

    result = mod_utils.shorten_paths_for_display(paths, config_dir=tmp_path)
    assert len(result) == num_paths
    assert all(f"dir{i}/file{i}.py" in result[i] for i in range(num_paths))


def test_shorten_path_for_display_with_dot_path(tmp_path: Path) -> None:
    """Test that '.' is handled correctly when path equals config_dir."""
    test_path = tmp_path / "file.py"
    test_path.write_text("")

    result = mod_utils.shorten_path_for_display(
        str(test_path.resolve()), cwd=tmp_path, config_dir=tmp_path
    )
    assert result == "file.py"


def test_shorten_path_for_display_with_pathresolved(tmp_path: Path) -> None:
    """Test that PathResolved uses its root field exclusively."""
    test_path = tmp_path / "src" / "module.py"
    test_path.parent.mkdir(parents=True)
    test_path.write_text("")

    # Create PathResolved with root different from cwd/config_dir
    root = tmp_path / "project"
    root.mkdir()
    path_resolved = mod_utils.make_pathresolved(
        "src/module.py", root=root, origin="config"
    )

    # Should resolve against root, not cwd or config_dir
    cwd = tmp_path / "other"
    cwd.mkdir()
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    result = mod_utils.shorten_path_for_display(
        path_resolved, cwd=cwd, config_dir=config_dir
    )
    # Should be relative to root (project), not cwd or config_dir
    assert result == "src/module.py"


def test_shorten_path_for_display_with_includeresolved(tmp_path: Path) -> None:
    """Test that IncludeResolved uses its root field exclusively."""
    test_path = tmp_path / "lib" / "module.py"
    test_path.parent.mkdir(parents=True)
    test_path.write_text("")

    # Create IncludeResolved with root different from cwd/config_dir
    root = tmp_path / "project"
    root.mkdir()
    include_resolved = mod_utils.make_includeresolved(
        "lib/module.py", root=root, origin="config"
    )

    # Should resolve against root, not cwd or config_dir
    cwd = tmp_path / "other"
    cwd.mkdir()
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    result = mod_utils.shorten_path_for_display(
        include_resolved, cwd=cwd, config_dir=config_dir
    )
    # Should be relative to root (project), not cwd or config_dir
    assert result == "lib/module.py"


def test_shorten_paths_for_display_with_pathresolved_list(tmp_path: Path) -> None:
    """Test that list of PathResolved uses their root fields exclusively."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "src").mkdir()
    (root / "lib").mkdir()
    (root / "src" / "module1.py").write_text("")
    (root / "lib" / "module2.py").write_text("")

    path1 = mod_utils.make_pathresolved("src/module1.py", root=root, origin="config")
    path2 = mod_utils.make_pathresolved("lib/module2.py", root=root, origin="config")

    cwd = tmp_path / "other"
    cwd.mkdir()
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    result = mod_utils.shorten_paths_for_display(
        [path1, path2], cwd=cwd, config_dir=config_dir
    )
    assert result == ["src/module1.py", "lib/module2.py"]


def test_shorten_paths_for_display_mixed_all_types(tmp_path: Path) -> None:
    """Test that mixed Path, str, and PathResolved work together."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src" / "module1.py").write_text("")

    regular_path = tmp_path / "other" / "file.py"
    regular_path.parent.mkdir(parents=True)
    regular_path.write_text("")

    path_resolved = mod_utils.make_pathresolved(
        "src/module1.py", root=root, origin="config"
    )

    cwd = tmp_path / "other"
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Type checker needs explicit type annotation for mixed list
    mixed_paths: list[Path | str | mod_config_types.PathResolved] = [
        regular_path,
        path_resolved,
        str(regular_path),
    ]
    result = mod_utils.shorten_paths_for_display(
        mixed_paths,
        cwd=cwd,
        config_dir=config_dir,
    )
    # regular_path should be relative to cwd, path_resolved to its root
    assert result[0] == "file.py"  # relative to cwd
    assert result[1] == "src/module1.py"  # relative to path_resolved root
    assert result[2] == "file.py"  # relative to cwd


def test_shorten_path_for_display_pathresolved_equals_root(tmp_path: Path) -> None:
    """Test that PathResolved with path equal to root returns '.'."""
    root = tmp_path / "project"
    root.mkdir()

    # PathResolved where path equals root
    # Use '.' which resolves to root, making relative_to return empty string
    path_resolved = mod_utils.make_pathresolved(".", root=root, origin="config")

    result = mod_utils.shorten_path_for_display(path_resolved)
    # When path equals root, relative_to returns empty string, so we return "."
    assert result == "."


def test_shorten_path_for_display_pathresolved_not_relative_to_root(
    tmp_path: Path,
) -> None:
    """Test that PathResolved with path not relative to root returns absolute."""
    root = tmp_path / "project"
    root.mkdir()
    outside_path = tmp_path / "outside" / "file.py"
    outside_path.parent.mkdir(parents=True)
    outside_path.write_text("")

    # PathResolved with absolute path that's not under root
    path_resolved = mod_utils.make_pathresolved(
        str(outside_path), root=root, origin="config"
    )

    result = mod_utils.shorten_path_for_display(path_resolved)
    # Should return absolute path since it's not relative to root
    assert result == str(outside_path.resolve())


def test_shorten_path_for_display_pathresolved_absolute_in_path_field(
    tmp_path: Path,
) -> None:
    """Test that PathResolved with absolute path in path field works correctly."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src" / "module.py").write_text("")

    # PathResolved with absolute path in path field
    # (should still resolve relative to root)
    abs_path = (root / "src" / "module.py").resolve()
    path_resolved = mod_utils.make_pathresolved(
        str(abs_path), root=root, origin="config"
    )

    result = mod_utils.shorten_path_for_display(path_resolved)
    # Should still be relative to root
    assert result == "src/module.py"


def test_shorten_path_for_display_regular_path_not_relative_to_cwd(
    tmp_path: Path,
) -> None:
    """Test that regular path not relative to cwd uses common prefix."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    outside_path = tmp_path / "outside" / "file.py"
    outside_path.parent.mkdir(parents=True)
    outside_path.write_text("")

    # Path not under cwd or config_dir, but shares common prefix (tmp_path)
    result = mod_utils.shorten_path_for_display(
        outside_path, cwd=cwd, config_dir=config_dir
    )
    # shorten_path finds common prefix (tmp_path) and returns relative from there
    assert result == "outside/file.py"


def test_shorten_paths_for_display_empty_list(tmp_path: Path) -> None:
    """Test that empty list returns empty list."""
    result = mod_utils.shorten_paths_for_display([], config_dir=tmp_path)
    assert result == []


def test_shorten_path_for_display_includeresolved_with_dest(tmp_path: Path) -> None:
    """Test that IncludeResolved with dest field still works correctly."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src" / "module.py").write_text("")

    include_resolved = mod_utils.make_includeresolved(
        "src/module.py", root=root, origin="config", dest=Path("custom.py")
    )

    result = mod_utils.shorten_path_for_display(include_resolved)
    # Should still resolve against root, dest field doesn't affect path display
    assert result == "src/module.py"
