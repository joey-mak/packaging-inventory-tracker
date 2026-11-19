# Packaging Inventory Tracker for a Fast Food Restaurant

This Streamlit application tracks packaging supplies for a fictional restaurant. Store employees view and withdraw stock. Shift managers view stock, add items, record receipts, review movement history and manage replenishment thresholds. The role selector is for coursework demonstrations. Both roles share the same SQLite inventory.

## Run locally

From this directory on macOS, run the following with Python 3.14.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL shown in the terminal. The first run creates `inventory.sqlite3` with sample items. Stock and movement history persist between local runs. Set `INVENTORY_DB_PATH` to use another database file. If the hosting service replaces the filesystem, a local SQLite database can be reset with the runtime.

## Check the main workflows

1. As **Store employee**, select **Paper Cups** in a fresh demo database. Withdraw 7 of the 10 available units and check that the page shows 3.
2. Try to withdraw 4. Check the insufficient stock message and confirm that the balance remains 3.
3. Switch to **Shift manager**. Confirm that the history includes the successful withdrawal. Receive 12 cups and confirm that the balance becomes 15 and that the receipt appears in history.
4. Add **Napkins** and confirm that the new item appears with zero stock.

## Check low-stock alerts

1. In a fresh demo database, withdraw 7 of the 10 **Paper Cups** as **Store employee**.
2. As **Shift manager**, open **Set threshold**, select **Paper Cups**, enter `3` and save. Confirm that **Items to replenish** shows the item with 3 units on hand.
3. Open **Receive stock** and receive 1 paper cup. Confirm that inventory shows 4 and that **Items to replenish** is empty.

Thresholds are whole numbers of zero or more. Items begin without a threshold and enter the list once their stock is at or below a configured threshold. The database adds the threshold field when an existing V1.0 inventory is opened.

## Automated checks

```sh
python -m unittest discover -s tests -v
```

The business logic tests cover inventory operations, quantity boundaries, failed-write rollback, concurrent withdrawals and persistence. The replenishment tests cover the threshold boundary, removal after a receipt and the V1.0 database upgrade. The Streamlit tests exercise employee and manager workflows. The GitHub Actions workflow runs the same tests on pushes and pull requests.

To run the SQLite business logic tests by themselves, use `python -m unittest discover -s tests -p 'test_inventory.py' -v`.

## Source files

| File | Responsibility |
| --- | --- |
| `requirements.md` | V1.0 scope, acceptance criteria and proposed V1.1 change |
| `app.py` | Streamlit screens, role selection and user feedback |
| `inventory.py` | Quantity validation, inventory balances and movement transactions |
| `tests/` | Automated checks for business logic and Streamlit workflows |

## AI assistance

OpenAI Codex assisted with the requirements draft, the initial application and the automated tests. The task was to implement the approved English-language V1.0 requirements and keep every development file in the Assessment 3 folder. The local test suite checks the generated behavior against the acceptance criteria.

For [Issue #1](https://github.com/joey-mak/packaging-inventory-tracker/issues/1), Codex assisted with the threshold form, the SQLite upgrade and the new tests. The change introduces optional thresholds set by shift managers. The change carries moderate risk because it upgrades a database containing existing balances and movements. A migration test opens a V1.0 database, compares its balances and movement history and opens it again after saving a threshold. The original 15 tests remain in the suite as regression checks.
