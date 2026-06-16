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

// Action panel switching
(function(){
  function showPanel(id){
    document.querySelectorAll('.action-panel').forEach(function(p){ p.style.display = 'none'; });
    var el = document.getElementById(id);
    if(el) el.style.display = '';
  }

  function initActionList(){
    var list = document.getElementById('actionList');
    if (!list) return;
    list.querySelectorAll('[data-target]').forEach(function(btn){
      btn.addEventListener('click', function(){
        // mark active
        list.querySelectorAll('.list-group-item').forEach(function(b){ b.classList.remove('active'); });
        btn.classList.add('active');
        var target = btn.getAttribute('data-target');
        showPanel(target);
      });
    });
    // show default
    var active = list.querySelector('.list-group-item.active');
    if (active) showPanel(active.getAttribute('data-target'));
  }

  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', initActionList);
  } else { initActionList(); }
})();
