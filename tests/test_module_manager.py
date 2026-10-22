import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from src.core.module.manager import ModuleInstallError, ModuleManager, Package


def make_archive(module_id: str = "sample", version: str = "1.0.0") -> bytes:
    content = io.BytesIO()
    with zipfile.ZipFile(content, "w") as archive:
        archive.writestr(
            "fear-module.json",
            json.dumps({"id": module_id, "version": version}),
        )
        archive.writestr("main.py", "from fear_module import FearModule\n")
    return content.getvalue()


class ModuleManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.manager = ModuleManager(root / "modules", root / ".data")
        self.archive = make_archive()
        self.package = Package(
            "sample", "1.0.0", "packages/sample.zip", hashlib.sha256(self.archive).hexdigest()
        )
        self.registry = patch.object(
            self.manager, "_registry", return_value={"sample": self.package}
        )
        self.fetch = patch.object(self.manager, "_fetch", return_value=self.archive)
        self.dependencies = patch.object(self.manager, "_install_dependencies")
        self.registry.start()
        self.fetch.start()
        self.dependencies.start()

    def tearDown(self):
        patch.stopall()
        self.temp_dir.cleanup()

    def test_install_and_commit_writes_package_and_state(self):
        self.manager.install("sample")
        self.manager.commit("sample")

        self.assertTrue((self.manager.modules_dir / "sample" / "main.py").is_file())
        self.assertEqual(self.manager.installed(), {"sample": "1.0.0"})

    def test_failed_activation_can_restore_previous_install(self):
        self.manager.install("sample")
        self.manager.commit("sample")
        previous_main = self.manager.modules_dir / "sample" / "main.py"
        previous_main.write_text("# old module version\n", encoding="utf-8")
        previous_manifest = self.manager.modules_dir / "sample" / "fear-module.json"
        previous_manifest.write_text(
            json.dumps({"id": "sample", "version": "0.9.0"}), encoding="utf-8"
        )
        self.manager._write_state({"sample": "0.9.0"})

        self.manager.install("sample", update=True)
        self.manager.rollback("sample")

        self.assertEqual(previous_main.read_text(encoding="utf-8"), "# old module version\n")
        self.assertEqual(self.manager.installed(), {"sample": "0.9.0"})

    def test_archive_path_traversal_is_rejected(self):
        malicious = io.BytesIO()
        with zipfile.ZipFile(malicious, "w") as archive:
            archive.writestr("../outside.py", "bad = True")
        data = malicious.getvalue()
        package = Package(
            "sample", "1.0.0", "packages/sample.zip", hashlib.sha256(data).hexdigest()
        )

        with tempfile.TemporaryDirectory() as destination:
            with self.assertRaisesRegex(ModuleInstallError, "небезопасный путь"):
                self.manager._safe_extract(data, Path(destination), package)


if __name__ == "__main__":
    unittest.main()
