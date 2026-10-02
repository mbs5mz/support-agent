const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
let platform = {aops: [], metrics: [], recent_runs: []};
let history = [];
let activeAop = '';

function setView(name) {
  $$('.view').forEach(view => view.classList.toggle('active', view.id === `view-${name}`));
  $$('.nav-item').forEach(item => item.classList.toggle('active', item.dataset.view === name));
  $('#crumb-current').textContent = name.toUpperCase();
  if (name === 'playground') $('#input').focus();
  window.scrollTo({top: 0, behavior: 'smooth'});
}
$$('.nav-item,.go-view').forEach(button => button.addEventListener('click', () => setView(button.dataset.view)));

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
}

async function loadPlatform() {
  const response = await fetch('/api/platform');
  platform = await response.json();
  $('#metrics').classList.remove('skeleton');
  $('#metrics').innerHTML = platform.metrics.map(item => `<div class="metric"><span>${escapeHtml(item.label)}</span><strong>${escapeHtml(item.value)}</strong><small>${escapeHtml(item.change)}</small></div>`).join('');
  $('#overview-aops').innerHTML = platform.aops.map(aop => `<div class="overview-aop" data-aop="${aop.id}"><div><strong>${escapeHtml(aop.name)}</strong><span>${escapeHtml(aop.version)} · ${aop.tools.length} tool${aop.tools.length === 1 ? '' : 's'}</span></div><span class="live-badge">${escapeHtml(aop.status)}</span></div>`).join('');
  $('#recent-runs').innerHTML = platform.recent_runs.map(run => `<div class="table-row"><span>${escapeHtml(run.intent)}</span><span>${escapeHtml(run.aop)}</span><span class="outcome">${escapeHtml(run.outcome)}</span><span>${escapeHtml(run.time)}</span></div>`).join('');
  $('#duet-aop').innerHTML += platform.aops.map(aop => `<option value="${aop.id}">${escapeHtml(aop.name)}</option>`).join('');
  renderAopList(platform.aops);
  renderWatchtower();
  $$('.overview-aop').forEach(row => row.addEventListener('click', () => { renderAop(row.dataset.aop); setView('aops'); }));
}

function renderWatchtower(range = '7') {
  const data = platform.watchtower;
  if (!data) return;
  const period = data.periods?.[range] || {metrics: data.metrics, trend: data.trend, context: ''};
  $('#watch-context').textContent = period.context;
  $('#watch-metrics').innerHTML = period.metrics.map(item => {
    const direction = item.change.startsWith('-') ? '↘' : '↗';
    return `<div class="metric"><span>${escapeHtml(item.label)}</span><strong>${escapeHtml(item.value)}</strong><small>${direction} ${escapeHtml(item.change)}</small><p>${escapeHtml(item.detail)}</p></div>`;
  }).join('');
  $('#deflection-current').textContent = period.metrics[0].value;
  $('#resolution-current').textContent = period.metrics[1].value;
  $('#deflection-change').textContent = `↗ ${period.metrics[0].change}`;
  $('#resolution-change').textContent = `↗ ${period.metrics[1].change}`;
  const chart = (field, tone) => period.trend.map(point => `<div class="single-trend-group"><div class="single-trend-bar ${tone}" style="height:${point[field]}%" data-value="${point[field]}%"></div><span>${escapeHtml(point.label)}</span></div>`).join('');
  $('#deflection-chart').innerHTML = chart('deflection', 'deflection');
  $('#resolution-chart').innerHTML = chart('resolution', 'resolution');
  $('#rubric-list').innerHTML = data.rubrics.map(item => `<div class="rubric-row"><div class="rubric-top"><strong>${escapeHtml(item.name)}</strong><span class="rubric-score">${item.score}% <i class="flag-count">${item.flags} flag${item.flags === 1 ? '' : 's'}</i></span></div><p>${escapeHtml(item.description)}</p><div class="score-track"><div class="score-fill" style="width:${item.score}%"></div></div></div>`).join('');
  const activeFilter = $('#watch-filters button.active')?.dataset.filter || 'All';
  renderReviewQueue(activeFilter);
}

