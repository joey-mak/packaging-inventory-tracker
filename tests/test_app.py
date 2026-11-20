import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from inventory import Inventory


class InventoryAppTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        database_path = Path(directory.name) / "inventory.sqlite3"
        environment = patch.dict(os.environ, {"INVENTORY_DB_PATH": str(database_path)})
        environment.start()
        self.addCleanup(environment.stop)

        self.inventory = Inventory(database_path)
        script = Path(__file__).resolve().parents[1] / "app.py"
        self.app = AppTest.from_file(str(script), default_timeout=15).run()
        self.assertFalse(self.app.exception)

    def submit(self, label):
        button = next(button for button in self.app.button if button.label == label)
        button.click().run()
        self.assertFalse(self.app.exception)

    def displayed_stock(self, item_name):
        inventory_table = self.app.dataframe[0].value
        return inventory_table.set_index("Item").loc[item_name, "Units on hand"]

    def test_employee_sees_updated_stock_and_rejection_feedback(self):
        self.assertEqual(self.app.radio[0].value, "Store employee")
        self.assertEqual(self.displayed_stock("Paper Cups"), 10)
        self.assertEqual([button.label for button in self.app.button], ["Record withdrawal"])
        paper_cups = next(item for item in self.inventory.list_items() if item["name"] == "Paper Cups")
        self.app.selectbox[0].set_value(paper_cups["id"])
        self.app.text_input[0].set_value("7")
        self.submit("Record withdrawal")

        self.assertIn("Paper Cups on hand: 3", self.app.success[0].value)
        self.assertEqual(self.displayed_stock("Paper Cups"), 3)
        movement_count = len(self.inventory.list_movements())

        self.app.text_input[0].set_value("4")
        self.submit("Record withdrawal")

        self.assertIn("Insufficient stock", self.app.error[0].value)
        self.assertEqual(self.displayed_stock("Paper Cups"), 3)
        self.assertEqual(len(self.inventory.list_movements()), movement_count)

    def test_manager_adds_item_receives_stock_and_sees_history(self):
        self.app.radio[0].set_value("Shift manager").run()
        self.assertFalse(self.app.exception)
        name_input = next(field for field in self.app.text_input if field.label == "Item name")
        name_input.set_value("Napkins")
        self.submit("Add item")

        self.assertEqual(self.displayed_stock("Napkins"), 0)
        self.assertIn("Napkins", self.app.selectbox[0].options)
        napkins = next(item for item in self.inventory.list_items() if item["name"] == "Napkins")
        self.app.selectbox[0].set_value(napkins["id"])
        quantity_input = next(field for field in self.app.text_input if field.label == "Quantity")
        quantity_input.set_value("12")
        self.submit("Record receipt")

        self.assertEqual(self.displayed_stock("Napkins"), 12)
        last_movement = self.app.dataframe[1].value.iloc[0]
        self.assertEqual(last_movement["Item"], "Napkins")
        self.assertEqual(last_movement["Movement"], "Receipt")
        self.assertEqual(last_movement["Quantity"], 12)

    def test_manager_sees_replenishment_list_update_after_receipt(self):
        paper_cups = next(item for item in self.inventory.list_items() if item["name"] == "Paper Cups")
        self.inventory.withdraw_stock(paper_cups["id"], 7)
        self.app.radio[0].set_value("Shift manager").run()
        self.assertFalse(self.app.exception)

        threshold_item = next(field for field in self.app.selectbox if field.label == "Packaging item")
        threshold_item.set_value(paper_cups["id"])
        threshold = next(field for field in self.app.text_input if field.label == "Replenishment threshold")
        threshold.set_value("3")
        self.submit("Save threshold")
        self.assertEqual(
            self.app.table[0].value.to_dict("records"),
            [{"Item": "Paper Cups", "Units on hand": 3, "Threshold": 3}],
        )

        self.app.selectbox[0].set_value(paper_cups["id"])
        quantity = next(field for field in self.app.text_input if field.label == "Quantity")
        quantity.set_value("1")
        self.submit("Record receipt")

        self.assertEqual(self.displayed_stock("Paper Cups"), 4)
        self.assertFalse(self.app.table)
        self.assertEqual(self.app.info[0].value, "No items are at or below their configured threshold.")


if __name__ == "__main__":
    unittest.main()
