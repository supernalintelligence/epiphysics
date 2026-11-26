from contextlib import contextmanager
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from epiphysics.store import Ledger, digest


class CaptureBoundsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.now = "2030-01-01T00:00:00Z"
        self.ledger = Ledger(self.root, clock=lambda: self.now)

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def blob_path(self, content):
        return self.root / "blobs" / digest(content)

    @contextmanager
    def checked_reads(self, path, expected_bound, *, refuse_open=False):
        original_open = Path.open
        sizes = []
        test = self

        class Reader:
            def __init__(self, stream):
                self.stream = stream

            def __enter__(self):
                self.stream.__enter__()
                return self

            def __exit__(self, *arguments):
                return self.stream.__exit__(*arguments)

            def read(self, size=-1):
                test.assertEqual(expected_bound, size, "Existing blob read was not bounded by expected bytes")
                sizes.append(size)
                return self.stream.read(size)

        def checked_open(candidate, mode="r", *arguments, **options):
            if candidate == path and mode == "rb":
                test.assertFalse(refuse_open, "Rejected blob was opened for reading")
                return Reader(original_open(candidate, mode, *arguments, **options))
            return original_open(candidate, mode, *arguments, **options)

        with patch.object(Path, "open", checked_open), patch.object(Path, "read_bytes",
                side_effect=AssertionError("Capture must not use unbounded Path.read_bytes")):
            yield sizes

    def test_oversized_sparse_existing_blob_is_read_only_to_expected_size_plus_one(self):
        content = b"c" * 235
        path = self.blob_path(content)
        with path.open("xb") as stream:
            stream.write(content)
            stream.truncate(20_000_000)
        before = path.stat()
        with self.checked_reads(path, 236) as reads, self.assertRaisesRegex(ValueError, "corrupted"):
            self.ledger.capture("test:config", content, event_id="config")
        self.assertEqual([236], reads)
        self.assertEqual([], self.ledger.events())
        after = path.stat()
        self.assertEqual(before.st_ino, after.st_ino)
        self.assertEqual(20_000_000, after.st_size)
        self.assertEqual(before.st_mtime_ns, after.st_mtime_ns)
        with path.open("rb") as stream:
            self.assertEqual(content + b"\0", stream.read(236))

    def test_same_size_corrupt_existing_blob_is_preserved_without_an_event(self):
        content = b"expected bytes"
        corrupted = b"x" * len(content)
        path = self.blob_path(content)
        path.write_bytes(corrupted)
        before = path.stat()
        with self.checked_reads(path, len(content) + 1) as reads, self.assertRaisesRegex(ValueError, "corrupted"):
            self.ledger.capture("test:source", content)
        self.assertEqual([len(content) + 1], reads)
        self.assertEqual(corrupted, path.read_bytes())
        self.assertEqual(before.st_mtime_ns, path.stat().st_mtime_ns)
        self.assertEqual([], self.ledger.events())

    def test_short_existing_blob_is_preserved_without_an_event(self):
        content = b"expected bytes"
        path = self.blob_path(content)
        path.write_bytes(content[:-1])
        with self.checked_reads(path, len(content) + 1), self.assertRaisesRegex(ValueError, "corrupted"):
            self.ledger.capture("test:source", content)
        self.assertEqual(content[:-1], path.read_bytes())
        self.assertEqual([], self.ledger.events())

    def test_valid_blob_reuse_and_exact_event_replay_do_not_rewrite_or_duplicate(self):
        content = b"preserved source"
        original = self.ledger.capture("test:source", content, event_id="original")
        path = self.blob_path(content)
        before = path.stat()
        self.now = "2030-01-01T00:01:00Z"
        with self.checked_reads(path, len(content) + 1) as reads:
            replay = self.ledger.capture("test:source", content, event_id="original")
            reused = self.ledger.capture("test:another-source", content, event_id="reused")
        self.assertEqual([len(content) + 1, len(content) + 1], reads)
        self.assertEqual(original, replay)
        self.assertEqual(original["body"]["content_hash"], reused["body"]["content_hash"])
        self.assertEqual([original, reused], self.ledger.events())
        self.assertEqual(before.st_ino, path.stat().st_ino)
        self.assertEqual(before.st_mtime_ns, path.stat().st_mtime_ns)
        self.assertTrue(self.ledger.verify()["valid"])

    def test_empty_blob_reuse_uses_one_byte_bound_and_preserves_zero_size(self):
        original = self.ledger.capture("test:empty", b"", event_id="empty")
        path = self.blob_path(b"")
        with self.checked_reads(path, 1) as reads:
            replay = self.ledger.capture("test:empty", b"", event_id="empty")
        self.assertEqual([1], reads)
        self.assertEqual(original, replay)
        self.assertEqual(0, replay["body"]["size"])
        self.assertEqual(0, path.stat().st_size)
        self.assertEqual([original], self.ledger.events())

    def test_valid_capture_above_one_megabyte_has_no_new_global_size_cap(self):
        content = b"valid" * 300_000
        original = self.ledger.capture("test:large", content, event_id="large")
        with self.checked_reads(self.blob_path(content), len(content) + 1) as reads:
            replay = self.ledger.capture("test:large", content, event_id="large")
        self.assertEqual([len(content) + 1], reads)
        self.assertEqual(original, replay)
        self.assertEqual(len(content), original["body"]["size"])

    def test_existing_symlinks_are_not_followed_or_replaced(self):
        content = b"source bytes"
        path = self.blob_path(content)
        for exists in (True, False):
            with self.subTest(target_exists=exists):
                target = self.root / ("present" if exists else "missing")
                if exists:
                    target.write_bytes(content)
                path.symlink_to(target)
                with self.checked_reads(path, len(content) + 1, refuse_open=True) as reads:
                    with self.assertRaisesRegex(ValueError, "regular non-symlink"):
                        self.ledger.capture("test:source", content)
                self.assertEqual([], reads)
                self.assertTrue(path.is_symlink())
                self.assertEqual(target, path.readlink())
                self.assertEqual(exists, target.exists())
                if exists:
                    self.assertEqual(content, target.read_bytes())
                self.assertEqual([], self.ledger.events())
                path.unlink()

    def test_existing_directory_is_refused_without_reading_or_replacing_it(self):
        content = b"source bytes"
        path = self.blob_path(content)
        path.mkdir()
        marker = path / "marker"
        marker.write_bytes(b"unchanged")
        with self.checked_reads(path, len(content) + 1, refuse_open=True) as reads:
            with self.assertRaisesRegex(ValueError, "regular non-symlink"):
                self.ledger.capture("test:source", content)
        self.assertEqual([], reads)
        self.assertEqual(b"unchanged", marker.read_bytes())
        self.assertEqual([], self.ledger.events())

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO creation unavailable")
    def test_existing_fifo_is_refused_without_opening_or_blocking(self):
        content = b"source bytes"
        path = self.blob_path(content)
        os.mkfifo(path)
        before = path.lstat()
        with self.checked_reads(path, len(content) + 1, refuse_open=True) as reads:
            with self.assertRaisesRegex(ValueError, "regular non-symlink"):
                self.ledger.capture("test:source", content)
        self.assertEqual([], reads)
        self.assertEqual(before.st_mode, path.lstat().st_mode)
        self.assertEqual(before.st_ino, path.lstat().st_ino)
        self.assertEqual([], self.ledger.events())

    def test_grouped_capture_refuses_before_any_blob_open_and_poisons_group(self):
        with patch.object(Path, "open", side_effect=AssertionError("Grouped capture touched a blob")):
            with self.assertRaisesRegex(ValueError, "complete group"):
                with self.ledger.atomic_write():
                    self.ledger.append("derived", {}, "derived")
                    with self.assertRaisesRegex(ValueError, "observation writes are not allowed"):
                        self.ledger.capture("test:source", b"new bytes")
        self.assertEqual([], self.ledger.events())
        self.assertEqual([], list((self.root / "blobs").iterdir()))


if __name__ == "__main__":
    unittest.main()
