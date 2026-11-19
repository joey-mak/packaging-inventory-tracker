# Packaging Inventory Tracker for a Fast Food Restaurant

## V1.0 Project Scope

The application helps a fictional fast food restaurant track packaging supplies such as paper cups, takeaway boxes and paper bags. Store employees can check availability and record supplies they take. Shift managers can add items, record deliveries and review stock movements. Inventory is tracked in individual units using sample data.

## Functional Requirements

| ID | User role | Requirement | Acceptance criterion |
| --- | --- | --- | --- |
| FR-01 | Store employee and shift manager | View the current inventory. | The inventory list shows each item's name and current quantity, including items with zero stock. |
| FR-02 | Store employee | Record a stock withdrawal for an existing item. | With 10 paper cups in stock, withdrawing 7 succeeds, leaves 3 in stock and creates one withdrawal record for 7 cups. |
| FR-03 | Shift manager | Add a packaging item to the inventory. | A new item with a nonblank name appears in the inventory with a quantity of zero. |
| FR-04 | Shift manager | Record stock received for an existing item. | With 3 paper cups in stock, receiving 12 raises the balance to 15 and creates one receipt record for 12 cups. |
| FR-05 | Shift manager | Review stock movement history. | After recording a receipt and a withdrawal, both appear in the history with the item name, quantity, movement type and timestamp. |

## Business Rules

- **BR-01 — Valid quantity.** Receipt and withdrawal quantities must be positive whole numbers. Zero, negative numbers and fractional quantities are rejected.
- **BR-02 — Sufficient stock.** A withdrawal may use up the entire available balance. A withdrawal that exceeds the balance is rejected. From a starting balance of 10, withdrawing 10 leaves zero. A separate attempt to withdraw 11 from a starting balance of 10 leaves the balance at 10 and creates no movement record.

## Software Quality Requirements

| ID | Quality attribute | Requirement and acceptance criterion |
| --- | --- | --- |
| QR-01 | Data integrity | Each successful stock movement updates the balance and creates exactly one matching history entry. A failed operation leaves both the balance and the history unchanged. This can be verified by comparing both records before and after a successful movement and a rejected movement. |
| QR-02 | Usability | An employee can select an item, enter a quantity and submit a withdrawal from a single screen. That screen displays the new balance after success or a specific reason for rejection, such as insufficient stock. |

## Project Risk

An invalid quantity or an excessive withdrawal could make the stock balance inaccurate. Apply the quantity and availability checks before saving a movement. Test valid movements, zero, negative and fractional quantities, a withdrawal equal to the available balance and a withdrawal one unit above it.

## Proposed V1.1 Change

After releasing V1.0, add a replenishment threshold that the shift manager can set for each item. An item appears in the replenishment list when its stock is at or below its threshold and leaves the list when its stock rises above that threshold. For an item with a threshold of 3, a balance of 3 appears in the list and a balance of 4 does not.
