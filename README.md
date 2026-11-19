# Packaging Inventory Tracker for a Fast Food Restaurant

This Streamlit application tracks packaging supplies for a fictional restaurant. Store employees view and withdraw stock. Shift managers view stock, add items, record receipts and review movement history. The role selector is for coursework demonstrations. Both roles share the same SQLite inventory.

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

## Automated checks

```sh
python -m unittest discover -s tests -v
```

The business logic tests cover the functional requirements, quantity boundaries, failed-write rollback, concurrent withdrawals and persistence. The Streamlit tests exercise the employee and manager workflows. The GitHub Actions workflow runs the same tests on pushes and pull requests.

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
