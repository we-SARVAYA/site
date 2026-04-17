// ===== Active Footer Link (current page highlight) =====
(function markActiveFooterLink() {
    const norm = (p) => {
        p = (p || '').toLowerCase().replace(/\/index\.html$/, '/');
        if (p !== '/' && p.endsWith('/')) p = p.slice(0, -1);
        return p;
    };
    const currentPath = norm(window.location.pathname);

    const tag = () => {
        document.querySelectorAll('.footer-col a[href]').forEach((a) => {
            const url = new URL(a.href, window.location.origin);
            if (url.origin !== window.location.origin) return;
            if (url.hash) return;
            if (norm(url.pathname) === currentPath) {
                a.setAttribute('aria-current', 'page');
            }
        });
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', tag);
    } else {
        tag();
    }
})();

// ===== Smooth Scroll (Lenis) =====
(function initSmoothScroll() {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const lenisScript = document.createElement('script');
    lenisScript.src = 'https://unpkg.com/lenis@1.1.13/dist/lenis.min.js';
    lenisScript.onload = () => {
        const lenis = new Lenis({
            duration: 1.2,
            easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
            smoothWheel: true,
            smoothTouch: false,
            touchMultiplier: 1.5,
        });
        window.lenis = lenis;

        function raf(time) {
            lenis.raf(time);
            requestAnimationFrame(raf);
        }
        requestAnimationFrame(raf);

        document.querySelectorAll('a[href^="#"]').forEach(link => {
            link.addEventListener('click', (e) => {
                const id = link.getAttribute('href');
                if (!id || id === '#') return;
                const target = document.querySelector(id);
                if (!target) return;
                e.preventDefault();
                lenis.scrollTo(target, { offset: -80 });
            });
        });
    };
    document.head.appendChild(lenisScript);
})();

// ===== Smooth Page Transitions =====
(function initPageTransitions() {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const overlay = document.createElement('div');
    overlay.className = 'page-transition-overlay';
    overlay.setAttribute('aria-hidden', 'true');
    overlay.innerHTML = '<div class="page-transition-mark"><span>SARVAYA</span><i></i></div>';
    document.body.appendChild(overlay);

    // First visit (or cold load) gets a brief brand hold before the wipe-up.
    // Subsequent in-session navigations wipe immediately so nav feels snappy.
    const FIRST_VISIT_KEY = 'sarvaya_visited';
    const firstVisit = !sessionStorage.getItem(FIRST_VISIT_KEY);
    try { sessionStorage.setItem(FIRST_VISIT_KEY, '1'); } catch (_) {}

    if (!reduceMotion) {
        // Only clear is-enter when the overlay's OWN pageEnter wipe finishes.
        // Child-mark animations (markIn/markOut) bubble animationend too —
        // filtering by animationName prevents them from cutting pageEnter short.
        overlay.addEventListener('animationend', (e) => {
            if (e.animationName === 'pageEnter' && overlay.classList.contains('is-enter')) {
                overlay.classList.remove('is-enter');
            }
        }, { once: false });

        if (firstVisit) {
            overlay.classList.add('is-hold');
            setTimeout(() => {
                overlay.classList.remove('is-hold');
                overlay.classList.add('is-enter');
            }, 300);
        } else {
            requestAnimationFrame(() => {
                overlay.classList.add('is-enter');
            });
        }
    }

    function handleLink(link) {
        const href = link.getAttribute('href');
        if (!href) return;
        if (href.startsWith('#') || href.startsWith('http') || href.startsWith('mailto:') || href.startsWith('tel:') || href.startsWith('javascript:') || link.target === '_blank') return;

        link.addEventListener('click', (e) => {
            if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
            e.preventDefault();
            if (reduceMotion) {
                window.location.href = href;
                return;
            }
            overlay.classList.remove('is-enter');
            overlay.classList.add('is-leave');
            setTimeout(() => { window.location.href = href; }, 520);
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('a[href]').forEach(handleLink);
    });

    // Handle back/forward cache restore (iOS Safari, Firefox) - replay enter
    window.addEventListener('pageshow', (e) => {
        if (e.persisted) {
            overlay.classList.remove('is-leave');
            overlay.classList.add('is-enter');
        }
    });
})();

// ===== Custom Cursor =====
const cursorDot = document.getElementById('cursorDot');
const cursorRing = document.getElementById('cursorRing');
let mouseX = 0, mouseY = 0;
let ringX = 0, ringY = 0;

if (cursorDot && cursorRing && window.matchMedia('(pointer: fine)').matches) {
    document.addEventListener('mousemove', (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
        cursorDot.style.left = mouseX + 'px';
        cursorDot.style.top = mouseY + 'px';
    });

    // Smooth lag for the ring
    function animateRing() {
        ringX += (mouseX - ringX) * 0.15;
        ringY += (mouseY - ringY) * 0.15;
        cursorRing.style.left = ringX + 'px';
        cursorRing.style.top = ringY + 'px';
        requestAnimationFrame(animateRing);
    }
    animateRing();

    // Hover expansion on interactive elements
    const hoverTargets = 'a, button, .service-card, .work-card, .pf-card, .blog-card, .faq-question';

    document.querySelectorAll(hoverTargets).forEach(el => {
        el.addEventListener('mouseenter', () => {
            cursorDot.classList.add('hovering');
            cursorRing.classList.add('hovering');
        });
        el.addEventListener('mouseleave', () => {
            cursorDot.classList.remove('hovering');
            cursorRing.classList.remove('hovering');
        });
    });
}

// ===== Navbar Scroll Effect & Scroll Progress Bar =====
const navbar = document.getElementById('navbar');
const scrollProgress = document.getElementById('scrollProgress');

window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }

    // Update scroll progress bar
    if (scrollProgress) {
        const scrollTop = window.scrollY;
        const docHeight = document.documentElement.scrollHeight - window.innerHeight;
        const percent = (scrollTop / docHeight) * 100;
        scrollProgress.style.width = percent + '%';
    }
});

