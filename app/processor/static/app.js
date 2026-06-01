async function setLevel(level) {
  await fetch(`/level/${level}`, { method: 'POST' });
  updateButtons(level);
}

function updateButtons(level) {
  ['off', 'low', 'medium', 'high'].forEach(l => {
    document.getElementById(`btn-${l}`).className = '';
  });
  document.getElementById(`btn-${level}`).className = `active-${level}`;

  const badge = document.getElementById('level-badge');
  badge.className = `level-badge badge-${level}`;
  badge.textContent = level.toUpperCase();
}

async function poll() {
  try {
    const lvlRes = await fetch('/level');
    const lvl = await lvlRes.json();
    updateButtons(lvl.level);

    const statsRes = await fetch('/stats');
    const stats = await statsRes.json();

    const podEl = document.getElementById('pod-count');
    const queueEl = document.getElementById('queue-depth');

    podEl.textContent = stats.pods;
    queueEl.textContent = stats.queue_depth;

    podEl.className = 'card-value';
    if (stats.pods >= 6) podEl.classList.add('high');
    else if (stats.pods >= 3) podEl.classList.add('medium');
    else if (stats.pods >= 1) podEl.classList.add('low');

  } catch (e) {
    console.error('Poll error:', e);
  }
}

setInterval(poll, 2000);
poll();