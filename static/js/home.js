// OIKOS - Landing Page JavaScript

document.addEventListener('DOMContentLoaded', function() {

    // Smooth scroll for navigation links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                const offsetTop = target.offsetTop - 80;
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });

                // Close mobile menu if open
                const navbarCollapse = document.querySelector('.navbar-collapse');
                if (navbarCollapse.classList.contains('show')) {
                    navbarCollapse.classList.remove('show');
                }
            }
        });
    });

    // Navbar background change on scroll
    const navbar = document.querySelector('.navbar');
    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            navbar.classList.add('shadow-lg');
        } else {
            navbar.classList.remove('shadow-lg');
        }
    });

    // Animate elements on scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animated');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Add animation to feature cards
    document.querySelectorAll('.feature-card, .step-card').forEach(card => {
        card.classList.add('animate-on-scroll');
        observer.observe(card);
    });

    // Counter animation for stats (if needed)
    function animateCounter(element, target) {
        let current = 0;
        const increment = target / 50;
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                element.textContent = target + '%';
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(current) + '%';
            }
        }, 20);
    }

    // Add hover effect to cards
    const cards = document.querySelectorAll('.feature-card, .step-card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px) scale(1.02)';
        });
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });

    // Parallax effect for hero section
    window.addEventListener('scroll', function() {
        const scrolled = window.pageYOffset;
        const parallaxElements = document.querySelectorAll('.floating-card');

        parallaxElements.forEach((el, index) => {
            const speed = 0.5 + (index * 0.1);
            el.style.transform = `translateY(${scrolled * speed * 0.1}px)`;
        });
    });

    // Copy to clipboard for donation data
    const donationInfo = document.querySelector('.donation-info');
    if (donationInfo) {
        donationInfo.style.cursor = 'pointer';
        donationInfo.addEventListener('click', function() {
            const cbu = this.querySelector('.text-primary').textContent;

            // Create temporary input
            const tempInput = document.createElement('input');
            tempInput.value = cbu;
            document.body.appendChild(tempInput);
            tempInput.select();

            try {
                document.execCommand('copy');

                // Show feedback
                const originalHTML = this.innerHTML;
                this.innerHTML = '<p class="text-success mb-0"><i class="bi bi-check-circle"></i> ¡Copiado al portapapeles!</p>';

                setTimeout(() => {
                    this.innerHTML = originalHTML;
                }, 2000);
            } catch (err) {
                console.error('Error al copiar:', err);
            }

            document.body.removeChild(tempInput);
        });
    }

    // Add active class to nav links based on scroll position
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav-link[href^="#"]');

    function highlightNavLink() {
        let scrollY = window.pageYOffset;

        sections.forEach(section => {
            const sectionHeight = section.offsetHeight;
            const sectionTop = section.offsetTop - 100;
            const sectionId = section.getAttribute('id');

            if (scrollY > sectionTop && scrollY <= sectionTop + sectionHeight) {
                navLinks.forEach(link => {
                    link.classList.remove('active', 'text-primary');
                    if (link.getAttribute('href') === `#${sectionId}`) {
                        link.classList.add('active', 'text-primary');
                    }
                });
            }
        });
    }

    window.addEventListener('scroll', highlightNavLink);

    // Button hover effects
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        button.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });

    // Add loading state to CTA buttons
    const ctaButtons = document.querySelectorAll('a[href*="registro"]');
    ctaButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!this.classList.contains('loading-btn')) {
                this.classList.add('loading-btn');
                const originalText = this.innerHTML;
                this.innerHTML = '<span class="loading me-2"></span>Cargando...';

                // Remove loading after navigation starts
                setTimeout(() => {
                    this.innerHTML = originalText;
                    this.classList.remove('loading-btn');
                }, 1000);
            }
        });
    });

    // Lazy loading for images (if any are added)
    const images = document.querySelectorAll('img[data-src]');
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
                imageObserver.unobserve(img);
            }
        });
    });

    images.forEach(img => imageObserver.observe(img));

    // Console message
    console.log('%cOIKOS', 'font-size: 32px; font-weight: bold; color: #6366f1; text-shadow: 2px 2px 4px rgba(0,0,0,0.2);');
    console.log('%cSistema de Gestión Financiera para Iglesias', 'font-size: 14px; color: #6b7280;');
    console.log('%c¡Gracias por visitar!', 'font-size: 12px; color: #10b981;');
});

// Prevent default form submission for demo
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function(e) {
        // Only prevent if it's a demo form (add demo class if needed)
        if (this.classList.contains('demo-form')) {
            e.preventDefault();
            alert('Esta es una demostración. En producción, el formulario se enviará normalmente.');
        }
    });
});
