function createCard() {
    let card = document.createElement("div");
    card.className = "card";

    function makeRow(labelText, inputs) {
        let row = document.createElement("div");
        row.className = "row";

        let label = document.createElement("div");
        label.className = "label";
        label.textContent = labelText;

        row.appendChild(label);
        inputs.forEach(input => row.appendChild(input));
        return row;
    }

    let itemInput = document.createElement("input");
    itemInput.type = "text";
    itemInput.className = "input";
    itemInput.placeholder = "Name";

    let qtyInput = document.createElement("input");
    qtyInput.type = "number";
    qtyInput.className = "input";
    qtyInput.placeholder = "Qty";

    let unitInput = document.createElement("input");
    unitInput.type = "text";
    unitInput.className = "input";
    unitInput.placeholder = "Unit";

    let priceInput = document.createElement("input");
    priceInput.type = "number";
    priceInput.className = "input";
    priceInput.placeholder = "Price per qty";

    let priorityInput = document.createElement("input");
    priorityInput.type = "number";
    priorityInput.className = "input";
    priorityInput.placeholder = "1 to 5";

    card.appendChild(makeRow("Item :", [itemInput]));
    card.appendChild(makeRow("Quantity :", [qtyInput, unitInput]));
    card.appendChild(makeRow("Price :", [priceInput]));
    card.appendChild(makeRow("Priority :", [priorityInput]));

    let buttons = document.createElement("div");
    buttons.className = "buttons";

    let remove = document.createElement("button");
    remove.className = "remove_btn";
    remove.textContent = "Remove Item";
    remove.addEventListener("click", () => {
        document.getElementById("cards").removeChild(card);
        const itemName = itemInput.value.trim();
        if (itemName !== "") {
            remove_from_List(itemName);
        }
    });

    let add = document.createElement("button");
    add.className = "add_btn";
    add.textContent = "Add to the list";
    add.addEventListener("click", () => {
        // Input validation
        if (
            !itemInput.value.trim() ||
            isNaN(parseFloat(qtyInput.value)) ||
            isNaN(parseFloat(priceInput.value)) ||
            isNaN(parseInt(priorityInput.value))
        ) {
            alert("Please fill all fields correctly.");
            return;
        }

        add_to_the_list(card, add);
    });

    buttons.appendChild(remove);
    buttons.appendChild(add);
    card.appendChild(buttons);
    document.getElementById("cards").appendChild(card);
}

function add_to_the_list(card, addButton) {
    let inputs = card.querySelectorAll("input");
    let data = {
        item: inputs[0].value,
        qty: parseFloat(inputs[1].value),
        price: parseFloat(inputs[3].value),
        priority: parseInt(inputs[4].value)
    };

    fetch("/add_item", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    })
    .then(res => res.json())
    .then(response => {
        console.log("Added:", response);
        Swal.fire({
            icon: 'success',
            title: 'Item Added!',
            text: response.message || "Item successfully added to the list.",
            confirmButtonColor: '#ffa500'
        });

        addButton.textContent = "Edit";
        addButton.disabled = false;

        // Clone and replace the button to remove previous event listener
        const newButton = addButton.cloneNode(true);
        addButton.parentNode.replaceChild(newButton, addButton);

        newButton.addEventListener("click", () => {
            // Remove the old item
            fetch("/remove_item", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ item: data.item })
            })
            .then(() => {
                // Re-add updated item
                const updatedData = {
                    item: inputs[0].value,
                    qty: parseFloat(inputs[1].value),
                    price: parseFloat(inputs[3].value),
                    priority: parseInt(inputs[4].value)
                };

                return fetch("/add_item", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(updatedData)
                });
            })
            .then(res => res.json())
            .then(updatedRes => {
                Swal.fire({
                    icon: 'success',
                    title: 'Item Updated!',
                    text: updatedRes.message || "Changes saved successfully.",
                    confirmButtonColor: '#ffa500'
                });

                newButton.textContent = "Edit";
                newButton.disabled = false;
            })
            .catch(err => console.error("Edit failed:", err));
        });
    })
    .catch(err => console.error("Error:", err));
}



function remove_from_List(itemName) {
    fetch('/remove_item', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ item: itemName })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Item removed:', data);
        Swal.fire({
            icon: 'info',
            title: 'Item Removed',
            text: data.message || "Item successfully removed from the list.",
            confirmButtonColor: '#ffa500'
        });

    })
    .catch(error => {
        console.error('Error:', error);
    });
}


function downloadBill() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();

    doc.setFont("helvetica", "normal");
    doc.setFontSize(18);
    doc.text("Optimized Grocery Bill", 14, 20);

    const rows = [];
    const tableRows = document.querySelectorAll("#billTableBody tr");

    tableRows.forEach(row => {
        const cells = row.querySelectorAll("td");
        rows.push([
            cells[0].textContent.replace(/[^\x20-\x7E]/g, '').trim(),
            "Rs. " + cells[1].textContent.replace(/[^\x20-\x7E]/g, '').trim(),
            cells[2].textContent.replace(/[^\x20-\x7E]/g, '').trim(),
            cells[3].textContent.replace(/[^\x20-\x7E]/g, '').trim(),
            "Rs. " + cells[4].textContent.replace(/[^\x20-\x7E]/g, '').trim()
        ]);
    });

    const totalSpent = document.getElementById("totalSpentCell").textContent.replace(/[^\x20-\x7E]/g, '').trim();

    doc.autoTable({
        startY: 30,
        head: [["Item", "Price", "Quantity", "Status", "Total"]],
        body: rows,
        theme: "striped",
        styles: { font: "helvetica", fontSize: 12 }
    });

    doc.setFontSize(14);
    doc.text(`Total Spent: Rs. ${totalSpent}`, 14, doc.lastAutoTable.finalY + 10);

    doc.save("Optimized_Grocery_Bill.pdf");
}


let chartInstance;

function submit() {
    const budget = parseFloat(document.getElementById("budget").value.trim());
    if (isNaN(budget) || budget < 0) {
        Swal.fire("Invalid Budget", "Enter a valid amount!", "warning");
        return;
    }

    fetch('/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ budget })
    })
    .then(response => response.json())
    .then(data => {
        const result = data.Final_list;
        const stats = data.Statistics;

        const tableBody = document.getElementById("billTableBody");
        tableBody.innerHTML = '';
        let totalSpent = 0;

        result.forEach(item => {
            const total = item.price * item.qty;
            totalSpent += total;

            const row = `<tr>
                <td>${item.item}</td>
                <td>₹${item.price}</td>
                <td>${item.qty}</td>
                <td>${item.status}</td>
                <td>₹${total.toFixed(2)}</td>
            </tr>`;
            tableBody.innerHTML += row;
        });

        document.getElementById("totalSpentCell").innerText = `₹${totalSpent}`;

        // Draw Chart
        if (chartInstance) chartInstance.destroy();
        const ctx = document.getElementById('statsChart').getContext('2d');
        chartInstance = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['Spent', 'Savings'],
                datasets: [{
                    data: [stats.spent, stats.savings],
                    backgroundColor: ['#ff7043', '#66bb6a']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' },
                    title: { display: true, text: 'Spending Summary' }
                }
            }
        });

        document.getElementById("resultContainer").style.display = 'block';
    });
}


document.addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        document.getElementById("submit").click(); 
    }
});
