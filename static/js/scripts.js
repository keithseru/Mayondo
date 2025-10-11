// MayondoWood Custom Scripts

document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Confirm delete actions
    const deleteButtons = document.querySelectorAll('[data-confirm-delete]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });

    // Initialize currency formatting
    initializeCurrencyFormatting();

    // Only prevent negative values on input
    const numberInputs = document.querySelectorAll('input[type="number"]');
    numberInputs.forEach(input => {
        input.addEventListener('input', function() {
            if (parseFloat(this.value) < 0) {
                this.value = '';
            }
        });
    });

    // Formset management
    initializeFormsets();

    // Stock indicator colors
    updateStockIndicators();

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Print functionality
    const printButtons = document.querySelectorAll('.btn-print');
    printButtons.forEach(button => {
        button.addEventListener('click', function() {
            window.print();
        });
    });

    // Filter toggle
    const filterToggle = document.querySelector('#filterToggle');
    if (filterToggle) {
        filterToggle.addEventListener('click', function() {
            const filterSection = document.querySelector('#filterSection');
            filterSection.classList.toggle('d-none');
        });
    }

    // Auto-update delivery fee display
    const deliveryCheckbox = document.querySelector('input[name="delivery_required"]');
    if (deliveryCheckbox) {
        deliveryCheckbox.addEventListener('change', function() {
            updateDeliveryFeeDisplay();
        });
    }

    // Variant selector - auto-fill price
    const variantSelects = document.querySelectorAll('select[name*="variant"]');
    variantSelects.forEach(select => {
        select.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            const priceText = selectedOption.text.match(/UGX ([\d,]+)/);
            if (priceText) {
                const price = priceText[1].replace(/,/g, '');
                const priceInput = this.closest('.formset-row, form').querySelector('input[name*="unit_price"], input[name*="price"]');
                if (priceInput) {
                    priceInput.value = price;
                }
            }
        });
    });
});

// Currency formatting that switches input type
function initializeCurrencyFormatting() {
    const currencyInputs = document.querySelectorAll(
        'input[type="number"][name*="price"], input[type="number"][name*="amount"]'
    );
    
    currencyInputs.forEach(input => {
        // Skip if already initialized
        if (input.dataset.currencyInitialized) return;
        input.dataset.currencyInitialized = 'true';
        
        // Store original attributes
        input.dataset.originalType = 'number';
        input.dataset.originalMin = input.min || '0';
        input.dataset.originalStep = input.step || '1';
        
        // Format with commas
        function formatNumber(num) {
            if (!num || num === '') return '';
            return parseFloat(num).toLocaleString('en-US');
        }
        
        // Remove commas
        function unformatNumber(str) {
            if (!str) return '';
            return str.replace(/,/g, '');
        }
        
        // When field gets focus, switch to number type
        input.addEventListener('focus', function() {
            // Switch to number type for editing
            this.type = 'number';
            this.min = this.dataset.originalMin;
            this.step = this.dataset.originalStep;
            
            // Remove commas
            this.value = unformatNumber(this.value);
        });
        
        // When field loses focus, switch to text type and format
        input.addEventListener('blur', function() {
            const rawValue = unformatNumber(this.value);
            
            if (rawValue && rawValue !== '') {
                const numValue = parseFloat(rawValue);
                
                if (!isNaN(numValue) && numValue > 0) {
                    const rounded = Math.round(numValue);
                    
                    // Switch to text type to display commas
                    this.type = 'text';
                    this.value = formatNumber(rounded);
                    
                    // Store the numeric value for form submission
                    this.dataset.numericValue = rounded;
                } else {
                    // Invalid value
                    this.value = '';
                    delete this.dataset.numericValue;
                }
            } else {
                // Empty value
                this.type = 'text';
                this.value = '';
                delete this.dataset.numericValue;
            }
        });
        
        // Format initial value
        if (input.value && input.value !== '') {
            const numValue = parseFloat(input.value);
            if (!isNaN(numValue)) {
                input.type = 'text';
                input.value = formatNumber(numValue);
                input.dataset.numericValue = numValue;
            }
        }
        
        // Before form submission, restore numeric values
        const form = input.closest('form');
        if (form && !form.dataset.currencySubmitHandler) {
            form.dataset.currencySubmitHandler = 'true';
            
            form.addEventListener('submit', function(e) {
                // Find all price/amount inputs and restore numeric values
                const priceInputs = this.querySelectorAll('input[name*="price"], input[name*="amount"]');
                
                priceInputs.forEach(priceInput => {
                    // If it has a stored numeric value, use it
                    if (priceInput.dataset.numericValue) {
                        priceInput.value = priceInput.dataset.numericValue;
                    } else {
                        // Otherwise, clean any commas
                        priceInput.value = unformatNumber(priceInput.value);
                    }
                    
                    // Make sure it's a number type for submission
                    priceInput.type = 'number';
                });
            });
        }
    });
}

// Formset management functions
function initializeFormsets() {
    const addButtons = document.querySelectorAll('.add-form-row');
    addButtons.forEach(button => {
        button.addEventListener('click', addFormRow);
    });

    const deleteButtons = document.querySelectorAll('.delete-form-row');
    deleteButtons.forEach(button => {
        button.addEventListener('click', deleteFormRow);
    });
}

