# tests/50_core/test_module_modes.py
"""Unit tests for all module_mode options."""

from tests.utils.build_final_script import call_build_final_script


class TestModuleModeNone:
    """Test module_mode='none' - no shims generated."""

    def test_no_shims_generated(self) -> None:
        """Should not generate any shim code."""
        result, _ = call_build_final_script(module_mode="none")

        assert "# --- import shims for single-file runtime ---" not in result
        assert "_create_pkg_module" not in result
        assert "_setup_pkg_modules" not in result
        assert "sys.modules" not in result or "import sys" in result


class TestModuleModeMulti:
    """Test module_mode='multi' - generate shims for all detected packages."""

    def test_multi_package_shims(self) -> None:
        """Should generate shims for all detected packages."""
        result, _ = call_build_final_script(
            package_name="mypkg",
            order_names=["pkg1.module1", "pkg2.module2"],
            detected_packages={"pkg1", "pkg2", "mypkg"},
            module_mode="multi",
        )

        assert "# --- import shims for single-file runtime ---" in result
        normalized = result.replace("'", '"')
        # Both packages should have shims
        assert '"pkg1.module1"' in normalized
        assert '"pkg2.module2"' in normalized

    def test_single_package_shims(self) -> None:
        """Should generate shims for single package."""
        result, _ = call_build_final_script(
            package_name="mypkg",
            order_names=["utils", "core"],
            detected_packages={"mypkg"},
            module_mode="multi",
        )

        assert "# --- import shims for single-file runtime ---" in result
        normalized = result.replace("'", '"')
        assert '"mypkg.utils"' in normalized
        assert '"mypkg.core"' in normalized


class TestModuleModeForce:
    """Test module_mode='force' - replace root package but keep subpackages."""

    def test_force_replaces_root_keeps_subpackages(self) -> None:
        """Should replace root package but keep subpackages."""
        result, _ = call_build_final_script(
            package_name="mypkg",
            order_names=["pkg1.sub.module1", "pkg2.sub.module2"],
            detected_packages={"pkg1", "pkg2"},
            module_mode="force",
        )

        assert "# --- import shims for single-file runtime ---" in result
        normalized = result.replace("'", '"')
        # Both should become mypkg.sub.module1 and mypkg.sub.module2
        assert '"mypkg.sub.module1"' in normalized
        assert '"mypkg.sub.module2"' in normalized

    def test_force_with_matching_package(self) -> None:
        """Should handle when package matches detected package."""
        result, _ = call_build_final_script(
            package_name="mypkg",
            order_names=["mypkg.utils", "other.sub"],
            detected_packages={"mypkg", "other"},
            module_mode="force",
        )

        normalized = result.replace("'", '"')
        assert '"mypkg.utils"' in normalized
        assert '"mypkg.sub"' in normalized


class TestModuleModeForceFlat:
    """Test module_mode='force_flat' - flatten everything to package."""

    def test_force_flat_flattens_all(self) -> None:
        """Should flatten all modules to direct children of package."""
        result, _ = call_build_final_script(
            package_name="mypkg",
            order_names=["pkg1.sub.module1", "pkg2.sub.module2", "loose"],
            detected_packages={"pkg1", "pkg2"},
            module_mode="force_flat",
        )

        assert "# --- import shims for single-file runtime ---" in result
        normalized = result.replace("'", '"')
        # All should become direct children: mypkg.module1, mypkg.module2, mypkg.loose
        assert '"mypkg.module1"' in normalized
        assert '"mypkg.module2"' in normalized
        assert '"mypkg.loose"' in normalized

    def test_force_flat_with_nested(self) -> None:
        """Should flatten nested packages."""
        result, _ = call_build_final_script(
            package_name="mypkg",
            order_names=["deep.nested.module"],
            detected_packages={"deep"},
            module_mode="force_flat",
        )

        normalized = result.replace("'", '"')
        assert '"mypkg.module"' in normalized


class TestModuleModeUnify:
    """Test module_mode='unify' - place all packages under package, combine if matches."""  # noqa: E501

    def test_unify_combines_matching_package(self) -> None:
        """Should combine when package matches detected package."""
        result, _ = call_build_final_script(
            package_name="serger",
            order_names=["serger.utils", "apathetic_logs.logs"],
            detected_packages={"serger", "apathetic_logs"},
            module_mode="unify",
        )

        normalized = result.replace("'", '"')
        # serger.utils stays as serger.utils (no double prefix)
        assert '"serger.utils"' in normalized
        # apathetic_logs.logs becomes serger.apathetic_logs.logs
        assert '"serger.apathetic_logs.logs"' in normalized

    def test_unify_places_other_packages_under(self) -> None:
        """Should place other detected packages under configured package."""
        result, _ = call_build_final_script(
            package_name="mypkg",
            order_names=["pkg1.module1", "pkg2.module2", "loose"],
            detected_packages={"pkg1", "pkg2"},
            module_mode="unify",
        )

        normalized = result.replace("'", '"')
        assert '"mypkg.pkg1.module1"' in normalized
        assert '"mypkg.pkg2.module2"' in normalized
        assert '"mypkg.loose"' in normalized


class TestModuleModeUnifyPreserve:
    """Test module_mode='unify_preserve' - like unify but preserves structure."""

    def test_unify_preserve_preserves_structure(self) -> None:
        """Should preserve structure when package matches."""
        result, _ = call_build_final_script(
            package_name="serger",
            order_names=["serger.utils.text", "apathetic_logs.logs"],
            detected_packages={"serger", "apathetic_logs"},
            module_mode="unify_preserve",
        )

        normalized = result.replace("'", '"')
        # serger.utils.text stays as serger.utils.text (preserved)
        assert '"serger.utils.text"' in normalized
        # apathetic_logs.logs becomes serger.apathetic_logs.logs
        assert '"serger.apathetic_logs.logs"' in normalized

    def test_unify_preserve_loose_files(self) -> None:
        """Should attach loose files to package."""
        result, _ = call_build_final_script(
            package_name="mypkg",
            order_names=["loose"],
            detected_packages={"mypkg"},
            module_mode="unify_preserve",
        )

        normalized = result.replace("'", '"')
        assert '"mypkg.loose"' in normalized


class TestModuleModeFlat:
    """Test module_mode='flat' - loose files as top-level modules."""

    def test_flat_keeps_loose_files_top_level(self) -> None:
        """Should keep loose files as top-level modules."""
        result, _ = call_build_final_script(
            package_name="mypkg",
            order_names=["main", "utils", "pkg1.module1"],
            detected_packages={"pkg1"},
            module_mode="flat",
        )

        normalized = result.replace("'", '"')
        # Loose files stay as top-level
        assert '"main"' in normalized
        assert '"utils"' in normalized
        # Packages still get package prefix
        assert '"mypkg.pkg1.module1"' in normalized or '"pkg1.module1"' in normalized

    def test_flat_with_only_loose_files(self) -> None:
        """Should handle only loose files."""
        result, _ = call_build_final_script(
            package_name="mypkg",
            order_names=["main", "utils"],
            detected_packages={"mypkg"},
            module_mode="flat",
        )

        normalized = result.replace("'", '"')
        assert '"main"' in normalized
        assert '"utils"' in normalized
