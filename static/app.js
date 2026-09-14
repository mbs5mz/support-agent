const messages = document.querySelector('#messages');
const activity = document.querySelector('#activity');
const input = document.querySelector('#input');
const form = document.querySelector('#form');
const send = document.querySelector('#send');
const mode = document.querySelector('#mode');
const voiceNote = document.querySelector('#voice-note');
let history = [];

function bubble(text, role) {
  const el = document.createElement('div');
  el.className = `message ${role}`;
  el.textContent = text;
  messages.append(el);
  messages.scrollTop = messages.scrollHeight;
}

async function submit(text) {
  if (!text.trim()) return;
  bubble(text, 'user');
  history.push({role: 'user', content: text});
  input.value = '';
  send.disabled = true;
  try {
    const response = await fetch('/api/chat', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({history})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Request failed');
    bubble(data.answer, 'assistant');
    history.push({role: 'assistant', content: data.answer});
    mode.textContent = data.mode;
    for (const call of data.activity) {
      if (activity.textContent === 'No tools called yet.') activity.textContent = '';
      const row = document.createElement('div');
      row.className = 'tool-call';
      const title = document.createElement('strong');
      title.textContent = call.tool;
      const detail = document.createElement('pre');
      detail.textContent = JSON.stringify({arguments: call.arguments, result: call.result}, null, 2);
      row.append(title, detail);
      activity.prepend(row);
    }
  } catch (error) {
    bubble(`Sorry, something went wrong: ${error.message}`, 'assistant');
    history.pop();
  } finally {
    send.disabled = false;
    input.focus();
  }
}

form.addEventListener('submit', event => {event.preventDefault(); submit(input.value);});
document.querySelectorAll('.suggestion').forEach(button => button.addEventListener('click', () => submit(button.dataset.prompt)));
document.querySelector('#reset').addEventListener('click', () => {history = []; messages.innerHTML = ''; activity.textContent = 'No tools called yet.'; bubble('Hi! What can I help you with?', 'assistant'); input.focus();});

const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const mic = document.querySelector('#mic');
if (!Recognition) {mic.disabled = true; voiceNote.textContent = 'Speech input is unavailable in this browser; typing still works.';}
else {
  const recognition = new Recognition();
  recognition.lang = 'en-US';
  recognition.onresult = event => {input.value = event.results[0][0].transcript; voiceNote.textContent = 'Transcribed. Press Send to review and submit.'; input.focus();};
  recognition.onerror = () => {voiceNote.textContent = 'Could not capture speech. You can type instead.';};
  recognition.onend = () => {mic.disabled = false;};
  mic.addEventListener('click', () => {mic.disabled = true; voiceNote.textContent = 'Listening…'; recognition.start();});
}
