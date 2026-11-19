import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path


MAX_QUANTITY = 2**63 - 1
DEMO_ITEMS = (("Paper Cups", 10), ("Takeaway Boxes", 24), ("Paper Bags", 0))


class InventoryError(ValueError):
    """An inventory request that cannot be completed."""


class Inventory:
    def __init__(self, database_path: Path):
        self.database_path = database_path

    @contextmanager
    def _connect(self):
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            with connection:
                yield connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0)
                );

                CREATE TABLE IF NOT EXISTS movements (
                    id INTEGER PRIMARY KEY,
                    item_id INTEGER NOT NULL REFERENCES items(id),
                    kind TEXT NOT NULL CHECK (kind IN ('Receipt', 'Withdrawal')),
                    quantity INTEGER NOT NULL CHECK (quantity > 0),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            connection.execute("BEGIN IMMEDIATE")
            columns = {column["name"] for column in connection.execute("PRAGMA table_info(items)")}
            if "replenishment_threshold" not in columns:
                connection.execute(
                    """
                    ALTER TABLE items ADD COLUMN replenishment_threshold INTEGER
                    CHECK (
                        replenishment_threshold IS NULL OR (
                            typeof(replenishment_threshold) = 'integer' AND replenishment_threshold >= 0
                        )
                    )
                    """
                )
            if connection.execute("SELECT 1 FROM items LIMIT 1").fetchone() is None:
                connection.executemany(
                    "INSERT INTO items (name, quantity) VALUES (?, ?)", DEMO_ITEMS
                )
                connection.execute(
                    """
                    INSERT INTO movements (item_id, kind, quantity)
                    SELECT id, 'Receipt', quantity FROM items WHERE quantity > 0
                    """
                )

    def list_items(self) -> list[sqlite3.Row]:
        with self._connect() as connection:
            return connection.execute(
                "SELECT id, name, quantity, replenishment_threshold FROM items ORDER BY name"
            ).fetchall()

    def add_item(self, name: str) -> None:
        name = name.strip()
        if not name:
            raise InventoryError("Enter an item name.")

        with self._connect() as connection:
            result = connection.execute(
                "INSERT INTO items (name) VALUES (?) ON CONFLICT(name) DO NOTHING",
                (name,),
            )
            if result.rowcount == 0:
                raise InventoryError("An item with that name already exists.")

    def set_replenishment_threshold(self, item_id: int, threshold: int | str) -> int:
        threshold = _whole_quantity(threshold, minimum=0, field="replenishment threshold")
        with self._connect() as connection:
            result = connection.execute(
                "UPDATE items SET replenishment_threshold = ? WHERE id = ?",
                (threshold, item_id),
            )
            if result.rowcount == 0:
                raise InventoryError("That item could not be found.")
        return threshold

    def list_low_stock_items(self) -> list[sqlite3.Row]:
        with self._connect() as connection:
            return connection.execute(
                """
                SELECT name, quantity, replenishment_threshold FROM items
                WHERE replenishment_threshold IS NOT NULL AND quantity <= replenishment_threshold
                ORDER BY name
                """
            ).fetchall()

    def list_movements(self) -> list[sqlite3.Row]:
        with self._connect() as connection:
            return connection.execute(
                """
                SELECT items.name, movements.kind, movements.quantity, movements.created_at
                FROM movements JOIN items ON items.id = movements.item_id
                ORDER BY movements.id DESC
                """
            ).fetchall()

    def receive_stock(self, item_id: int, quantity: int | str) -> int:
        return self._record_movement(item_id, quantity, "Receipt")

    def withdraw_stock(self, item_id: int, quantity: int | str) -> int:
        return self._record_movement(item_id, quantity, "Withdrawal")

    def _record_movement(self, item_id: int, quantity: int | str, kind: str) -> int:
        quantity = _whole_quantity(quantity)

        with self._connect() as connection:
            # Keep another submission from changing the balance before this one commits.
            connection.execute("BEGIN IMMEDIATE")
            item = connection.execute(
                "SELECT quantity FROM items WHERE id = ?", (item_id,)
            ).fetchone()
            if item is None:
                raise InventoryError("That item could not be found.")

            current_quantity = item["quantity"]
            new_quantity = (
                current_quantity + quantity if kind == "Receipt" else current_quantity - quantity
            )
            if new_quantity < 0:
                raise InventoryError(f"Insufficient stock. Only {current_quantity} units available.")
            if new_quantity > MAX_QUANTITY:
                raise InventoryError("The resulting stock balance is too large.")

            connection.execute("UPDATE items SET quantity = ? WHERE id = ?", (new_quantity, item_id))
            connection.execute(
                "INSERT INTO movements (item_id, kind, quantity) VALUES (?, ?, ?)",
                (item_id, kind, quantity),
            )
            return new_quantity


def _whole_quantity(value: int | str, *, minimum: int = 1, field: str = "quantity") -> int:
    requirement = "positive" if minimum == 1 else "non-negative"
    error = f"Enter a {requirement} whole number for the {field}."
    if isinstance(value, str):
        value = value.strip()
        if not value.isascii() or not value.isdecimal():
            raise InventoryError(error)
        try:
            value = int(value)
        except ValueError:
            raise InventoryError(error) from None

    if type(value) is not int or value < minimum:
        raise InventoryError(error)
    if value > MAX_QUANTITY:
        raise InventoryError(f"The {field} is too large.")
    return value