// ===== Mobile Menu Toggle =====
const hamburger = document.getElementById('hamburger');
const mobileMenu = document.getElementById('mobileMenu');

if (hamburger && mobileMenu) {
    hamburger.addEventListener('click', () => {
        hamburger.classList.toggle('active');
        mobileMenu.classList.toggle('active');
        document.body.style.overflow = mobileMenu.classList.contains('active') ? 'hidden' : '';
    });

    mobileMenu.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            hamburger.classList.remove('active');
            mobileMenu.classList.remove('active');
            document.body.style.overflow = '';
        });
    });
}

// ===== FAQ Accordion =====
document.querySelectorAll('.faq-question').forEach(button => {
    button.addEventListener('click', () => {
        const item = button.parentElement;
        const isActive = item.classList.contains('active');

        // Close all FAQ items
        document.querySelectorAll('.faq-item').forEach(faq => {
            faq.classList.remove('active');
            faq.querySelector('.faq-question').setAttribute('aria-expanded', 'false');
        });

        // Open the clicked one (if it wasn't already open)
        if (!isActive) {
            item.classList.add('active');
            button.setAttribute('aria-expanded', 'true');
        }
    });
});

// ===== Scroll Reveal Animations =====
const observerOptions = {
    root: null,
    rootMargin: '0px 0px -60px 0px',
    threshold: 0.1
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
        }
    });
}, observerOptions);

