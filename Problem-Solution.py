# 📝 Problem Statement:
# Create a simple web app where users enter their monthly grocery budget and a list of grocery items they need (with name, quantity, and price per unit). 
# The system should:

# -- Optimize the list to fit within the budget.
# -- Show which items can be bought fully, partially (optional), or skipped.
# -- Allow sorting items by priority (if user adds it) or cost.
# -- Show statistics:
# ----> Total cost if everything is bought.
# ----> Amount saved.
# ----> Items dropped due to budget limits.

from math import floor
input_data = {
    1: { "item": "Flour", "qty": 2, "price": 40, "priority": 1 },
    2: { "item": "Honey", "qty": 1, "price": 320, "priority": 2 },
    3: { "item": "Ghee", "qty": 1, "price": 520, "priority": 2 },
    4: { "item": "Butter", "qty": 1, "price": 250, "priority": 3 }
}
budget = 700

valid_units = [1.0, 0.75, 0.5, 0.25]

def get_valid_qty(budget_left, price):
    for unit in valid_units:
        if unit * price <= budget_left:
            return unit
    return 0 


# Convert dict to list
items = list(input_data.values())
# Sort by priority
items.sort(key=lambda x: x["priority"])

# Total cost of everything
total_cost = sum(item["qty"] * item["price"] for item in items)
print("Total cost of the input list:", total_cost)

remaining_budget = budget
final_list = []

if total_cost <= budget:
    for item in items:
        item_copy = item.copy()
        item_copy["status"] = "Full"
        final_list.append(item_copy)
    remaining_budget-=total_cost
else:
    for item in items:
        item_copy = item.copy()
        cost = item["qty"] * item["price"]
        if cost <= remaining_budget:
            item_copy["status"] = "Full"
            final_list.append(item_copy)
            remaining_budget -= cost
        else:
            unit_qty = get_valid_qty(remaining_budget, item["price"])
            if unit_qty > 0:
                item_copy["qty"] = unit_qty
                item_copy["status"] = "Partial"
                remaining_budget -= unit_qty * item["price"]
                final_list.append(item_copy)
            else:
                item_copy["status"] = "Skipped"
                item_copy["qty"] = 0
                final_list.append(item_copy)

            # ✅ Final Output
            print("\nFinal Optimized List:")
            for item in final_list:
                print(item)

print("\nStatistics:")
print("-- Total Spent:", budget - remaining_budget)
print("-- Savings:",  floor(remaining_budget * 100)/100)

# Skipped items
skipped_items = [item["item"] for item in final_list if item["status"] == "Skipped"]
print("-- Items Skipped:")
if skipped_items:
    for name in skipped_items:
        print("---->", name)
else:
    print("----> None")
