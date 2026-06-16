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
      // start scraper (background)
      fetch('/fetch-kibor', { method: 'POST', headers: {'Accept':'application/json'} })
        .then(function(res){ return res.json(); })
        .then(function(data){
          if(!data || !data.ok){
            if(spinner) spinner.style.display = 'none';
            btn.disabled = false;
            var container = document.getElementById('kiborResult');
            container.innerHTML = '<div class="text-danger">Error starting scraper: ' + (data && data.error ? data.error : 'unknown') + '</div>';
            return;
          }
          // poll status
          var pollId = null;
          var container = document.getElementById('kiborResult');
          container.innerHTML = '<div class="text-muted">Scraper started — waiting for progress...</div>';
          function renderLogLines(containerEl, lines){
            containerEl.innerHTML = '';
            if(!lines || !lines.length){
              containerEl.innerHTML = '<div class="text-muted">No logs yet.</div>';
              return;
            }
            var list = document.createElement('div');
            list.className = 'list-group';
            lines.forEach(function(line){
              var item = document.createElement('div');
              item.className = 'list-group-item py-1';
              var text = document.createElement('div');
              text.textContent = line;
              // simple heuristics for styling
              if(/\u2713|Saved|Done|Already downloaded/i.test(line)){
                item.classList.add('text-success');
              } else if(/\u2717|Failed|Error|failed|✗/i.test(line)){
                item.classList.add('text-danger');
              } else if(/skip|Already downloaded|skipping/i.test(line)){
                item.classList.add('text-muted');
              }
              item.appendChild(text);
              list.appendChild(item);
            });
            containerEl.appendChild(list);
            // auto-scroll to bottom
            containerEl.scrollTop = containerEl.scrollHeight;
          }

          function poll(){
            fetch('/scrape/status').then(function(r){ return r.json(); }).then(function(s){
              if(s && s.log){
                renderLogLines(container, s.log);
              } else {
                container.innerHTML = '<div class="text-muted">No logs yet.</div>';
              }

              if(!s.running){
                // finished — stop polling and fetch files
                if(pollId) clearInterval(pollId);
                if(spinner) spinner.style.display = 'none';
                btn.disabled = false;
                fetch('/scrape/files').then(function(r){ return r.json(); }).then(function(f){
                  if(f && typeof f.count === 'number'){
                    var info = document.createElement('div');
                    info.className = 'mt-2';
                    info.innerHTML = '<strong>Done.</strong> PDFs found: ' + f.count;
                    container.appendChild(info);

                    if(f.files && f.files.length){
                      var filesList = document.createElement('ul');
                      filesList.className = 'list-unstyled small mt-2';
                      f.files.forEach(function(fname){
                        var li = document.createElement('li');
                        var a = document.createElement('a');
                        a.href = '/static/data/kibor_files/' + encodeURIComponent(fname);
                        a.target = '_blank';
                        a.textContent = fname;
                        li.appendChild(a);
                        filesList.appendChild(li);
                      });
                      container.appendChild(filesList);
                    }
                  }
                }).catch(function(){ /* ignore */ });
              }
            }).catch(function(){
              // network error — stop polling
              if(pollId) clearInterval(pollId);
              if(spinner) spinner.style.display = 'none';
              btn.disabled = false;
              container.innerHTML = '<div class="text-danger">Error polling scraper status.</div>';
            });
          }
          // start immediate poll and interval
          poll();
          pollId = setInterval(poll, 2500);
        }).catch(function(err){
          if(spinner) spinner.style.display = 'none';
          btn.disabled = false;
          var container = document.getElementById('kiborResult');
          container.innerHTML = '<div class="text-danger">Error starting scraper.</div>';
        });
    });
  }

  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', initKibor);
  } else { initKibor(); }
})();
