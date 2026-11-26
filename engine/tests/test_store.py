from pathlib import Path
import tempfile
import unittest

from epiphysics.store import Ledger


class ForecastValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.now = "2030-01-01T00:00:00Z"
        self.ledger = Ledger(Path(self.temp.name), clock=lambda: self.now)
        self.snapshot = self.ledger.snapshot()
        self.question = self.ledger.question("Synthetic question", "2030-01-01T00:05:00Z",
            "2030-01-01T00:10:00Z", "Synthetic outcome", "synthetic")

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def forecast(self, **options):
        return self.ledger.forecast(self.question["id"], self.snapshot["id"], "test-method", 0.5,
                                   model={"identifier": "synthetic"}, **options)

    def test_additional_validator_runs_inside_write_transaction_at_recorded_time(self):
        seen = []
        self.now = "2030-01-01T00:01:00Z"

        def validate(recorded_at):
            seen.append((self.ledger.db.in_transaction, recorded_at))

        event = self.forecast(validate=validate)
        self.assertEqual(seen, [(True, event["recorded_at"])])
        self.assertEqual(event["recorded_at"], self.now)

    def test_additional_validation_rejection_rolls_back_and_replay_skips_callback(self):
        before = len(self.ledger.events())

        def reject(recorded_at):
            raise ValueError("Additional binding rejected")

        with self.assertRaisesRegex(ValueError, "Additional binding"):
            self.forecast(validate=reject)
        self.assertEqual(len(self.ledger.events()), before)
        self.assertFalse(self.ledger.db.in_transaction)
        original = self.forecast(event_id="original")
        self.now = "2030-01-01T00:06:00Z"
        self.assertEqual(self.forecast(event_id="original", validate=reject), original)
        self.assertEqual(len(self.ledger.events()), before + 1)

    def test_additional_validator_cannot_replace_core_deadline_and_duplicate_checks(self):
        self.forecast()
        called = []
        with self.assertRaisesRegex(ValueError, "already attempted"):
            self.forecast(validate=lambda now: called.append(now))
        self.now = "2030-01-01T00:05:00Z"
        with self.assertRaisesRegex(ValueError, "deadline"):
            self.forecast(validate=lambda now: called.append(now))
        self.assertEqual(called, [])
        self.assertEqual(len(self.ledger.events("forecast")), 1)

    def test_noncallable_additional_validators_are_rejected_without_append(self):
        before = len(self.ledger.events())
        for value in (False, 1, "validate", {}, []):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "callable"):
                self.forecast(validate=value)
        self.assertEqual(len(self.ledger.events()), before)


if __name__ == "__main__":
    unittest.main()