function renderReviewQueue(filter) {
  const rows = (platform.watchtower?.queue || []).filter(item => filter === 'All' || item.category === filter);
  $('#review-queue').innerHTML = rows.map(item => `<div class="review-row"><strong>${escapeHtml(item.id)}</strong><span>${escapeHtml(item.category)}</span><span class="summary"><b>${escapeHtml(item.intent)}</b> · ${escapeHtml(item.summary)}</span><span class="severity ${item.severity.toLowerCase()}">${escapeHtml(item.severity)}</span><span>${escapeHtml(item.score)}</span><span>${escapeHtml(item.time)}</span></div>`).join('') || '<div class="empty-trace"><p>No conversations match this filter.</p></div>';
}

function renderResources(kind) {
  const labels = {
    tools: ['Tools', 'Inspect the functions Bookly procedures can call.'],
    knowledge: ['Knowledge', 'Review the approved information available to the agent.'],
    guardrails: ['Guardrails', 'Review deterministic controls applied around agent behavior.'],
  };
  const [title, subtitle] = labels[kind];
  $('#resource-title').textContent = title;
  $('#resource-subtitle').textContent = subtitle;
  $('#resource-content').innerHTML = (platform.resources?.[kind] || []).map(item => `<article class="resource-card"><div class="resource-card-head"><h2>${escapeHtml(item.name)}</h2><span class="resource-status">● ${escapeHtml(item.status)}</span></div><p>${escapeHtml(item.description)}</p><div class="resource-meta"><span>${kind === 'tools' ? 'REFERENCE' : kind === 'knowledge' ? 'SOURCE' : 'SCOPE'}</span><strong>${escapeHtml(item.used_by)}</strong></div></article>`).join('');
  setView('resources');
  $('#crumb-current').textContent = title.toUpperCase();
}

function renderAopList(aops) {
  $('#aop-list').innerHTML = aops.map(aop => `<div class="aop-row ${aop.id === activeAop ? 'active' : ''}" data-id="${aop.id}"><strong>${escapeHtml(aop.name)}</strong><span>${escapeHtml(aop.version)} · ${escapeHtml(aop.status)} · ${aop.steps.length} steps</span></div>`).join('') || '<div class="empty-trace"><p>No matching procedures.</p></div>';
  $$('.aop-row').forEach(row => row.addEventListener('click', () => renderAop(row.dataset.id)));
  if (!activeAop && aops.length) renderAop(aops[0].id);
}

function renderAop(id) {
  const aop = platform.aops.find(item => item.id === id);
  if (!aop) return;
  activeAop = id;
  $$('.aop-row').forEach(row => row.classList.toggle('active', row.dataset.id === id));
  $('#aop-detail').innerHTML = `<div class="aop-title"><div><span class="eyebrow">PUBLISHED PROCEDURE</span><h2>${escapeHtml(aop.name)}</h2><p>${escapeHtml(aop.description)}</p></div><span class="version-pill">● ${escapeHtml(aop.status)} · ${escapeHtml(aop.version)}</span></div><div class="aop-meta"><div class="meta-block"><h3>Entry conditions</h3><p>${escapeHtml(aop.entry_conditions)}</p></div><div class="meta-block"><h3>Referenced tools</h3>${aop.tools.map(tool => `<span class="tool-chip">${escapeHtml(tool)}</span>`).join('')}<h3 style="margin-top:15px">Guardrails</h3><ul>${aop.guardrails.map(rule => `<li>${escapeHtml(rule)}</li>`).join('')}</ul></div></div><div class="procedure"><h3>Procedure</h3>${aop.steps.map((step, index) => `<div class="step"><span class="step-num">${index + 1}</span><div class="step-body"><span class="type">${escapeHtml(step.type)}</span><strong>${escapeHtml(step.title)}</strong><p>${escapeHtml(step.body)}</p></div></div>`).join('')}</div><div class="detail-actions"><button class="primary" id="test-aop">Test in playground</button><button class="secondary" id="improve-aop">Improve with Duet ✦</button></div>`;
  $('#test-aop').addEventListener('click', () => { $('#input').value = aop.test_prompt; setView('playground'); });
  $('#improve-aop').addEventListener('click', () => { $('#duet-aop').value = aop.id; $('#duet-input').value = `Analyze and recommend improvements for the ${aop.name} AOP`; setView('duet'); });
}

