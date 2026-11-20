import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from inventory import MAX_QUANTITY, Inventory, InventoryError


class LowStockTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.database = Path(directory.name) / "inventory.sqlite3"
        self.inventory = Inventory(self.database)
        self.inventory.initialize()
        self.items = {item["name"]: item["id"] for item in self.inventory.list_items()}
        self.cups = self.items["Paper Cups"]

    def test_threshold_uses_the_inclusive_stock_boundary(self):
        self.inventory.set_replenishment_threshold(self.cups, 3)
        cases = ((6, []), (1, [("Paper Cups", 3, 3)]), (1, [("Paper Cups", 2, 3)]))
        for withdrawal, expected in cases:
            with self.subTest(withdrawal=withdrawal, expected=expected):
                self.inventory.withdraw_stock(self.cups, withdrawal)
                self.assertEqual([tuple(item) for item in self.inventory.list_low_stock_items()], expected)

    def test_receipt_above_threshold_removes_item_from_list(self):
        self.inventory.set_replenishment_threshold(self.cups, 3)
        self.inventory.withdraw_stock(self.cups, 7)
        self.assertEqual(len(self.inventory.list_low_stock_items()), 1)

        self.assertEqual(self.inventory.receive_stock(self.cups, 1), 4)
        self.assertEqual(self.inventory.list_low_stock_items(), [])

    def test_items_without_a_threshold_are_excluded_even_at_zero_stock(self):
        self.inventory.add_item("Napkins")
        stock = {item["name"]: item for item in self.inventory.list_items()}
        for name in ("Paper Bags", "Napkins"):
            self.assertEqual(stock[name]["quantity"], 0)
            self.assertIsNone(stock[name]["replenishment_threshold"])
        self.assertEqual(self.inventory.list_low_stock_items(), [])

    def test_setting_thresholds_does_not_change_stock_or_record_movements(self):
        quantities_before = {item["id"]: item["quantity"] for item in self.inventory.list_items()}
        movements_before = self.inventory.list_movements()

        self.inventory.set_replenishment_threshold(self.cups, "12")
        self.inventory.set_replenishment_threshold(self.items["Paper Bags"], "0")

        self.assertEqual(
            [tuple(item) for item in self.inventory.list_low_stock_items()],
            [("Paper Bags", 0, 0), ("Paper Cups", 10, 12)],
        )
        self.assertEqual({item["id"]: item["quantity"] for item in self.inventory.list_items()}, quantities_before)
        self.assertEqual(self.inventory.list_movements(), movements_before)

    def test_invalid_thresholds_leave_the_saved_threshold_unchanged(self):
        self.inventory.set_replenishment_threshold(self.cups, 3)
        stock_before = self.inventory.list_items()
        for invalid in (-1, "-1", "1.5", 1.5, "", "two", True, MAX_QUANTITY + 1):
            with self.subTest(invalid=invalid), self.assertRaises(InventoryError):
                self.inventory.set_replenishment_threshold(self.cups, invalid)
        self.assertEqual(self.inventory.list_items(), stock_before)

    def test_v10_database_upgrade_preserves_stock_history_and_saved_thresholds(self):
        legacy_database = self.database.with_name("v10.sqlite3")
        with closing(sqlite3.connect(legacy_database)) as connection:
            connection.executescript(
                """
                CREATE TABLE items (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0)
                );
                CREATE TABLE movements (
                    id INTEGER PRIMARY KEY,
                    item_id INTEGER NOT NULL REFERENCES items(id),
                    kind TEXT NOT NULL CHECK (kind IN ('Receipt', 'Withdrawal')),
                    quantity INTEGER NOT NULL CHECK (quantity > 0),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                INSERT INTO items (id, name, quantity) VALUES (7, 'Legacy Cups', 6);
                INSERT INTO movements (item_id, kind, quantity, created_at) VALUES
                    (7, 'Receipt', 10, '2026-11-18 10:00:00'),
                    (7, 'Withdrawal', 4, '2026-11-18 10:30:00');
                """
            )

        upgraded = Inventory(legacy_database)
        upgraded.initialize()
        self.assertEqual([tuple(item) for item in upgraded.list_items()], [(7, "Legacy Cups", 6, None)])
        expected_history = [
            ("Legacy Cups", "Withdrawal", 4, "2026-11-18 10:30:00"),
            ("Legacy Cups", "Receipt", 10, "2026-11-18 10:00:00"),
        ]
        self.assertEqual([tuple(movement) for movement in upgraded.list_movements()], expected_history)

        upgraded.set_replenishment_threshold(7, 6)
        reopened = Inventory(legacy_database)
        reopened.initialize()
        self.assertEqual([tuple(item) for item in reopened.list_low_stock_items()], [("Legacy Cups", 6, 6)])
        self.assertEqual([tuple(movement) for movement in reopened.list_movements()], expected_history)


if __name__ == "__main__":
    unittest.main()
