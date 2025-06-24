    // Global function to display AJAX messages
    function showAjaxMessage(message, type = 'success') {
        const msgBox = document.getElementById('ajax-message-box');
        if (!msgBox) {
            console.warn('AJAX message box element not found!');
            return;
        }
        msgBox.textContent = message;
        // Basic styling based on type (can be expanded)
        if (type === 'success') {
            msgBox.style.backgroundColor = 'rgba(40, 167, 69, 0.9)'; // Green
        } else if (type === 'error') {
            msgBox.style.backgroundColor = 'rgba(220, 53, 69, 0.9)'; // Red
        } else if (type === 'info') {
            msgBox.style.backgroundColor = 'rgba(23, 162, 184, 0.9)'; // Blue
        } else {
            msgBox.style.backgroundColor = 'rgba(0, 0, 0, 0.8)'; // Default dark
        }
        msgBox.style.display = 'block';
        setTimeout(() => {
            msgBox.style.display = 'none';
        }, 3000); // Hide after 3 seconds
    }

    // Function to get CSRF token for Django AJAX calls
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Common AJAX handlers (examples, adapt as needed)
    document.addEventListener('DOMContentLoaded', function() {
        // Example for Add to Cart buttons (from index.html, products.html, product_details.html)
        document.querySelectorAll('.add-to-cart-btn').forEach(button => {
            button.addEventListener('click', function() {
                const productId = this.dataset.productId;
                const productName = this.dataset.productName || 'Product'; // Fallback
                const quantityInput = this.closest('.card-body')?.querySelector('.quantity-input') || document.getElementById('quantity');
                const quantity = quantityInput ? parseInt(quantityInput.value) : 1;

                console.log(`Simulating AJAX for adding ${quantity} of product ${productId} (${productName}) to cart.`);
                showAjaxMessage(`'${productName}' added to cart!`, 'success');

                // In a real Django app, you'd do something like:
                /*
                fetch('/api/cart/add/', { // This URL would be defined in your Django urls.py
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken'), // Important for Django POST requests
                    },
                    body: JSON.stringify({
                        product_id: productId,
                        quantity: quantity
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showAjaxMessage(`${productName} added to cart!`, 'success');
                        // Optional: Update a cart count display
                    } else {
                        showAjaxMessage(`Failed to add ${productName} to cart: ${data.message}`, 'error');
                    }
                })
                .catch(error => {
                    console.error('Error adding to cart:', error);
                    showAjaxMessage('Error adding to cart. Please try again.', 'error');
                });
                */
            });
        });

        // Example for Contact Form submission (from contact.html)
        const contactForm = document.getElementById('contactForm');
        if (contactForm) {
            contactForm.addEventListener('submit', function(event) {
                event.preventDefault();
                console.log('Simulating AJAX for contact form submission.');
                showAjaxMessage('Your message has been sent successfully!', 'success');
                contactForm.reset();
                /*
                // In a real Django app:
                fetch('/api/contact/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken'),
                    },
                    body: JSON.stringify({
                        name: document.getElementById('name').value,
                        email: document.getElementById('email').value,
                        subject: document.getElementById('subject').value,
                        message: document.getElementById('message').value,
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showAjaxMessage('Your message has been sent successfully!', 'success');
                        contactForm.reset();
                    } else {
                        showAjaxMessage(data.message || 'Failed to send message.', 'error');
                    }
                })
                .catch(error => {
                    console.error('Contact form submission error:', error);
                    showAjaxMessage('Error sending message. Please try again.', 'error');
                });
                */
            });
        }
    });
    