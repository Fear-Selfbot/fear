import unittest


class SdkIntegrationTests(unittest.TestCase):
    def test_system_module_imports_with_locked_sdk_contract(self):
        from modules.system.main import SystemModule

        self.assertEqual(SystemModule.name, "System")


if __name__ == "__main__":
    unittest.main()
