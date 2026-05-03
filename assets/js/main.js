// Jackson Lab - Main JS

// Mobile nav toggle
document.addEventListener('DOMContentLoaded', function () {
  const toggle = document.getElementById('nav-toggle');
  const navUl = document.querySelector('nav#nav > ul');
  if (toggle && navUl) {
    toggle.addEventListener('click', function () {
      navUl.classList.toggle('open');
    });
  }

  // Mobile sub-menu toggles
  document.querySelectorAll('nav#nav > ul > li > a').forEach(function (link) {
    link.addEventListener('click', function (e) {
      if (window.innerWidth <= 768) {
        const li = this.parentElement;
        if (li.querySelector('ul')) {
          e.preventDefault();
          li.classList.toggle('open');
        }
      }
    });
  });

  // Mark active page
  const current = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('nav#nav a').forEach(function (a) {
    const href = a.getAttribute('href');
    if (href === current || (current === '' && href === 'index.html')) {
      a.parentElement.classList.add('active');
    }
  });
});
