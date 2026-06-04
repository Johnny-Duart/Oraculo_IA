document.addEventListener('DOMContentLoaded', function () {
  // Placeholder for future UI interactions (mobile menu, theme toggle, etc.)
  document.querySelectorAll('[data-toggle="mobile-menu"]').forEach(function(btn){
    btn.addEventListener('click', function(){
      var menu = document.getElementById('mobile-menu');
      if(menu) menu.classList.toggle('hidden');
    });
  });
});
