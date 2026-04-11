document.addEventListener('DOMContentLoaded', () => {
    // 1. Sticky Header Logic
    const header = document.getElementById('main-header');
    
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
    });

    // 2. Scroll Animation Logic
    const revealElements = document.querySelectorAll('.reveal-up, .reveal-left, .reveal-right');

    const revealOnScroll = () => {
        const windowHeight = window.innerHeight;
        const revealPoint = 100; // Point before bottom to trigger

        revealElements.forEach(element => {
            const elementTop = element.getBoundingClientRect().top;

            if (elementTop < windowHeight - revealPoint) {
                element.classList.add('active');
            }
        });
    };

    // Initial check and attach to scroll
    revealOnScroll();
    window.addEventListener('scroll', revealOnScroll);

    // 3. Mobile Menu Toggle (Basic implementation)
    const mobileToggle = document.querySelector('.mobile-menu-toggle');
    const mainNav = document.querySelector('.main-nav');
    
    // For demonstration purposes. In a real app, this would toggle classes 
    // to show/hide a mobile menu overlay.
    if(mobileToggle){
        mobileToggle.addEventListener('click', () => {
            alert('Mobile menu toggle activated. Implement overlay here.');
        });
    }
});