// Assign animation types to different element groups
function initAnimations() {
    // Fade up - default for most elements
    const fadeUp = [
        '.section-label', '.section-title', '.about-description',
        '.about-detail', '.twentyfour-badge', '.twentyfour-title',
        '.twentyfour-desc', '.twentyfour-features', '.twentyfour-cta',
        '.view-all-btn', '.hero-services',
        '.intro-block', '.includes-row',
        '.feature-card', '.step-card', '.page-hero__title',
        '.page-hero__desc', '.page-hero__label', '.page-hero__cta',
        '.metric-block'
    ];

    // Slide from left - about left column
    const slideLeft = ['.about-left'];

    // Slide from right - about right column, contact info
    const slideRight = ['.about-right', '.contact-info'];

    // Scale in - work cards, portfolio cards (dramatic entrance)
    const scaleIn = [
        '.work-card', '.work-card--featured', '.pf-card'
    ];

    // Blur in - blog cards, FAQ items (softer feel)
    const blurIn = ['.blog-card', '.blog-page-card', '.faq-item'];

    // Staggered fade up - service cards (cascading grid)
    const staggered = ['.service-card'];

    // Apply fade-up
    fadeUp.forEach(sel => {
        document.querySelectorAll(sel).forEach((el, i) => {
            el.classList.add('fade-up');
            el.style.transitionDelay = `${i * 0.05}s`;
            observer.observe(el);
        });
    });

    // Apply slide-left
    slideLeft.forEach(sel => {
        document.querySelectorAll(sel).forEach(el => {
            el.classList.add('slide-left');
            observer.observe(el);
        });
    });

    // Apply slide-right
    slideRight.forEach(sel => {
        document.querySelectorAll(sel).forEach(el => {
            el.classList.add('slide-right');
            observer.observe(el);
        });
    });

    // Apply scale-in with stagger
    scaleIn.forEach(sel => {
        document.querySelectorAll(sel).forEach((el, i) => {
            el.classList.add('scale-in');
            el.style.transitionDelay = `${i * 0.1}s`;
            observer.observe(el);
        });
    });

    // Apply blur-in with stagger
    blurIn.forEach(sel => {
        document.querySelectorAll(sel).forEach((el, i) => {
            el.classList.add('blur-in');
            el.style.transitionDelay = `${i * 0.08}s`;
            observer.observe(el);
        });
    });

    // Apply staggered fade-up for service cards (diagonal cascade)
    staggered.forEach(sel => {
        document.querySelectorAll(sel).forEach((el, i) => {
            el.classList.add('fade-up');
            el.style.transitionDelay = `${i * 0.07}s`;
            observer.observe(el);
        });
    });

    // About cards - alternate slide directions
    document.querySelectorAll('.about-card').forEach((el, i) => {
        el.classList.add(i % 2 === 0 ? 'slide-right' : 'fade-up');
        el.style.transitionDelay = `${i * 0.15}s`;
        observer.observe(el);
    });

    // Contact info cards
    document.querySelectorAll('.contact-info__card').forEach((el, i) => {
        el.classList.add('fade-up');
        el.style.transitionDelay = `${i * 0.08}s`;
        observer.observe(el);
    });
}

// ===== Parallax-lite on scroll =====
function initParallax() {
    const hero = document.querySelector('.hero-title');
    const heroSub = document.querySelector('.hero-subtitle');

    if (!hero) return;

    window.addEventListener('scroll', () => {
        const scrollY = window.scrollY;
        if (scrollY < window.innerHeight) {
            const speed = scrollY * 0.3;
            hero.style.transform = `translateY(${speed * 0.4}px)`;
            if (heroSub) heroSub.style.transform = `translateY(${speed * 0.2}px)`;
        }
    }, { passive: true });
}

// ===== Smooth Scroll for Anchor Links =====
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const targetId = this.getAttribute('href');
        if (targetId === '#') return;

        const target = document.querySelector(targetId);
        if (target) {
            e.preventDefault();
            const navHeight = navbar.offsetHeight;
            const targetPos = target.getBoundingClientRect().top + window.scrollY - navHeight - 20;

            window.scrollTo({
                top: targetPos,
                behavior: 'smooth'
            });
        }
    });
});

// ===== Dynamic Copyright Year =====
const yearEl = document.getElementById('currentYear');
if (yearEl) yearEl.textContent = new Date().getFullYear();

// ===== Testimonials Infinite Scroll =====
const testimonialsTrack = document.getElementById('testimonialsTrack');
if (testimonialsTrack) {
    const cards = Array.from(testimonialsTrack.children);
    cards.forEach(card => {
        testimonialsTrack.appendChild(card.cloneNode(true));
    });
}

// ===== GA4 Analytics (consent-gated) =====
function initGA4() {
    if (!window.GA_MEASUREMENT_ID || window.GA_MEASUREMENT_ID === 'G-KZ28NS98BR') return;
    if (document.getElementById('ga4-script')) return;

    const script = document.createElement('script');
    script.id = 'ga4-script';
    script.async = true;
    script.src = 'https://www.googletagmanager.com/gtag/js?id=' + window.GA_MEASUREMENT_ID;
    document.head.appendChild(script);

    script.onload = function () {
        window.dataLayer = window.dataLayer || [];
        function gtag() { window.dataLayer.push(arguments); }
        gtag('js', new Date());
        gtag('config', window.GA_MEASUREMENT_ID, {
            anonymize_ip: true,
            cookie_flags: 'SameSite=None;Secure'
        });
        window.gtag = gtag;
    };
}

if (localStorage.getItem('sarvaya_cookie_consent') === 'accepted') {
    initGA4();
}

// ===== Cookie Consent Banner =====
const cookieBanner = document.getElementById('cookieBanner');
const cookieAccept = document.getElementById('cookieAccept');
const cookieDecline = document.getElementById('cookieDecline');

if (cookieBanner && !localStorage.getItem('sarvaya_cookie_consent')) {
    setTimeout(() => cookieBanner.classList.add('visible'), 1500);
}

