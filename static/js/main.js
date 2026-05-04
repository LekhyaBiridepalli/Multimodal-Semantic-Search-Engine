// Main JavaScript File

$(document).ready(function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);

    // Smooth scroll for anchor links
    $('a[href*="#"]').on('click', function(e) {
        if (this.hash !== '') {
            e.preventDefault();
            const hash = this.hash;
            $('html, body').animate({
                scrollTop: $(hash).offset().top - 80
            }, 800);
        }
    });

    // Add ripple effect to buttons
    $('.btn').on('click', function(e) {
        let ripple = $('<span class="ripple"></span>');
        let posX = e.pageX - $(this).offset().left;
        let posY = e.pageY - $(this).offset().top;
        
        ripple.css({
            left: posX,
            top: posY
        });
        
        $(this).append(ripple);
        
        setTimeout(function() {
            ripple.remove();
        }, 600);
    });

    // Form validation
    $('form').on('submit', function(e) {
        let isValid = true;
        
        $(this).find('[required]').each(function() {
            if (!$(this).val()) {
                $(this).addClass('is-invalid');
                isValid = false;
            } else {
                $(this).removeClass('is-invalid');
            }
        });
        
        return isValid;
    });

    // Password strength meter
    $('#password').on('keyup', function() {
        let password = $(this).val();
        let strength = 0;
        
        if (password.length >= 8) strength += 25;
        if (password.match(/[a-z]+/)) strength += 25;
        if (password.match(/[A-Z]+/)) strength += 25;
        if (password.match(/[0-9]+/)) strength += 25;
        
        $('#password-strength').css('width', strength + '%');
        
        if (strength <= 25) {
            $('#password-strength').removeClass('bg-success bg-warning').addClass('bg-danger');
        } else if (strength <= 50) {
            $('#password-strength').removeClass('bg-success bg-danger').addClass('bg-warning');
        } else {
            $('#password-strength').removeClass('bg-warning bg-danger').addClass('bg-success');
        }
    });

    // Search input with debounce
    let searchTimeout;
    $('#search-input').on('keyup', function() {
        clearTimeout(searchTimeout);
        let query = $(this).val();
        
        if (query.length < 3) return;
        
        searchTimeout = setTimeout(function() {
            performSearch(query);
        }, 500);
    });

    // Lazy loading images
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
    }

    // Copy to clipboard
    window.copyToClipboard = function(text) {
        navigator.clipboard.writeText(text).then(function() {
            showNotification('Copied to clipboard!', 'success');
        }).catch(function() {
            showNotification('Failed to copy', 'danger');
        });
    };

    // Show notification
    window.showNotification = function(message, type = 'info') {
        const notification = $(`
            <div class="alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3 animate__animated animate__fadeInRight" 
                 role="alert" style="z-index: 9999;">
                <i class="fas fa-${type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `);
        
        $('body').append(notification);
        
        setTimeout(() => {
            notification.fadeOut('slow', function() {
                $(this).remove();
            });
        }, 3000);
    };

    // Toggle password visibility
    $('.toggle-password').on('click', function() {
        let input = $($(this).data('target'));
        let icon = $(this).find('i');
        
        if (input.attr('type') === 'password') {
            input.attr('type', 'text');
            icon.removeClass('fa-eye').addClass('fa-eye-slash');
        } else {
            input.attr('type', 'password');
            icon.removeClass('fa-eye-slash').addClass('fa-eye');
        }
    });

    // Delete confirmation
    $('.delete-confirm').on('click', function(e) {
        if (!confirm('Are you sure you want to delete this item?')) {
            e.preventDefault();
        }
    });

    // Infinite scroll
    let loading = false;
    $(window).on('scroll', function() {
        if ($(window).scrollTop() + $(window).height() > $(document).height() - 100) {
            if (!loading && $('#load-more').length) {
                loading = true;
                $('#load-more').click();
            }
        }
    });
});

// Perform search (AJAX)
function performSearch(query) {
    $.ajax({
        url: '/api/search',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({query: query}),
        success: function(data) {
            displaySearchResults(data);
        },
        error: function(xhr, status, error) {
            showNotification('Search failed: ' + error, 'danger');
        }
    });
}

// Display search results
function displaySearchResults(data) {
    let html = '';
    
    data.results.forEach(item => {
        html += `
            <div class="search-result-item">
                <h5>${item.title}</h5>
                <p>${item.description}</p>
                <a href="${item.url}" target="_blank">Learn more</a>
            </div>
        `;
    });
    
    $('#search-results').html(html);
}

// Chart initialization
function initChart(elementId, type, data, options) {
    const ctx = document.getElementById(elementId).getContext('2d');
    return new Chart(ctx, {
        type: type,
        data: data,
        options: options
    });
}

// Add ripple effect styles
$('<style>')
    .prop('type', 'text/css')
    .html(`
        .btn {
            position: relative;
            overflow: hidden;
        }
        
        .ripple {
            position: absolute;
            border-radius: 50%;
            background-color: rgba(255, 255, 255, 0.7);
            width: 100px;
            height: 100px;
            margin-top: -50px;
            margin-left: -50px;
            animation: ripple 0.6s ease-out;
            transform: scale(0);
            pointer-events: none;
        }
        
        @keyframes ripple {
            to {
                transform: scale(4);
                opacity: 0;
            }
        }
        
        .is-invalid {
            border-color: #dc3545 !important;
        }
        
        .password-strength-meter {
            height: 5px;
            margin-top: 10px;
            border-radius: 5px;
            overflow: hidden;
        }
        
        .search-result-item {
            padding: 15px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            transition: all 0.3s ease;
        }
        
        .search-result-item:hover {
            background: rgba(255,255,255,0.05);
            transform: translateX(5px);
        }
    `)
    .appendTo('head');

// Get CSRF token from meta tag or cookie
function getCSRFToken() {
    // Try to get from meta tag first
    let token = document.querySelector('meta[name="csrf-token"]');
    if (token) {
        return token.getAttribute('content');
    }
    return '';
}

// Add CSRF token to all AJAX requests
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", getCSRFToken());
        }
    }
});