function addFormRow(e) {
    e.preventDefault();
    const formset = this.closest('.formset');
    const totalForms = formset.querySelector('input[name$="-TOTAL_FORMS"]');
    const newFormIndex = parseInt(totalForms.value);
    
    const emptyForm = formset.querySelector('.empty-form');
    if (emptyForm) {
        const newForm = emptyForm.cloneNode(true);
        newForm.classList.remove('empty-form', 'd-none');
        newForm.classList.add('formset-row');
        
        // Update form index in all fields
        newForm.innerHTML = newForm.innerHTML.replace(/__prefix__/g, newFormIndex);
        
        // Insert before add button
        this.parentElement.insertBefore(newForm, this);
        
        // Update total forms count
        totalForms.value = newFormIndex + 1;
        
        // Reinitialize event listeners and currency formatting
        initializeFormsets();
        initializeCurrencyFormatting();
    }
}

function deleteFormRow(e) {
    e.preventDefault();
    const row = this.closest('.formset-row');
    const deleteCheckbox = row.querySelector('input[name$="-DELETE"]');
    
    if (deleteCheckbox) {
        deleteCheckbox.checked = true;
        row.classList.add('to-delete');
        row.style.display = 'none';
    } else {
        row.remove();
    }
}

// Update stock indicators
function updateStockIndicators() {
    document.querySelectorAll('[data-stock]').forEach(element => {
        const stock = parseInt(element.dataset.stock);
        const reorderLevel = parseInt(element.dataset.reorder) || 10;
        
        let indicator = element.querySelector('.stock-indicator');
        if (!indicator) {
            indicator = document.createElement('span');
            indicator.className = 'stock-indicator';
            element.prepend(indicator);
        }
        
        if (stock === 0) {
            indicator.classList.add('out');
            indicator.classList.remove('low', 'high');
        } else if (stock <= reorderLevel) {
            indicator.classList.add('low');
            indicator.classList.remove('out', 'high');
        } else {
            indicator.classList.add('high');
            indicator.classList.remove('out', 'low');
        }
    });
}

// Calculate and display delivery fee
function updateDeliveryFeeDisplay() {
    const deliveryCheckbox = document.querySelector('input[name="delivery_required"]');
    const deliveryFeeDisplay = document.querySelector('#deliveryFeeDisplay');
    
    if (!deliveryCheckbox || !deliveryFeeDisplay) return;
    
    if (deliveryCheckbox.checked) {
        // Calculate 5% of subtotal
        let subtotal = 0;
        document.querySelectorAll('.item-total').forEach(el => {
            subtotal += parseFloat(el.textContent.replace(/[^0-9.-]+/g, '')) || 0;
        });
        
        const deliveryFee = Math.round(subtotal * 0.05);
        deliveryFeeDisplay.textContent = `UGX ${deliveryFee.toLocaleString()}`;
        deliveryFeeDisplay.parentElement.classList.remove('d-none');
    } else {
        deliveryFeeDisplay.parentElement.classList.add('d-none');
    }
}

// Calculate row totals in formsets
function calculateRowTotal(row) {
    const quantityInput = row.querySelector('input[name*="quantity"]');
    const priceInput = row.querySelector('input[name*="price"], input[name*="unit_price"]');
    const discountInput = row.querySelector('input[name*="discount"]');
    const totalDisplay = row.querySelector('.row-total');
    
    if (!quantityInput || !priceInput || !totalDisplay) return;
    
    const quantity = parseFloat(quantityInput.value) || 0;
    const price = parseFloat(priceInput.value) || 0;
    const discount = parseFloat(discountInput?.value) || 0;
    
    const subtotal = quantity * price;
    const discountAmount = subtotal * (discount / 100);
    const total = subtotal - discountAmount;
    
    totalDisplay.textContent = `UGX ${Math.round(total).toLocaleString()}`;
    
    // Update grand total
    updateGrandTotal();
}

// Update grand total
function updateGrandTotal() {
    const grandTotalDisplay = document.querySelector('#grandTotal');
    if (!grandTotalDisplay) return;
    
    let grandTotal = 0;
    document.querySelectorAll('.row-total').forEach(el => {
        const value = parseFloat(el.textContent.replace(/[^0-9.-]+/g, '')) || 0;
        grandTotal += value;
    });
    
    grandTotalDisplay.textContent = `UGX ${Math.round(grandTotal).toLocaleString()}`;
    
    // Update delivery fee if applicable
    updateDeliveryFeeDisplay();
}

// Export table to CSV
function exportTableToCSV(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    let csv = [];
    const rows = table.querySelectorAll('tr');
    
    rows.forEach(row => {
        const cols = row.querySelectorAll('td, th');
        const csvRow = [];
        cols.forEach(col => {
            csvRow.push('"' + col.textContent.trim().replace(/"/g, '""') + '"');
        });
        csv.push(csvRow.join(','));
    });
    
    const csvContent = csv.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename + '.csv';
    a.click();
    window.URL.revokeObjectURL(url);
}

// Search filter
function filterTable(inputId, tableId) {
    const input = document.getElementById(inputId);
    const table = document.getElementById(tableId);
    
    if (!input || !table) return;
    
    input.addEventListener('keyup', function() {
        const filter = this.value.toLowerCase();
        const rows = table.querySelectorAll('tbody tr');
        
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(filter) ? '' : 'none';
        });
    });
}