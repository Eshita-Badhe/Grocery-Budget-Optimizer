from flask import Flask, render_template, request , jsonify
from math import floor

app=Flask(__name__)

input_data=[]
budget=0
final_list=[]
remaining_budget=0

@app.route('/')
def homepage():
    global input_data, budget, final_list,remaining_budget
    input_data=[]
    budget=0
    final_list=[]
    remaining_budget=0
    return render_template('index.html')

def optimizer():
    global final_list,remaining_budget
    valid_units = [1.0, 0.75, 0.5, 0.25]

    def get_valid_qty(budget_left, price):
        for unit in valid_units:
            if unit * price <= budget_left:
                return unit
        return 0 


    items = input_data.copy()
    items.sort(key=lambda x: x["priority"])

    # Total cost of everything
    total_cost = sum(item["qty"] * item["price"] for item in items)
    print("Total cost of the input list:", total_cost)

    remaining_budget = budget
    final_list=[]

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


@app.route('/add_item', methods=['POST'])
def add_item():
    data = request.get_json()
    input_data.append(data)
    print("Received:", data)  
    return jsonify({"message": "Item received", "received_data": data})

@app.route('/remove_item', methods=['POST'])
def remove_item():
    data = request.get_json()
    item_to_remove = data.get('item')

    global input_data
    input_data = [item for item in input_data if item['item'] != item_to_remove]
    return jsonify({"message": "Item removed", "updated_data": input_data})

@app.route('/submit', methods=['POST'])
def submit():
    global budget
    budget = request.get_json()
    budget=budget['budget']
    optimizer()
    stats = {
        "spent": round(budget - remaining_budget, 2),
        "savings": round(remaining_budget, 2),
        "skipped": [item["item"] for item in final_list if item["status"] == "Skipped"]
    }
    return jsonify({
        "message": "Final optimization complete",
        "Final_list": final_list,
        "Statistics": stats
    })

if (__name__ == "__main__"):
    app.run(debug=True)