$('#aop-search').addEventListener('input', event => {
  const query = event.target.value.toLowerCase();
  renderAopList(platform.aops.filter(aop => `${aop.name} ${aop.description} ${aop.tools.join(' ')}`.toLowerCase().includes(query)));
});
$('#new-aop').addEventListener('click', () => { $('#duet-input').value = 'Draft a new AOP for damaged books'; setView('duet'); });
$$('.resource-nav').forEach(button => button.addEventListener('click', () => renderResources(button.dataset.resource)));
$('#watch-range').addEventListener('change', event => renderWatchtower(event.target.value));
$('#watch-filters').addEventListener('click', event => {
  const button = event.target.closest('[data-filter]');
  if (!button) return;
  $$('#watch-filters button').forEach(item => item.classList.toggle('active', item === button));
  renderReviewQueue(button.dataset.filter);
});

const messages = $('#messages');
const input = $('#input');
const send = $('#send');
function bubble(text, role) {
  const el = document.createElement('div');
  el.className = `message ${role}`;
  el.textContent = text;
  messages.append(el);
  messages.scrollTop = messages.scrollHeight;
}
function renderTrace(trace) {
  $('#run-trace').innerHTML = `<div class="trace-head"><span class="aop-chip">AOP · ${escapeHtml(trace.version)}</span><h3>${escapeHtml(trace.aop_name)}</h3><p>${escapeHtml(trace.reason)}</p></div>${trace.events.map(event => `<div class="trace-event"><strong>${escapeHtml(event.label)}</strong><p>${escapeHtml(event.detail)}</p></div>`).join('')}`;
}
async function submit(text) {
  if (!text.trim()) return;
  bubble(text, 'user'); history.push({role:'user', content:text}); input.value = ''; send.disabled = true;
  try {
    const response = await fetch('/api/chat', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({history})});
    const data = await response.json(); if (!response.ok) throw new Error(data.error || 'Request failed');
    bubble(data.answer, 'assistant'); history.push({role:'assistant',content:data.answer}); $('#mode').textContent = data.mode; renderTrace(data.trace);
  } catch (error) { bubble(`Sorry, something went wrong: ${error.message}`, 'assistant'); history.pop(); }
  finally { send.disabled = false; input.focus(); }
}
$('#form').addEventListener('submit', event => {event.preventDefault(); submit(input.value);});
$$('.suggestion').forEach(button => button.addEventListener('click', () => {input.value = button.dataset.prompt; input.focus();}));
$('#reset').addEventListener('click', () => {history=[];messages.innerHTML='';bubble('Hi there! Welcome to Bookly. What can I look into for you?','assistant');$('#run-trace').innerHTML='<div class="empty-trace"><span>⌁</span><h3>No run yet</h3><p>Send a message to see AOP selection, decisions, and tool calls.</p></div>';input.focus();});
$$('.tab').forEach(tab => tab.addEventListener('click', () => {$$('.tab').forEach(t=>t.classList.toggle('active',t===tab));$$('.run-tab').forEach(panel=>panel.classList.toggle('active',panel.id===`run-${tab.dataset.runTab}`));}));

function renderArtifact(artifact) {
  if (!artifact) return;
  $('#artifact-panel').innerHTML = `<div class="artifact-head"><span>${escapeHtml(artifact.kind).toUpperCase()}</span><h2>${escapeHtml(artifact.title)}</h2><p>${escapeHtml(artifact.summary)}</p></div>${artifact.items.map(item => `<div class="artifact-item"><div><strong>${escapeHtml(item.label)}</strong><span class="artifact-status">${escapeHtml(item.status)}</span></div><p>${escapeHtml(item.detail)}</p></div>`).join('')}<div class="detail-actions"><button class="secondary">Save artifact</button><button class="secondary">Share preview</button></div>`;
}
async function askDuet(prompt) {
  if (!prompt.trim()) return;
  const area = $('#duet-messages');
  area.insertAdjacentHTML('beforeend', `<div class="duet-message user">${escapeHtml(prompt)}</div>`); area.scrollTop = area.scrollHeight; $('#duet-input').value='';
  const thinking = document.createElement('div'); thinking.className='duet-message'; thinking.textContent='Reviewing Bookly workspace…'; area.append(thinking);
  try {
    const response = await fetch('/api/duet',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt,aop_id:$('#duet-aop').value})});
    const data=await response.json(); if(!response.ok) throw new Error(data.error||'Request failed');
    thinking.textContent=data.answer; renderArtifact(data.artifact);
  } catch(error){thinking.textContent=`Duet could not complete that request: ${error.message}`;}
  area.scrollTop=area.scrollHeight;
}
$('#duet-form').addEventListener('submit',event=>{event.preventDefault();askDuet($('#duet-input').value);});
$$('[data-duet]').forEach(button=>button.addEventListener('click',()=>askDuet(button.dataset.duet)));

