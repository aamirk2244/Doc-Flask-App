// ui.js — small UI helpers (placeholder for future UI code)
var AppUI = (function(){
  function flashMessage(text, type){
    // placeholder: server-side flashes are used; implement client-side if needed
    console.log('flash', type, text);
  }

  // Auto-hide server-side flash alerts after a short delay
  function initAutoDismiss(delayMs){
    if (typeof delayMs === 'undefined') delayMs = 4000;
    // run on DOM ready
    var run = function(){
      var alerts = document.querySelectorAll('.alert');
      alerts.forEach(function(alert){
        // schedule dismissal
        setTimeout(function(){
          if (window.bootstrap && bootstrap.Alert){
            // fade then close
            alert.classList.add('fade');
            try{ bootstrap.Alert.getOrCreateInstance(alert).close(); }catch(e){ alert.remove(); }
          } else {
            // fallback: remove element
            alert.remove();
          }
        }, delayMs);
      });
    };

    if (document.readyState === 'loading'){
      document.addEventListener('DOMContentLoaded', run);
    } else {
      run();
    }
  }

  return { flashMessage: flashMessage, initAutoDismiss: initAutoDismiss };
})();

// initialize auto-dismiss with default 4s
AppUI.initAutoDismiss();
