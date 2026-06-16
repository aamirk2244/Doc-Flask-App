// forms.js — handles form submit behaviors, loading state, and confirmation modal
(function(){
  function init(){
    // Restore any buttons left in a loading/disabled state (e.g., when navigating back)
    function restoreButtons(){
      // restore any submit buttons that were put into a loading state
      document.querySelectorAll('button[type=submit]').forEach(function(btn){
        if (btn.dataset.origText) {
          btn.innerText = btn.dataset.origText;
          delete btn.dataset.origText;
        }
        btn.disabled = false;
      });
      // also handle buttons that might not be type=submit but have loading text
      document.querySelectorAll('button[data-loading-text]').forEach(function(btn){
        if (btn.dataset.origText) {
          btn.innerText = btn.dataset.origText;
          delete btn.dataset.origText;
        }
        btn.disabled = false;
      });
      // clear confirmed flags on forms
      document.querySelectorAll('form[data-confirmed]').forEach(function(f){ delete f.dataset.confirmed; });
    }
    // run once during init
    restoreButtons();
    var confirmModalEl = document.getElementById('confirmModal');
    var confirmModal = confirmModalEl ? new bootstrap.Modal(confirmModalEl, {}) : null;
    var confirmMessageEl = confirmModalEl ? confirmModalEl.querySelector('.modal-body') : null;
    var confirmTitleEl = confirmModalEl ? confirmModalEl.querySelector('.modal-title') : null;
    var confirmOkBtn = confirmModalEl ? confirmModalEl.querySelector('#confirmModalOk') : null;

    document.querySelectorAll('form').forEach(function(form){
      form.addEventListener('submit', function(event){
        // avoid re-entering after user confirmed
        if (form.dataset.confirmed === '1') {
          // show loading state for the first submit after confirm
          var btn2 = form.querySelector('button[type=submit]');
          if(btn2){
            btn2.disabled = true;
            var txt2 = btn2.getAttribute('data-loading-text') || 'Processing...';
            btn2.dataset.origText = btn2.innerText;
            btn2.innerText = txt2;
          }
          return true;
        }

        var btn = form.querySelector('button[type=submit]');
        if (btn) {
          var confirmMsg = btn.getAttribute('data-confirm');
          var confirmTitle = btn.getAttribute('data-confirm-title') || 'Confirm';
          if (confirmMsg && confirmModal) {
            // prevent immediate submit and show modal
            event.preventDefault();
            if (confirmTitleEl) confirmTitleEl.textContent = confirmTitle;
            if (confirmMessageEl) confirmMessageEl.textContent = confirmMsg;

            // when user clicks OK, mark form as confirmed and submit
            var onOk = function(){
              confirmOkBtn.removeEventListener('click', onOk);
              form.dataset.confirmed = '1';
              confirmModal.hide();
              form.submit();
            };
            confirmOkBtn.addEventListener('click', onOk);
            confirmModal.show();
            return false;
          }

          // no confirm required, proceed to show loading state
          btn.disabled = true;
          var txt = btn.getAttribute('data-loading-text') || 'Processing...';
          btn.dataset.origText = btn.innerText;
          btn.innerText = txt;
        }
      });
    });

    // Also restore buttons when page is shown (handles bfcache/back navigation)
    window.addEventListener('pageshow', function(){ restoreButtons(); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
