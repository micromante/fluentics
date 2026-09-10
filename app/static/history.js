const list = document.querySelector('#history-list');
const clearButton = document.querySelector('#clear-history');
const error = document.querySelector('#history-error');

loadHistory();

clearButton.addEventListener('click', async () => {
  if (!confirm('Clear all translation history?')) return;
  try {
    const response = await fetch('/api/history', {method: 'DELETE'});
    if (!response.ok) throw new Error('Could not clear history.');
    loadHistory();
  } catch (err) { showError(err.message); }
});

async function loadHistory() {
  try {
    const response = await fetch('/api/history');
    const entries = await response.json();
    if (!response.ok) throw new Error(entries.detail || 'Could not load history.');
    renderHistory(entries);
  } catch (err) { showError(err.message); }
}

function renderHistory(entries) {
  list.replaceChildren();
  clearButton.hidden = !entries.length;
  if (!entries.length) {
    const empty = document.createElement('div'); empty.className = 'empty-history'; empty.textContent = 'No translations yet.'; list.append(empty); return;
  }
  for (const entry of entries) {
    const card = document.createElement('article'); card.className = 'history-entry';
    const link = document.createElement('a'); link.className = 'history-entry-link'; link.href = `/?history=${encodeURIComponent(entry.id)}`;
    const date = document.createElement('div'); date.className = 'history-date'; date.textContent = formatDate(entry.created_at);
    const original = document.createElement('div'); original.className = 'history-original'; original.textContent = entry.corrected_text || entry.original_text;
    const translation = document.createElement('div'); translation.className = 'history-translation'; translation.textContent = entry.translation;
    link.append(date, original, translation);
    const actions = document.createElement('div'); actions.className = 'history-entry-actions';
    const remove = document.createElement('button'); remove.className = 'delete-history'; remove.type = 'button'; remove.textContent = 'Delete';
    remove.addEventListener('click', () => deleteEntry(entry.id));
    actions.append(remove); card.append(link, actions); list.append(card);
  }
}

async function deleteEntry(id) {
  try {
    const response = await fetch(`/api/history/${encodeURIComponent(id)}`, {method: 'DELETE'});
    if (!response.ok) throw new Error('Could not delete history entry.');
    loadHistory();
  } catch (err) { showError(err.message); }
}

function formatDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString();
}

function showError(message) { error.textContent = message; error.hidden = false; }
