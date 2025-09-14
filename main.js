// Hamburger menu toggle
document.addEventListener('DOMContentLoaded', function() {
    const navToggle = document.getElementById('nav-toggle');
    const navMenu = document.getElementById('nav-menu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });
    }
    
    // Close modal when clicking outside
    const modal = document.getElementById('editModal');
    if (modal) {
        window.addEventListener('click', function(event) {
            if (event.target === modal) {
                closeModal();
            }
        });
    }
});

// Transaction management functions
function editTransaction(id) {
    // Fetch transaction data
    fetch(`/api/transactions/${id}`)
        .then(response => response.json())
        .then(transaction => {
            // Populate the edit form
            document.getElementById('editId').value = transaction.id;
            document.getElementById('editTitle').value = transaction.title;
            document.getElementById('editDescription').value = transaction.description || '';
            document.getElementById('editAmount').value = transaction.amount;
            document.getElementById('editType').value = transaction.type;
            document.getElementById('editDate').value = transaction.date;
            
            // Show the modal
            document.getElementById('editModal').style.display = 'block';
        })
        .catch(error => {
            console.error('Error fetching transaction:', error);
            alert('Error loading transaction data');
        });
}

function deleteTransaction(id) {
    if (confirm('Are you sure you want to delete this transaction?')) {
        fetch(`/api/transactions/${id}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Remove the transaction item from the DOM
                const transactionItem = document.querySelector(`.transaction-item[data-id="${id}"]`);
                if (transactionItem) {
                    transactionItem.remove();
                }
                
                // If we're on the dashboard, reload to update balance
                if (window.location.pathname === '/') {
                    window.location.reload();
                }
            } else {
                alert('Error deleting transaction');
            }
        })
        .catch(error => {
            console.error('Error deleting transaction:', error);
            alert('Error deleting transaction');
        });
    }
}

// Modal functions
function closeModal() {
    document.getElementById('editModal').style.display = 'none';
}

// Close modal when clicking the X
document.querySelector('.close')?.addEventListener('click', closeModal);

// Handle edit form submission
document.getElementById('editForm')?.addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = {
        id: document.getElementById('editId').value,
        title: document.getElementById('editTitle').value,
        description: document.getElementById('editDescription').value,
        amount: document.getElementById('editAmount').value,
        type: document.getElementById('editType').value,
        date: document.getElementById('editDate').value
    };
    
    fetch(`/api/transactions/${formData.id}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Close the modal and reload the page
            closeModal();
            window.location.reload();
        } else {
            alert('Error updating transaction');
        }
    })
    .catch(error => {
        console.error('Error updating transaction:', error);
        alert('Error updating transaction');
    });
});