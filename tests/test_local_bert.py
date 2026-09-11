"""Exercise the real BERT loading functions without importing the GPU stack."""
import ast
import os
from pathlib import Path
from types import SimpleNamespace as NS
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
FILES = ("config.json", "pytorch_model.bin", "tokenizer_config.json", "tokenizer.json", "vocab.txt")


class LocalBertTests(unittest.TestCase):
    def functions(self):
        path = ROOT / "libero/lifelong/utils.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name in ("get_bert_directory", "get_task_embs")]
        namespace = dict(Path=Path, os=os, __file__=str(path), logging=Mock(),
                         AutoTokenizer=Mock(), AutoModel=Mock(), to_absolute_path=lambda p: p)
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
        return namespace

    def test_missing_local_directory_is_explicit(self):
        ns = self.functions()
        self.assertIn("get_bert_directory", ns, "Local model path validation is missing")
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"BOSS_BERT_PATH": tmp}):
            with self.assertRaisesRegex(FileNotFoundError, "pytorch_model.bin"):
                ns["get_bert_directory"]()

    def test_default_location_is_project_relative(self):
        ns = self.functions()
        self.assertIn("get_bert_directory", ns)
        with patch.dict(os.environ, {}, clear=True), patch.object(Path, "is_file", return_value=True):
            self.assertEqual(ns["get_bert_directory"](), ROOT / "bert/bert-base-cased")

    def test_bert_and_one_hot_load_local_files_only(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"BOSS_BERT_PATH": tmp}):
            for name in FILES:
                (Path(tmp) / name).write_text("fixture")
            for encoding in ("bert", "one-hot"):
                with self.subTest(encoding=encoding):
                    ns = self.functions()
                    ns["AutoTokenizer"].from_pretrained.return_value.return_value = {
                        "input_ids": [1], "attention_mask": [1]}
                    vector = Mock()
                    vector.detach.return_value = NS(shape=(1, 768))
                    ns["AutoModel"].from_pretrained.return_value.return_value = {"pooler_output": vector}
                    cfg = NS(task_embedding_format=encoding, task_embedding_one_hot_offset=1,
                             data=NS(max_word_len=25), policy=NS(language_encoder=NS(network_kwargs=NS())))
                    ns["get_task_embs"](cfg, ["open drawer"])
                    for factory in (ns["AutoTokenizer"], ns["AutoModel"]):
                        factory.from_pretrained.assert_called_once_with(str(Path(tmp).resolve()), local_files_only=True)
                    self.assertEqual(cfg.policy.language_encoder.network_kwargs.input_size, 768)


if __name__ == "__main__":
    unittest.main()