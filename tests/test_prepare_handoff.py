import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PreparationTests(unittest.TestCase):
    def module(self):
        path = ROOT / "scripts/prepare_handoff.py"
        self.assertTrue(path.exists(), "non-destructive dataset preparation is missing")
        spec = importlib.util.spec_from_file_location("prepare_handoff", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_missing_source_does_not_create_partial_dataset(self):
        mod = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "raw"
            source.mkdir()
            (source / "A_demo.hdf5").write_bytes(b"example")
            with self.assertRaises(FileNotFoundError):
                mod.prepare_dataset(source, root / "prepared", ["A", "B"], "copy")
            self.assertFalse((root / "prepared").exists())

    def test_copy_keeps_original_and_rejects_overwrite(self):
        mod = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "raw"
            source.mkdir()
            (source / "A_demo.hdf5").write_bytes(b"example")
            mod.prepare_dataset(source, root / "prepared", ["A"], "copy")
            self.assertEqual((source / "A_demo.hdf5").read_bytes(), b"example")
            self.assertEqual((root / "prepared/A_demo.hdf5").read_bytes(), b"example")
            with self.assertRaises(FileExistsError):
                mod.prepare_dataset(source, root / "prepared", ["A"], "copy")

    def test_benchmark_names_come_from_actual_44_task_registry(self):
        mod = self.module()
        names = mod.boss_names(ROOT)
        self.assertEqual(len(names), 44)
        self.assertEqual(names[2], "KITCHEN_SCENE1_open_the_bottom_drawer_of_the_cabinet")


if __name__ == "__main__":
    unittest.main()
