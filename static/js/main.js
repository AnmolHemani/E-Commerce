// Initialize form validation
document.addEventListener('DOMContentLoaded', function() {
    // Initialize login form validation
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            let isValid = true;
            
            // Validate username
            const username = loginForm.querySelector('input[name="username"]');
            if (username) {
                if (username.value.length < 3) {
                    isValid = false;
                    username.classList.add('is-invalid');
                    showError(username, 'Username must be at least 3 characters');
                } else {
                    username.classList.remove('is-invalid');
                }
            }
            
            // Validate password
            const password = loginForm.querySelector('input[type="password"]');
            if (password) {
                if (password.value.length < 6) {
                    isValid = false;
                    password.classList.add('is-invalid');
                    showError(password, 'Password must be at least 6 characters');
                } else {
                    password.classList.remove('is-invalid');
                }
            }
            
            if (!isValid) {
                e.preventDefault();
            }
        });
    }

    // Initialize other form validations
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        if (form.id !== 'login-form') {
            validateForm(form.id);
        }
    });
});

// Show error message
function showError(input, message) {
    const errorDiv = input.nextElementSibling;
    if (errorDiv && errorDiv.classList.contains('invalid-feedback')) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    }
}

// Product Sorting
document.addEventListener('DOMContentLoaded', function() {
    const sortButtons = document.querySelectorAll('[data-sort]');
    sortButtons.forEach(button => {
        button.addEventListener('click', function() {
            const sortType = this.dataset.sort;
            sortProducts(sortType);
        });
    });
});

function sortProducts(type) {
    const products = document.querySelectorAll('.product-card');
    const productsArray = Array.from(products);
    
    productsArray.sort((a, b) => {
        const priceA = parseFloat(a.dataset.price) || 0;
        const priceB = parseFloat(b.dataset.price) || 0;
        
        if (type === 'price-low') {
            return priceA - priceB;
        } else if (type === 'price-high') {
            return priceB - priceA;
        }
        return 0;
    });
    
    // Reorder products
    productsArray.forEach(product => {
        product.parentElement.appendChild(product);
    });
}

// Add to Cart Animation
function addToCartAnimation(button) {
    const icon = button.querySelector('.bi-cart-plus');
    if (icon) {
        icon.classList.add('animate__animated', 'animate__bounce');
        setTimeout(() => {
            icon.classList.remove('animate__animated', 'animate__bounce');
        }, 1000);
    }
}

// Wishlist Functionality
document.addEventListener('DOMContentLoaded', function() {
    const wishlistButtons = document.querySelectorAll('.wishlist-btn');
    wishlistButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const icon = this.querySelector('.bi-heart');
            if (icon) {
                icon.classList.toggle('bi-heart-fill');
                
                // Add animation
                icon.classList.add('animate__animated', 'animate__pulse');
                setTimeout(() => {
                    icon.classList.remove('animate__animated', 'animate__pulse');
                }, 1000);
                
                // Show toast notification
                showToast('Product added to wishlist', 'success');
            }
        });
    });
});

// Toast Notifications
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    // Remove toast after 3 seconds
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// Initialize all forms
validateForm('login-form');
validateForm('register-form');
