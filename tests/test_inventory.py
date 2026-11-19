import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from inventory import MAX_QUANTITY, Inventory, InventoryError


class InventoryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.database = Path(directory.name) / "inventory.sqlite3"
        self.inventory = Inventory(self.database)
        self.inventory.initialize()
        self.cups = next(item["id"] for item in self.inventory.list_items() if item["name"] == "Paper Cups")

    def snapshot(self):
        return self.inventory.list_items(), self.inventory.list_movements()

    def balance(self):
        return next(item["quantity"] for item in self.inventory.list_items() if item["id"] == self.cups)

    def test_fr01_inventory_includes_items_with_zero_stock(self):
        stock = {item["name"]: item["quantity"] for item in self.inventory.list_items()}
        self.assertEqual(stock["Paper Cups"], 10)
        self.assertEqual(stock["Paper Bags"], 0)

    def test_fr02_withdrawal_updates_stock_and_records_one_movement(self):
        movement_count = len(self.inventory.list_movements())
        self.assertEqual(self.inventory.withdraw_stock(self.cups, "7"), 3)
        self.assertEqual(self.balance(), 3)

        movements = self.inventory.list_movements()
        self.assertEqual(len(movements), movement_count + 1)
        self.assertEqual(tuple(movements[0])[:3], ("Paper Cups", "Withdrawal", 7))

    def test_fr03_new_item_starts_at_zero(self):
        self.inventory.add_item("  Napkins  ")
        napkins = next(item for item in self.inventory.list_items() if item["name"] == "Napkins")
        self.assertEqual(napkins["quantity"], 0)

    def test_fr03_rejects_blank_and_duplicate_item_names(self):
        before = self.snapshot()
        for name in ("  ", "paper cups"):
            with self.subTest(name=name), self.assertRaises(InventoryError):
                self.inventory.add_item(name)
        self.assertEqual(self.snapshot(), before)

    def test_fr04_receipt_increases_stock_and_records_one_movement(self):
        self.inventory.withdraw_stock(self.cups, 7)
        movement_count = len(self.inventory.list_movements())
        self.assertEqual(self.inventory.receive_stock(self.cups, 12), 15)
        self.assertEqual(self.balance(), 15)
        movements = self.inventory.list_movements()
        self.assertEqual(len(movements), movement_count + 1)
        self.assertEqual(tuple(movements[0])[:3], ("Paper Cups", "Receipt", 12))

    def test_fr05_history_lists_both_movements_with_timestamps(self):
        self.inventory.receive_stock(self.cups, 5)
        self.inventory.withdraw_stock(self.cups, 3)

        withdrawal, receipt = self.inventory.list_movements()[:2]
        self.assertEqual(tuple(withdrawal)[:3], ("Paper Cups", "Withdrawal", 3))
        self.assertEqual(tuple(receipt)[:3], ("Paper Cups", "Receipt", 5))
        for movement in (withdrawal, receipt):
            self.assertRegex(movement["created_at"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")

    def test_br01_rejects_invalid_quantities_without_changes(self):
        before = self.snapshot()
        for operation in (self.inventory.receive_stock, self.inventory.withdraw_stock):
            for quantity in (0, -1, 1.5, True, "", "1.5", "two", MAX_QUANTITY + 1):
                with self.subTest(operation=operation.__name__, quantity=quantity):
                    with self.assertRaises(InventoryError):
                        operation(self.cups, quantity)
        self.assertEqual(self.snapshot(), before)

    def test_br02_allows_withdrawal_of_entire_stock(self):
        self.assertEqual(self.inventory.withdraw_stock(self.cups, 10), 0)
        self.assertEqual(self.balance(), 0)

    def test_br02_rejects_withdrawal_one_above_stock(self):
        before = self.snapshot()
        with self.assertRaisesRegex(InventoryError, "Insufficient stock"):
            self.inventory.withdraw_stock(self.cups, 11)
        self.assertEqual(self.snapshot(), before)

    def test_receipt_that_would_overflow_the_balance_changes_nothing(self):
        before = self.snapshot()
        with self.assertRaisesRegex(InventoryError, "balance is too large"):
            self.inventory.receive_stock(self.cups, MAX_QUANTITY)
        self.assertEqual(self.snapshot(), before)

    def test_qr01_rolls_back_balance_if_history_write_fails(self):
        before = self.snapshot()
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                """
                CREATE TRIGGER reject_movement BEFORE INSERT ON movements
                BEGIN
                    SELECT RAISE(ABORT, 'Simulated history write failure');
                END;
                """
            )

        with self.assertRaisesRegex(sqlite3.IntegrityError, "Simulated history write failure"):
            self.inventory.withdraw_stock(self.cups, 7)
        self.assertEqual(self.snapshot(), before)

    def test_simultaneous_withdrawals_cannot_overdraw_stock(self):
        movement_count = len(self.inventory.list_movements())
        start = Barrier(2, timeout=5)

        def attempt_withdrawal():
            start.wait()
            try:
                return self.inventory.withdraw_stock(self.cups, 7)
            except InventoryError:
                return "rejected"

        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(attempt_withdrawal)
            second = executor.submit(attempt_withdrawal)
            self.assertCountEqual([first.result(), second.result()], [3, "rejected"])

        self.assertEqual(self.balance(), 3)
        self.assertEqual(len(self.inventory.list_movements()), movement_count + 1)

    def test_reopening_preserves_existing_stock_and_history(self):
        self.inventory.withdraw_stock(self.cups, 7)
        before = self.snapshot()
        reopened = Inventory(self.database)
        reopened.initialize()
        self.assertEqual((reopened.list_items(), reopened.list_movements()), before)


if __name__ == "__main__":
    unittest.main()
