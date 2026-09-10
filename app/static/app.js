const form = document.querySelector('#translate-form');
const source = document.querySelector('#source-text');
const count = document.querySelector('#char-count');
const startView = document.querySelector('#start-view');
const resultView = document.querySelector('#result-view');
const output = document.querySelector('#translation-output');
const originalOutput = document.querySelector('#original-output');
const loading = document.querySelector('#loading');
const startError = document.querySelector('#start-error');
const resultError = document.querySelector('#result-error');
const copyButton = document.querySelector('#copy-button');
const correctionsPanel = document.querySelector('#corrections-panel');
const correctionsList = document.querySelector('#corrections-list');
const alternativesPanel = document.querySelector('#alternatives-panel');
const alternativesList = document.querySelector('#alternatives-list');
const settingsDialog = document.querySelector('#settings-dialog');
const settingsForm = document.querySelector('#settings-form');
const settingsStatus = document.querySelector('#settings-status');
const modelName = document.querySelector('#model-name');

fetch('/api/config')
  .then((response) => response.json())
  .then((data) => { applySettings(data); })
  .catch(() => { modelName.textContent = 'configured model'; });

const historyId = new URLSearchParams(window.location.search).get('history');
if (historyId) {
  fetch(`/api/history/${encodeURIComponent(historyId)}`)
    .then((response) => response.json().then((data) => ({response, data})))
    .then(({response, data}) => {
      if (!response.ok) throw new Error(data.detail || 'Could not load history entry.');
      renderResult(data, data.original_text);
      startView.hidden = true; resultView.hidden = false;
    })
    .catch((error) => showError(startError, error.message));
}

document.querySelector('#settings-button').addEventListener('click', async () => {
  settingsStatus.textContent = '';
  if (!settingsDialog.open) settingsDialog.showModal();
});
document.querySelector('#close-settings').addEventListener('click', () => settingsDialog.close());
document.querySelector('#cancel-settings').addEventListener('click', () => settingsDialog.close());
settingsForm.addEventListener('submit', async (event) => {
  event.preventDefault(); settingsStatus.textContent = 'Saving…';
  const payload = { model: document.querySelector('#settings-model').value, fallback_model: document.querySelector('#settings-fallback-model').value, direction: document.querySelector('#settings-direction').value, prompt: document.querySelector('#settings-prompt').value, api_keys: {} };
  payload.provider = document.querySelector('#settings-provider').value;
  for (const provider of ['openai', 'claude', 'gemini', 'grok', 'deepseek']) {
    const value = document.querySelector(`#settings-${provider}-key`).value.trim();
    if (value) payload.api_keys[provider] = value;
  }
  try {
    const response = await fetch('/api/config', { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Could not save configuration.');
    applySettings(data); settingsStatus.textContent = 'Saved'; setTimeout(() => settingsDialog.close(), 400);
  } catch (error) { settingsStatus.textContent = error.message; }
});

function applySettings(data) {
  modelName.textContent = `${data.provider || 'openai'} · ${data.model || 'configured model'}`;
  document.querySelector('#settings-provider').value = data.provider || 'openai';
  document.querySelector('#settings-model').value = data.model || '';
  document.querySelector('#settings-fallback-model').value = data.fallback_model || '';
  document.querySelector('#settings-direction').value = data.direction || 'auto';
  document.querySelector('#settings-prompt').value = data.prompt || '';
  for (const provider of ['openai', 'claude', 'gemini', 'grok', 'deepseek']) {
    const field = document.querySelector(`#settings-${provider}-key`);
    field.value = data.api_keys?.[provider] || '';
    field.placeholder = 'Enter API key';
  }
}

source.addEventListener('input', () => { count.textContent = `${source.value.length} / 5000`; });
source.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const text = source.value.trim();
  if (!text) return showError(startError, 'Enter some text to translate.');
  hideError(startError); hideError(resultError);
  loading.hidden = false;
  form.querySelector('button').disabled = true;
  try {
    const response = await fetch('/api/translate', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text}) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'The text could not be translated.');
    renderResult(data, text);
    startView.hidden = true; resultView.hidden = false; window.scrollTo({top: 0, behavior: 'smooth'});
  } catch (error) { showError(startView.hidden ? resultError : startError, error.message); }
  finally { loading.hidden = true; form.querySelector('button').disabled = false; }
});

function renderResult(data, originalText) {
    output.textContent = data.translation;
    originalOutput.textContent = data.corrected_text || originalText;
    alternativesList.replaceChildren();
    for (const alternative of data.alternatives || []) {
      const row = document.createElement('div'); row.className = 'alternative';
      const text = document.createElement('span'); text.textContent = alternative;
      const copy = document.createElement('button'); copy.type = 'button'; copy.className = 'small-copy'; copy.textContent = 'Copy';
      copy.addEventListener('click', async () => {
        try { await copyText(alternative); copy.textContent = 'Copied'; setTimeout(() => { copy.textContent = 'Copy'; }, 1400); }
        catch { showError(resultError, 'Could not access the clipboard.'); }
      });
      row.append(text, copy); alternativesList.append(row);
    }
    alternativesPanel.hidden = !(data.alternatives && data.alternatives.length);
    correctionsList.replaceChildren();
    for (const correction of data.corrections || []) {
      const row = document.createElement('div'); row.className = 'correction';
      const wrong = document.createElement('span'); wrong.className = 'wrong'; wrong.textContent = correction.original;
      const arrow = document.createElement('span'); arrow.className = 'arrow'; arrow.textContent = '→';
      const right = document.createElement('span'); right.className = 'right'; right.textContent = correction.corrected;
      row.append(wrong, arrow, right); correctionsList.append(row);
    }
    correctionsPanel.hidden = !(data.corrections && data.corrections.length);
    document.querySelector('#language-label').textContent = data.detected_language === 'es' ? 'English' : 'Spanish';
    document.querySelector('#latency').textContent = `${data.latency_ms} ms`;
}

copyButton.addEventListener('click', async () => {
  try { await copyText(output.textContent); copyButton.textContent = 'Copied'; setTimeout(() => { copyButton.textContent = 'Copy'; }, 1400); }
  catch { showError(resultError, 'Could not access the clipboard.'); }
});

document.querySelector('#new-translation').addEventListener('click', () => { resultView.hidden = true; startView.hidden = false; source.focus(); });
function showError(element, message) { element.textContent = message; element.hidden = false; }
function hideError(element) { element.hidden = true; }

async function copyText(text) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }
  } catch (_) {
    // Fall back to the legacy method when the page is served over plain HTTP.
  }
  const helper = document.createElement('textarea');
  helper.value = text;
  helper.setAttribute('readonly', '');
  helper.style.position = 'fixed'; helper.style.opacity = '0';
  document.body.appendChild(helper); helper.select(); helper.setSelectionRange(0, helper.value.length);
  const copied = document.execCommand('copy');
  helper.remove();
  if (!copied) throw new Error('Clipboard access denied');
}
