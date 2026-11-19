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


def main() -> None:
    st.set_page_config(page_title="Packaging Inventory Tracker", layout="wide")
    default_database = Path(__file__).with_name("inventory.sqlite3")
    database_path = Path(os.getenv("INVENTORY_DB_PATH", str(default_database)))
    inventory = open_inventory(database_path)

    role = st.sidebar.radio("Demo role", ("Store employee", "Shift manager"))
    st.title("Packaging Inventory Tracker")

    stock_panel, action_panel = st.columns([3, 2], gap="large")
    with action_panel:
        if role == "Store employee":
            st.header("Withdraw stock")
            show_movement_form(inventory, withdrawal=True)
        else:
            st.header("Manage stock")
            receive_tab, add_tab = st.tabs(["Receive stock", "Add item"])
            with add_tab:
                show_add_item_form(inventory)
            with receive_tab:
                show_movement_form(inventory, withdrawal=False)

    with stock_panel:
        st.header("Current inventory")
        st.dataframe(
            [{"Item": item["name"], "Units on hand": item["quantity"]} for item in inventory.list_items()],
            hide_index=True,
            width="stretch",
        )

    if role == "Shift manager":
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
