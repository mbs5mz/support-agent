const messages = document.querySelector('#messages');
const activity = document.querySelector('#activity');
const input = document.querySelector('#input');
const form = document.querySelector('#form');
const send = document.querySelector('#send');
const mode = document.querySelector('#mode');
const voiceNote = document.querySelector('#voice-note');
const suggestions = document.querySelectorAll('.suggestion');
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
  suggestions.forEach(button => button.disabled = true);
  try {
    const response = await fetch('/api/chat', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({history})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Request failed');
    bubble(data.answer, 'assistant');
    history.push({role: 'assistant', content: data.answer});
    mode.textContent = data.mode;
    for (const call of data.activity) {
      const empty = activity.querySelector('.empty-activity');
      if (empty) empty.remove();
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
    suggestions.forEach(button => button.disabled = false);
    input.focus();
  }
}

form.addEventListener('submit', event => {event.preventDefault(); submit(input.value);});
suggestions.forEach(button => button.addEventListener('click', () => {input.value = button.dataset.prompt; input.focus();}));
document.querySelector('#reset').addEventListener('click', () => {history = []; messages.innerHTML = ''; activity.innerHTML = '<div class="empty-activity"><span>✦</span><p>No tools called yet.</p></div>'; bubble('Hi there! I’m happy to help with an order, return, refund, or policy question. What’s on your mind?', 'assistant'); input.focus();});

const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const mic = document.querySelector('#mic');
let recorder = null;
let recordingTimer = null;

function voiceError(error) {
  if (error === 'not-allowed' || error === 'service-not-allowed' || error === 'NotAllowedError' || error === 'PermissionDeniedError') return 'Microphone access was denied. Allow it for localhost in your browser or system settings, then try again.';
  if (error === 'audio-capture' || error === 'NotFoundError' || error === 'NotReadableError') return 'No available microphone was found. Check your input device and try again.';
  if (error === 'network') return 'The browser speech service could not connect. Try a supported browser, or configure OPENAI_API_KEY for recorded transcription.';
  if (error === 'no-speech') return 'I did not hear any speech. Please try again.';
  return `Speech could not start (${error || 'unknown error'}). Try typing or another browser.`;
}

function enableBrowserRecognition() {
  if (!Recognition) {
    mic.disabled = true;
    voiceNote.textContent = 'Speech recognition is unavailable here. Configure OPENAI_API_KEY for recorded transcription, or type your question.';
    return;
  }
  voiceNote.textContent = 'Voice uses your browser’s speech service. Press the microphone to speak.';
  const recognition = new Recognition();
  recognition.lang = 'en-US';
  recognition.onresult = event => {input.value = event.results[0][0].transcript; voiceNote.textContent = 'Transcribed. Review the text, then press Send.'; input.focus();};
  recognition.onerror = event => {voiceNote.textContent = voiceError(event.error);};
  recognition.onend = () => {mic.disabled = false; mic.classList.remove('recording'); mic.setAttribute('aria-pressed', 'false');};
  mic.addEventListener('click', () => {
    mic.disabled = true;
    mic.classList.add('recording');
    mic.setAttribute('aria-pressed', 'true');
    voiceNote.textContent = 'Listening…';
    try {recognition.start();} catch (error) {voiceNote.textContent = voiceError(error.name); mic.disabled = false; mic.classList.remove('recording');}
  });
}

function enableRecordedTranscription() {
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    enableBrowserRecognition();
    return;
  }
  const mimeType = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'].find(type => MediaRecorder.isTypeSupported(type));
  if (!mimeType) {enableBrowserRecognition(); return;}
  mic.title = 'Start or stop recording';
  mic.setAttribute('aria-label', 'Start recording');
  voiceNote.textContent = 'Voice clips are transcribed through the configured OpenAI API. Press the microphone to start.';
  mic.addEventListener('click', async () => {
    if (recorder?.state === 'recording') {recorder.stop(); return;}
    mic.disabled = true;
    voiceNote.textContent = 'Requesting microphone access…';
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({audio: true});
      const chunks = [];
      recorder = new MediaRecorder(stream, {mimeType});
      recorder.ondataavailable = event => {if (event.data.size) chunks.push(event.data);};
      recorder.onerror = event => {voiceNote.textContent = voiceError(event.error?.name);};
      recorder.onstop = async () => {
        clearTimeout(recordingTimer);
        stream.getTracks().forEach(track => track.stop());
        mic.disabled = true;
        mic.classList.remove('recording');
        mic.setAttribute('aria-pressed', 'false');
        mic.setAttribute('aria-label', 'Start recording');
        voiceNote.textContent = 'Transcribing recording…';
        try {
          const blob = new Blob(chunks, {type: mimeType});
          const response = await fetch('/api/transcribe', {method: 'POST', headers: {'Content-Type': mimeType.split(';')[0]}, body: blob});
          const data = await response.json();
          if (!response.ok) throw new Error(data.error || 'Transcription failed');
          input.value = data.text;
          voiceNote.textContent = 'Transcribed. Review the text, then press Send.';
          input.focus();
        } catch (error) {voiceNote.textContent = error.message;}
        finally {recorder = null; mic.disabled = false;}
      };
      recorder.start();
      mic.disabled = false;
      mic.classList.add('recording');
      mic.setAttribute('aria-pressed', 'true');
      mic.setAttribute('aria-label', 'Stop recording');
      voiceNote.textContent = 'Recording… press the microphone again to stop (20 seconds maximum).';
      recordingTimer = setTimeout(() => {if (recorder?.state === 'recording') recorder.stop();}, 20000);
    } catch (error) {
      stream?.getTracks().forEach(track => track.stop());
      voiceNote.textContent = voiceError(error.name);
      mic.disabled = false;
    }
  });
}

fetch('/api/config').then(response => response.json()).then(config => {
  if (config.serverTranscription) enableRecordedTranscription();
  else enableBrowserRecognition();
}).catch(enableBrowserRecognition);
