import os
import sqlite3
from pathlib import Path

import streamlit as st

from inventory import Inventory, InventoryError


@st.cache_resource
def open_inventory(database_path: Path) -> Inventory:
    inventory = Inventory(database_path)
    inventory.initialize()
    return inventory


def show_movement_form(inventory: Inventory, *, withdrawal: bool) -> None:
    action = "withdrawal" if withdrawal else "receipt"
    items = {item["id"]: item["name"] for item in inventory.list_items()}

    with st.form(action):
        item_id = st.selectbox("Item", options=list(items), format_func=items.__getitem__)
        quantity = st.text_input("Quantity", placeholder="e.g. 7")
        submitted = st.form_submit_button(f"Record {action}", type="primary")
        if submitted:
            save = inventory.withdraw_stock if withdrawal else inventory.receive_stock
            try:
                balance = save(item_id, quantity)
            except InventoryError as error:
                st.error(str(error))
            except sqlite3.Error:
                st.error("The stock movement could not be saved. Please try again.")
            else:
                st.success(f"Stock {action} recorded. {items[item_id]} on hand: {balance}.")


def show_add_item_form(inventory: Inventory) -> None:
    with st.form("new_item"):
        name = st.text_input("Item name", placeholder="e.g. Napkins")
        if st.form_submit_button("Add item", type="primary"):
            try:
                inventory.add_item(name)
            except InventoryError as error:
                st.error(str(error))
            except sqlite3.Error:
                st.error("The item could not be saved. Please try again.")
            else:
                st.success(f"{name.strip()} added with zero stock.")


def show_threshold_form(inventory: Inventory) -> None:
    items = {item["id"]: item["name"] for item in inventory.list_items()}
    with st.form("set_threshold"):
        item_id = st.selectbox("Packaging item", options=list(items), format_func=items.__getitem__)
        threshold = st.text_input(
            "Replenishment threshold",
            placeholder="e.g. 3",
            help="Enter a whole number of zero or more.",
        )
        if st.form_submit_button("Save threshold", type="primary"):
            try:
                saved = inventory.set_replenishment_threshold(item_id, threshold)
            except InventoryError as error:
                st.error(str(error))
            except sqlite3.Error:
                st.error("The threshold could not be saved. Please try again.")
            else:
                st.success(f"Replenishment threshold for {items[item_id]} set to {saved} units.")


def show_replenishment_list(inventory: Inventory) -> None:
    st.header("Items to replenish")
    low_stock_items = inventory.list_low_stock_items()
    if not low_stock_items:
        st.info("No items are at or below their configured threshold.")
        return

    st.table(
        [
            {
                "Item": item["name"],
                "Units on hand": item["quantity"],
                "Threshold": item["replenishment_threshold"],
            }
            for item in low_stock_items
        ],
        hide_index=True,
    )


def main() -> None:
    st.set_page_config(page_title="Packaging Inventory Tracker", layout="wide")
    default_database = Path(__file__).with_name("inventory.sqlite3")
    database_path = Path(os.getenv("INVENTORY_DB_PATH", str(default_database)))
    inventory = open_inventory(database_path)

    role = st.sidebar.radio("Demo role", ("Store employee", "Shift manager"))
    is_manager = role == "Shift manager"
    st.title("Packaging Inventory Tracker")

    stock_panel, action_panel = st.columns([3, 2], gap="large")
    with action_panel:
        if is_manager:
            st.header("Manage stock")
            receive_tab, add_tab, threshold_tab = st.tabs(["Receive stock", "Add item", "Set threshold"])
            with add_tab:
                show_add_item_form(inventory)
            with receive_tab:
                show_movement_form(inventory, withdrawal=False)
            with threshold_tab:
                show_threshold_form(inventory)
        else:
            st.header("Withdraw stock")
            show_movement_form(inventory, withdrawal=True)

    with stock_panel:
        st.header("Current inventory")
        stock_columns = {"Item": "name", "Units on hand": "quantity"}
        if is_manager:
            stock_columns["Threshold"] = "replenishment_threshold"
        st.dataframe(
            [
                {label: item[column] for label, column in stock_columns.items()}
                for item in inventory.list_items()
            ],
            column_config={"Threshold": st.column_config.NumberColumn(format="%d")},
            hide_index=True,
            width="stretch",
        )

    if is_manager:
        show_replenishment_list(inventory)
        st.header("Stock movement history")
        st.dataframe(
            [
                {
                    "Item": movement["name"],
                    "Movement": movement["kind"],
                    "Quantity": movement["quantity"],
                    "Recorded at (UTC)": movement["created_at"],
                }
                for movement in inventory.list_movements()
            ],
            hide_index=True,
            width="stretch",
        )


if __name__ == "__main__":
    main()
