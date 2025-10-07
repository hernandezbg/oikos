// OIKOS - Modern UI Interactions

document.addEventListener('DOMContentLoaded', function() {

    // Mobile Sidebar Toggle
    initializeMobileSidebar();

    // Add fade-in animation to cards on page load
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        setTimeout(() => {
            card.style.transition = 'all 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });

    // Sidebar active link highlight
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.sidebar .nav-link');
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });

    // Add ripple effect to buttons
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            ripple.classList.add('ripple-effect');
            this.appendChild(ripple);

            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;

            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';

            setTimeout(() => ripple.remove(), 600);
        });
    });

    // Auto-dismiss alerts after 7 seconds with countdown
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        // Crear barra de progreso y contador
        const countdownContainer = document.createElement('div');
        countdownContainer.className = 'alert-countdown-container';
        countdownContainer.innerHTML = `
            <div class="d-flex align-items-center gap-2 mt-2 pt-2" style="border-top: 1px solid rgba(0,0,0,0.1);">
                <small class="text-muted">Se cerrará en <strong class="countdown-number">7</strong>s</small>
                <div class="progress flex-grow-1" style="height: 4px;">
                    <div class="progress-bar countdown-progress" role="progressbar" style="width: 100%; transition: width 100ms linear;"></div>
                </div>
            </div>
        `;
        alert.appendChild(countdownContainer);

        const countdownNumber = alert.querySelector('.countdown-number');
        const progressBar = alert.querySelector('.countdown-progress');

        let timeLeft = 7;
        let progress = 100;

        // Actualizar cada 100ms para animación suave
        const interval = setInterval(() => {
            progress -= (100 / 70); // 7000ms / 100ms = 70 pasos
            progressBar.style.width = Math.max(0, progress) + '%';
        }, 100);

        // Actualizar contador cada segundo
        const counterInterval = setInterval(() => {
            timeLeft--;
            if (timeLeft > 0) {
                countdownNumber.textContent = timeLeft;
            } else {
                clearInterval(counterInterval);
            }
        }, 1000);

        // Cerrar después de 7 segundos
        setTimeout(() => {
            clearInterval(interval);
            clearInterval(counterInterval);
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 7000);

        // Si el usuario cierra manualmente, limpiar intervalos
        alert.addEventListener('closed.bs.alert', () => {
            clearInterval(interval);
            clearInterval(counterInterval);
        });
    });

    // Smooth scroll to top button
    const scrollTopBtn = createScrollTopButton();
    document.body.appendChild(scrollTopBtn);

    window.addEventListener('scroll', () => {
        if (window.pageYOffset > 300) {
            scrollTopBtn.classList.add('show');
        } else {
            scrollTopBtn.classList.remove('show');
        }
    });

    scrollTopBtn.addEventListener('click', () => {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });

    // Form validation feedback
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();

                // Shake effect on invalid form
                form.classList.add('shake');
                setTimeout(() => form.classList.remove('shake'), 500);
            }
            form.classList.add('was-validated');
        });
    });

    // Tooltips initialization
    const tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Add loading state to form submissions
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && form.checkValidity()) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="loading-spinner me-2"></span>Procesando...';
            }
        });
    });

    // Table row click animation
    const tableRows = document.querySelectorAll('.table-hover tbody tr');
    tableRows.forEach(row => {
        row.addEventListener('click', function() {
            this.style.transform = 'scale(0.98)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });

    // Enhanced number formatting for amounts
    const amountElements = document.querySelectorAll('[data-amount]');
    amountElements.forEach(el => {
        const amount = parseFloat(el.getAttribute('data-amount'));
        if (!isNaN(amount)) {
            animateNumber(el, amount);
        }
    });

    // Auto-hide mobile navbar after click
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    if (navbarToggler && navbarCollapse) {
        navLinks.forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth < 768) {
                    navbarCollapse.classList.remove('show');
                }
            });
        });
    }

    // Input focus effects
    const inputs = document.querySelectorAll('.form-control, .form-select');
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('input-focused');
        });
        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('input-focused');
        });
    });

    // Prevent double form submission
    forms.forEach(form => {
        let submitted = false;
        form.addEventListener('submit', function(e) {
            if (submitted) {
                e.preventDefault();
                return false;
            }
            if (form.checkValidity()) {
                submitted = true;
            }
        });
    });
});

