document.addEventListener('DOMContentLoaded', () => {
  const socket = io();

  const suggestForm = document.getElementById('suggest-form');
  const suggestOutput = document.getElementById('suggest-output');
  const baselineForm = document.getElementById('baseline-form');
  const baselineOutput = document.getElementById('baseline-output');
  const events = document.getElementById('events');

  function logEvent(type, payload) {
    const li = document.createElement('li');
    li.innerHTML = `<strong>${type}</strong> <small>${new Date().toLocaleTimeString()}</small><br><code>${JSON.stringify(payload)}</code>`;
    events.prepend(li);
  }

  socket.on('connect', () => logEvent('socket:connected', {sid: socket.id}));
  socket.on('suggestion_event', (data) => {
    renderSuggestions(data);
    logEvent('suggestion_event', data);
  });
  socket.on('baseline_event', (data) => {
    renderBaseline(data);
    logEvent('baseline_event', data);
  });

  suggestForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(suggestForm);
    const payload = {
      project_type: fd.get('project_type'),
      language: fd.get('language'),
      use_case: fd.get('use_case')
    };
    const res = await fetch('/api/suggest', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    renderSuggestions(data);
  });

  baselineForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(baselineForm);
    const features = (fd.get('features') || '').split(',').map(s => s.trim()).filter(Boolean);
    const res = await fetch('/api/baseline-check', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ features })
    });
    const data = await res.json();
    renderBaseline(data);
  });

  function renderSuggestions(data) {
    suggestOutput.innerHTML = '';
    (data.suggestions || []).forEach(block => {
      const div = document.createElement('div');
      div.className = 'block';
      div.innerHTML = `<div class="title">${block.title}</div>` +
        '<ul>' + block.items.map(i => `<li>${i}</li>`).join('') + '</ul>';
      suggestOutput.appendChild(div);
    });
  }

  function renderBaseline(data) {
    baselineOutput.innerHTML = '';
    (data.results || data?.results || data?.results)?.forEach?.(() => {}); // noop guard
    const list = data.results || [];
    list.forEach(f => {
      const div = document.createElement('div');
      div.className = 'block';
      div.innerHTML = `<div class="title">${f.title} <small>(${f.id})</small></div>
        <div>Status: <strong>${f.baseline}</strong></div>
        <div><a href="${f.docs}" target="_blank" rel="noopener">Docs</a></div>
        <div>${f.notes}</div>`;
      baselineOutput.appendChild(div);
    });
  }
});