const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;const mic=$('#mic');const voiceNote=$('#voice-note');let recorder=null,recordingTimer=null;
function voiceError(error){if(['not-allowed','service-not-allowed','NotAllowedError','PermissionDeniedError'].includes(error))return'Microphone access was denied. Allow it for localhost and try again.';if(['audio-capture','NotFoundError','NotReadableError'].includes(error))return'No available microphone was found.';if(error==='no-speech')return'I did not hear any speech. Please try again.';return`Speech could not start (${error||'unknown error'}). You can type instead.`}
function enableBrowserRecognition(){if(!Recognition){mic.disabled=true;voiceNote.textContent='Speech recognition is unavailable here. You can type your question.';return}const recognition=new Recognition();recognition.lang='en-US';voiceNote.textContent='Voice uses your browser speech service.';recognition.onresult=e=>{input.value=e.results[0][0].transcript;voiceNote.textContent='Transcribed. Review, then press Send.'};recognition.onerror=e=>{voiceNote.textContent=voiceError(e.error)};recognition.onend=()=>{mic.disabled=false};mic.addEventListener('click',()=>{mic.disabled=true;voiceNote.textContent='Listening…';try{recognition.start()}catch(e){voiceNote.textContent=voiceError(e.name);mic.disabled=false}})}
function enableRecordedTranscription(){if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder){enableBrowserRecognition();return}const mimeType=['audio/webm;codecs=opus','audio/webm','audio/mp4'].find(type=>MediaRecorder.isTypeSupported(type));if(!mimeType){enableBrowserRecognition();return}voiceNote.textContent='Press the microphone to record with OpenAI transcription.';mic.addEventListener('click',async()=>{if(recorder?.state==='recording'){recorder.stop();return}mic.disabled=true;let stream;try{stream=await navigator.mediaDevices.getUserMedia({audio:true});const chunks=[];recorder=new MediaRecorder(stream,{mimeType});recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};recorder.onstop=async()=>{clearTimeout(recordingTimer);stream.getTracks().forEach(track=>track.stop());voiceNote.textContent='Transcribing…';try{const response=await fetch('/api/transcribe',{method:'POST',headers:{'Content-Type':mimeType.split(';')[0]},body:new Blob(chunks,{type:mimeType})});const data=await response.json();if(!response.ok)throw new Error(data.error);input.value=data.text;voiceNote.textContent='Transcribed. Review, then press Send.'}catch(e){voiceNote.textContent=e.message}finally{recorder=null;mic.disabled=false}};recorder.start();mic.disabled=false;voiceNote.textContent='Recording… press again to stop.';recordingTimer=setTimeout(()=>{if(recorder?.state==='recording')recorder.stop()},20000)}catch(e){stream?.getTracks().forEach(track=>track.stop());voiceNote.textContent=voiceError(e.name);mic.disabled=false}})}

fetch('/api/config').then(r=>r.json()).then(config=>{ $('#mode').textContent=config.serverTranscription?'OpenAI API':'Scripted demo'; config.serverTranscription?enableRecordedTranscription():enableBrowserRecognition(); }).catch(enableBrowserRecognition);
loadPlatform().catch(error=>{$('#metrics').innerHTML=`<div class="metric">Could not load workspace: ${escapeHtml(error.message)}</div>`});