// Helper function to create scroll to top button
function createScrollTopButton() {
    const button = document.createElement('button');
    button.className = 'scroll-to-top';
    button.innerHTML = '<i class="bi bi-arrow-up"></i>';
    button.setAttribute('aria-label', 'Volver arriba');

    const style = document.createElement('style');
    style.textContent = `
        .scroll-to-top {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            width: 3rem;
            height: 3rem;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--primary-color, #6366f1), var(--primary-dark, #4f46e5));
            color: white;
            border: none;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            cursor: pointer;
            opacity: 0;
            visibility: hidden;
            transform: scale(0.8);
            transition: all 0.3s ease;
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
        }
        .scroll-to-top.show {
            opacity: 1;
            visibility: visible;
            transform: scale(1);
        }
        .scroll-to-top:hover {
            transform: scale(1.1);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
        }
        .ripple-effect {
            position: absolute;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.6);
            transform: scale(0);
            animation: ripple 0.6s ease-out;
            pointer-events: none;
        }
        @keyframes ripple {
            to {
                transform: scale(4);
                opacity: 0;
            }
        }
        .shake {
            animation: shake 0.5s;
        }
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-10px); }
            75% { transform: translateX(10px); }
        }
        .input-focused {
            transform: scale(1.01);
        }
    `;
    document.head.appendChild(style);

    return button;
}

// Helper function to animate numbers
function animateNumber(element, target) {
    const duration = 1000;
    const start = 0;
    const increment = target / (duration / 16);
    let current = start;

    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            element.textContent = formatCurrency(target);
            clearInterval(timer);
        } else {
            element.textContent = formatCurrency(Math.floor(current));
        }
    }, 16);
}

// Helper function to format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('es-AR', {
        style: 'currency',
        currency: 'ARS',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

// Add keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K: Focus search (if exists)
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('input[name="buscar"]');
        if (searchInput) {
            searchInput.focus();
        }
    }

    // ESC: Close modals and dropdowns
    if (e.key === 'Escape') {
        const openDropdowns = document.querySelectorAll('.dropdown-menu.show');
        openDropdowns.forEach(dropdown => {
            dropdown.classList.remove('show');
        });
    }
});

// Performance: Debounce function for search inputs
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Apply debounce to search inputs
const searchInputs = document.querySelectorAll('input[name="buscar"]');
searchInputs.forEach(input => {
    input.addEventListener('input', debounce(function(e) {
        // Search logic here if needed
        console.log('Searching:', e.target.value);
    }, 300));
});

// Initialize Mobile Sidebar
function initializeMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');

    if (!sidebar || !sidebarToggle) return;

    // Create overlay for mobile
    const overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    overlay.id = 'sidebarOverlay';
    document.body.appendChild(overlay);

    // Toggle sidebar on button click
    sidebarToggle.addEventListener('click', function() {
        sidebar.classList.toggle('show');
        overlay.classList.toggle('show');
        document.body.style.overflow = sidebar.classList.contains('show') ? 'hidden' : '';
    });

    // Close sidebar when clicking overlay
    overlay.addEventListener('click', function() {
        sidebar.classList.remove('show');
        overlay.classList.remove('show');
        document.body.style.overflow = '';
    });

    // Close sidebar when clicking a link (mobile)
    const sidebarLinks = sidebar.querySelectorAll('.nav-link');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth < 768) {
                setTimeout(() => {
                    sidebar.classList.remove('show');
                    overlay.classList.remove('show');
                    document.body.style.overflow = '';
                }, 150);
            }
        });
    });

    // Close sidebar on window resize to desktop
    window.addEventListener('resize', function() {
        if (window.innerWidth >= 768) {
            sidebar.classList.remove('show');
            overlay.classList.remove('show');
            document.body.style.overflow = '';
        }
    });

    // Close sidebar on ESC key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && sidebar.classList.contains('show')) {
            sidebar.classList.remove('show');
            overlay.classList.remove('show');
            document.body.style.overflow = '';
        }
    });
}

// Console message
console.log('%cOIKOS', 'font-size: 24px; font-weight: bold; color: #6366f1;');
console.log('%cSistema de Gestión Financiera para Iglesias', 'font-size: 12px; color: #666;');