if (cookieAccept) {
    cookieAccept.addEventListener('click', () => {
        localStorage.setItem('sarvaya_cookie_consent', 'accepted');
        cookieBanner.classList.remove('visible');
        initGA4();
    });
}

if (cookieDecline) {
    cookieDecline.addEventListener('click', () => {
        localStorage.setItem('sarvaya_cookie_consent', 'declined');
        cookieBanner.classList.remove('visible');
    });
}

// ===== WhatsApp Float Button =====
// The element is visible by default via CSS; JS just keeps the .visible class
// wired up for any code elsewhere that relies on it.
const whatsappFloat = document.getElementById('whatsappFloat');
if (whatsappFloat) {
    whatsappFloat.classList.add('visible');
}

// ===== Animated Counter for Metrics =====
function animateCounters() {
    const counters = document.querySelectorAll('.metric-number[data-target]');
    if (!counters.length) return;

    const counterObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                const target = parseInt(el.dataset.target, 10);
                const duration = 2000;
                const startTime = performance.now();

                function updateCount(currentTime) {
                    const elapsed = currentTime - startTime;
                    const progress = Math.min(elapsed / duration, 1);
                    const eased = 1 - Math.pow(1 - progress, 3);
                    el.textContent = Math.floor(eased * target);

                    if (progress < 1) {
                        requestAnimationFrame(updateCount);
                    } else {
                        el.textContent = target;
                    }
                }

                requestAnimationFrame(updateCount);
                counterObserver.unobserve(el);
            }
        });
    }, { threshold: 0.3 });

    counters.forEach(counter => counterObserver.observe(counter));
}

// ===== 3D Tilt Effect on Cards =====
function initTiltCards() {
    if (window.matchMedia('(pointer: coarse)').matches) return;

    const cards = document.querySelectorAll('.work-card, .pf-card, .service-card, .feature-card');
    cards.forEach(card => {
        card.classList.add('tilt-card');

        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            const rotateX = ((y - centerY) / centerY) * -6;
            const rotateY = ((x - centerX) / centerX) * 6;

            card.style.transform = `perspective(800px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-4px)`;
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = '';
        });
    });
}

// ===== Magnetic Button Effect =====
function initMagneticButtons() {
    if (window.matchMedia('(pointer: coarse)').matches) return;

    const buttons = document.querySelectorAll('.hero-cta, .nav-cta, .page-hero__cta, .twentyfour-cta, .view-all-btn');
    buttons.forEach(btn => {
        btn.classList.add('magnetic-btn');

        btn.addEventListener('mousemove', (e) => {
            const rect = btn.getBoundingClientRect();
            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;
            btn.style.transform = `translate(${x * 0.2}px, ${y * 0.2}px)`;
        });

        btn.addEventListener('mouseleave', () => {
            btn.style.transform = '';
        });
    });
}

// ===== Floating Particles in Hero =====
function initHeroParticles() {
    const hero = document.querySelector('.hero');
    if (!hero) return;

    const container = document.createElement('div');
    container.className = 'hero-particles';
    hero.appendChild(container);

    for (let i = 0; i < 20; i++) {
        const particle = document.createElement('div');
        particle.className = 'hero-particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.animationDuration = (8 + Math.random() * 12) + 's';
        particle.style.animationDelay = (Math.random() * 10) + 's';
        particle.style.width = (2 + Math.random() * 2) + 'px';
        particle.style.height = particle.style.width;
        container.appendChild(particle);
    }
}

// ===== Card Glow Follow Effect =====
function initCardGlow() {
    if (window.matchMedia('(pointer: coarse)').matches) return;

    document.querySelectorAll('.service-card').forEach(card => {
        if (card.querySelector('.card-glow')) return;
        const glow = document.createElement('div');
        glow.className = 'card-glow';
        card.appendChild(glow);

        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width) * 100;
            const y = ((e.clientY - rect.top) / rect.height) * 100;
            card.style.setProperty('--glow-x', x + '%');
            card.style.setProperty('--glow-y', y + '%');
        });
    });
}

// ===== Section Dividers (animate on scroll) =====
function initSectionDividers() {
    document.querySelectorAll('.section-divider').forEach(el => {
        observer.observe(el);
    });
}

// ===== Initialize =====
document.addEventListener('DOMContentLoaded', () => {
    initAnimations();
    initParallax();
    animateCounters();
    initTiltCards();
    initMagneticButtons();
    initHeroParticles();
    initCardGlow();
    initSectionDividers();
});
