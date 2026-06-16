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

// KIBOR fetch handler
(function(){
  function renderResults(data){
    var container = document.getElementById('kiborResult');
    if(!container) return;
    container.innerHTML = '';
    if(!data || !data.results || data.results.length === 0){
      container.innerHTML = '<p class="text-muted">No KIBOR data fetched.</p>';
      return;
    }
    var table = document.createElement('table');
    table.className = 'table table-sm';
    var thead = document.createElement('thead');
    thead.innerHTML = '<tr><th>Month</th><th>3M</th><th>6M</th><th>1Y</th></tr>';
    table.appendChild(thead);
    var tbody = document.createElement('tbody');
    data.results.forEach(function(r){
      var tr = document.createElement('tr');
      var month = document.createElement('td');
      month.textContent = r.month_key;
      tr.appendChild(month);
      var c3 = document.createElement('td'); c3.textContent = r.rates['3M'] || '';
      var c6 = document.createElement('td'); c6.textContent = r.rates['6M'] || '';
      var c1 = document.createElement('td'); c1.textContent = r.rates['1Y'] || '';
      tr.appendChild(c3); tr.appendChild(c6); tr.appendChild(c1);
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    container.appendChild(table);
  }

  function initKibor(){
    var btn = document.getElementById('fetchKiborBtn');
    if(!btn) return;
    var spinner = document.getElementById('kiborSpinner');
    btn.addEventListener('click', function(ev){
      ev.preventDefault();
      btn.disabled = true;
      if(spinner) spinner.style.display = '';
      fetch('/fetch-kibor', { method: 'POST', headers: {'Accept':'application/json'} })
        .then(function(res){ return res.json(); })
        .then(function(data){
          if(spinner) spinner.style.display = 'none';
          btn.disabled = false;
          if(data && data.ok){
            renderResults(data);
          } else {
            var container = document.getElementById('kiborResult');
            container.innerHTML = '<div class="text-danger">Error fetching KIBOR: ' + (data && data.error ? data.error : 'unknown') + '</div>';
          }
        }).catch(function(err){
          if(spinner) spinner.style.display = 'none';
          btn.disabled = false;
          var container = document.getElementById('kiborResult');
          container.innerHTML = '<div class="text-danger">Error fetching KIBOR.</div>';
        });
    });
  }

  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', initKibor);
  } else { initKibor(); }
})();
