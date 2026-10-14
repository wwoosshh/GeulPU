// GeulPU 앱 화면 — 관리자(GeulPU.exe)의 /api 와 /v1 만 쓴다(바깥 자원 없음, 새 판 알림만 GitHub API 를 묻는다).
'use strict';

const S = {
  st: null,            // /api/state
  view: 'chat',
  rooms: [],
  roomId: null,
  streaming: null,     // { ctrl, msgEl, ... }
  log: { job: 0, from: 0 },
  results: null,
  resultsAt: 0,
  update: null,
  lastSig: {},
};

// ---------- 도움 ----------
const $ = (s, r = document) => r.querySelector(s);
function h(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  if (attrs) for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') e.className = v;
    else if (k === 'html') e.innerHTML = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? '' : v);
  }
  for (const k of kids.flat()) {
    if (k === null || k === undefined || k === false) continue;
    e.append(k instanceof Node ? k : document.createTextNode(String(k)));
  }
  return e;
}
const esc = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
function fmtBytes(n) {
  if (!(n >= 0)) return '-';
  if (n >= 1e9) return (n / 1e9).toFixed(n >= 1e11 ? 0 : 1) + ' GB';
  if (n >= 1e6) return (n / 1e6).toFixed(0) + ' MB';
  if (n >= 1e3) return (n / 1e3).toFixed(0) + ' KB';
  return n + ' B';
}
function fmtDur(s) {
  if (!(s >= 0) || !isFinite(s)) return '-';
  s = Math.round(s);
  if (s < 60) return s + '초';
  const m = Math.floor(s / 60), r = s % 60;
  if (m < 60) return m + '분 ' + r + '초';
  return Math.floor(m / 60) + '시간 ' + (m % 60) + '분';
}
async function api(path, body) {
  const opt = body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
  const r = await fetch(path, opt);
  let j = null;
  try { j = await r.json(); } catch (_) { }
  if (!r.ok) throw new Error((j && j.error && j.error.message) || ('HTTP ' + r.status));
  return j;
}
function toast(msg, kind) {
  const d = h('div', { class: kind || '' }, msg);
  $('#toast').append(d);
  setTimeout(() => d.remove(), kind === 'err' ? 9000 : 5000);
}
function store(key, val) { try { localStorage.setItem(key, JSON.stringify(val)); } catch (_) { } }
function load(key, dflt) { try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : dflt; } catch (_) { return dflt; } }
function sig(name, obj) {
  const s = JSON.stringify(obj);
  if (S.lastSig[name] === s) return false;
  S.lastSig[name] = s;
  return true;
}
function modal(content, buttons) {
  const box = $('#modalbox');
  box.replaceChildren(content);
  if (buttons && buttons.length) box.append(h('div', { class: 'foot' }, buttons));
  $('#modal').hidden = false;
}
function closeModal() { $('#modal').hidden = true; $('#modalbox').replaceChildren(); }
function confirmBox(title, body, okText, danger) {
  return new Promise(res => {
    const ok = h('button', { class: 'btn ' + (danger ? 'danger' : 'primary'), onclick: () => { closeModal(); res(true); } }, okText || '확인');
    const no = h('button', { class: 'btn', onclick: () => { closeModal(); res(false); } }, '취소');
    modal(h('div', null, h('h3', { style: 'margin-top:0' }, title), body), [no, ok]);
  });
}

// ---------- 보기 ----------
function show(view) {
  S.view = view;
  document.querySelectorAll('.navbtn').forEach(b => b.classList.toggle('active', b.dataset.view === view));
  document.querySelectorAll('.view').forEach(v => v.classList.toggle('active', v.id === 'view-' + view));
  S.lastSig = {};
  renderAll();
  if (view === 'bench') loadResults(true);
  try { sessionStorage.setItem('geulpu.view', view); } catch (_) { }
}
document.querySelectorAll('.navbtn').forEach(b => b.addEventListener('click', () => show(b.dataset.view)));

// ---------- 상태 읽기 ----------
let failCount = 0;
async function refresh() {
  try {
    const st = await api('/api/state');
    S.st = st;
    failCount = 0;
    $('#chip-conn').hidden = true;
    renderAll();
    await pollLog();
  } catch (e) {
    failCount++;
    if (failCount >= 2) $('#chip-conn').hidden = false;
  }
}
setInterval(() => { if (!document.hidden) refresh(); }, 1000);

function renderAll() {
  if (!S.st) return;
  renderTop();
  if (S.view === 'chat') renderChatHead();
  if (S.view === 'models') renderModels();
  if (S.view === 'bench') renderBench();
  if (S.view === 'device') renderDevice();
  if (S.view === 'settings') renderSettings();
}

function layerName(l) { return l === 'cuda' ? 'CUDA' : l === 'vulkan' ? 'Vulkan' : '-'; }

function renderTop() {
  const st = S.st, d = st.device, sv = st.server, j = st.job;
  $('#ver').textContent = 'v' + st.app.version;
  const g = $('#chip-gpu');
  if (!d.checked) { g.querySelector('.dot').className = 'dot busy'; g.lastChild.textContent = '장치 확인 중…'; }
  else if (!d.layer) { g.querySelector('.dot').className = 'dot err'; g.lastChild.textContent = '돌릴 수 있는 GPU 없음'; g.title = d.reason; }
  else {
    g.querySelector('.dot').className = 'dot ok';
    g.lastChild.textContent = `${d.name} · ${layerName(d.layer)} · ${fmtBytes(d.memory)}`;
    g.title = d.layer === 'vulkan' ? `모듈 판 ${d.variant}${d.coop ? ' · 협력 행렬 ' + d.coop : ''}` : '';
  }
  const s = $('#chip-server');
  const dotc = { off: 'dot', starting: 'dot busy', ready: 'dot ok', failed: 'dot err' }[sv.state] || 'dot';
  s.querySelector('.dot').className = dotc;
  s.lastChild.textContent = sv.state === 'ready' ? `서버 준비 · ${sv.model} · 슬롯 ${sv.slots} · 문맥 ${sv.context}`
    : sv.state === 'starting' ? `서버 올리는 중 · ${sv.model} · ${fmtDur(sv.seconds)}`
    : sv.state === 'failed' ? '서버 실패 — 기록을 보세요' : '서버 꺼짐';
  s.title = sv.reason || '';
  const jc = $('#chip-job');
  if (j && j.state === 'running') {
    jc.hidden = false;
    jc.lastChild.textContent = `${j.title} · ${Math.round(j.progress / 10)}% · ${fmtDur(j.seconds)}`;
  } else jc.hidden = true;
}

// ---------- 새 판 알림 ----------
function verNum(v) { return String(v || '').replace(/^v/, '').split('.').map(x => parseInt(x, 10) || 0); }
function newer(a, b) { const x = verNum(a), y = verNum(b); for (let i = 0; i < 3; i++) { if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) > (y[i] || 0); } return false; }
async function checkUpdate() {
  if (!S.st || !S.st.settings.update_check) return;
  let rel = null;
  try {
    const c = JSON.parse(sessionStorage.getItem('geulpu.rel') || 'null');
    if (c && Date.now() - c.t < 3600e3) rel = c.r;
  } catch (_) { }
  if (!rel) {
    try {
      const r = await fetch('https://api.github.com/repos/wwoosshh/GeulPU/releases/latest', { headers: { Accept: 'application/vnd.github+json' } });
      if (!r.ok) return;
      const j = await r.json();
      rel = { tag: j.tag_name, url: j.html_url, name: j.name };
      try { sessionStorage.setItem('geulpu.rel', JSON.stringify({ t: Date.now(), r: rel })); } catch (_) { }
    } catch (_) { return; }
  }
  S.update = rel;
  const b = $('#update-banner');
  if (rel && newer(rel.tag, S.st.app.version)) {
    b.replaceChildren(h('span', null, `새 판 ${rel.tag} 이(가) 있습니다 (지금 v${S.st.app.version}) — `), h('a', { href: rel.url, target: '_blank', rel: 'noopener' }, rel.name || rel.tag),
      h('span', { class: 'muted small' }, ' · 받아서 새 폴더에 풀고 GeulPU.exe 를 실행하면 됩니다. 모델 · 결과는 자료 폴더에 그대로 남습니다.'),
      h('span', { class: 'grow' }), h('button', { class: 'btn small', onclick: () => { b.hidden = true; } }, '닫기'));
    b.hidden = false;
  } else b.hidden = true;
}

// ---------- 채팅 ----------
const R1_BOS = '<｜begin▁of▁sentence｜>', R1_USER = '<｜User｜>', R1_ASSIST = '<｜Assistant｜>', R1_EOS = '<｜end▁of▁sentence｜>';

function saveRooms() { store('geulpu.rooms', S.rooms); store('geulpu.room', S.roomId); }
function curRoom() { return S.rooms.find(r => r.id === S.roomId) || null; }
function newRoom() {
  const r = { id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6), title: '새 대화', model: defaultModel(), messages: [], created: Date.now() };
  S.rooms.unshift(r);
  S.roomId = r.id;
  saveRooms();
  renderRooms();
  renderMsgs();
  $('#input').focus();
}
function runnableModels() {
  if (!S.st) return [];
  return S.st.models.filter(m => m.shape && m.shape.ok && !m.device_reason);
}
function defaultModel() {
  const st = S.st;
  if (st && st.server.state === 'ready' && st.server.model) return st.server.model;
  const rm = runnableModels();
  return rm.length ? rm[0].id : '';
}
function modelOf(id) { return S.st ? S.st.models.find(m => m.id === id) : null; }

function renderRooms() {
  const list = $('#roomlist');
  list.replaceChildren(...S.rooms.map(r => h('div', { class: 'room' + (r.id === S.roomId ? ' active' : ''), onclick: () => { if (S.streaming) return; S.roomId = r.id; saveRooms(); renderRooms(); renderMsgs(); renderChatHead(true); } },
    h('span', { class: 't', title: r.title }, r.title),
    h('button', { class: 'x', title: '지우기', onclick: ev => { ev.stopPropagation(); delRoom(r.id); } }, '×'))));
}
async function delRoom(id) {
  if (S.streaming && id === S.roomId) return;
  const r = S.rooms.find(x => x.id === id);
  if (r && r.messages.length && !(await confirmBox('대화 지우기', h('p', null, `"${r.title}" 대화를 지울까요? (이 브라우저에만 저장된 것이라 되돌릴 수 없습니다)`), '지우기', true))) return;
  S.rooms = S.rooms.filter(x => x.id !== id);
  if (S.roomId === id) S.roomId = S.rooms.length ? S.rooms[0].id : null;
  if (!S.rooms.length) { newRoom(); return; }
  saveRooms(); renderRooms(); renderMsgs();
}

function renderChatHead(force) {
  const sel = $('#chatmodel');
  const room = curRoom();
  const models = S.st ? S.st.models : [];
  if (!sig('chathead', [models.map(m => [m.id, m.device_reason, m.shape && m.shape.ok]), room && room.model, S.st && S.st.server]) && !force) return;
  const opts = models.map(m => {
    const bad = !(m.shape && m.shape.ok) || m.device_reason;
    return h('option', { value: m.id, disabled: bad ? true : null }, (m.name || m.id) + (m.shape && m.shape.quant ? ' · ' + m.shape.quant : '') + (bad ? ' (못 돌림)' : ''));
  });
  if (!models.length) opts.push(h('option', { value: '' }, '모델이 없습니다 — 모델 쪽에서 받거나 더하세요'));
  sel.replaceChildren(...opts);
  if (room) {
    if (!room.model || !models.some(m => m.id === room.model)) room.model = defaultModel();
    sel.value = room.model || '';
  }
  const m = room && modelOf(room.model);
  const sv = S.st ? S.st.server : null;
  let info = '';
  if (m && m.shape) info = `${m.shape.params ? (m.shape.params / 1e9).toFixed(1) + 'B' : ''} · 문맥 ${m.shape.context} · ${m.template === 'deepseek-r1' ? 'R1 틀' : 'ChatML'}`;
  if (sv && sv.model === (room && room.model)) {
    if (sv.state === 'ready') info += ` · 서버 준비(슬롯마다 문맥 ${sv.context})`;
    else if (sv.state === 'starting') info += ' · 서버 올리는 중…';
  }
  $('#chatmodelinfo').textContent = info;
}
$('#chatmodel').addEventListener('change', e => {
  const r = curRoom();
  if (!r) return;
  r.model = e.target.value;
  saveRooms();
  renderChatHead(true);
});
$('#newroom').addEventListener('click', () => { if (!S.streaming) newRoom(); });
$('#optbtn').addEventListener('click', () => $('#chatopts').classList.toggle('open'));

// 아주 작은 마크다운(탈출 먼저 — 화면에 HTML 을 넣지 않는다)
function mdInline(s) {
  return s.replace(/`([^`\n]+)`/g, '<code class="inl">$1</code>')
    .replace(/\*\*([^*\n]+)\*\*/g, '<b>$1</b>')
    .replace(/(^|[\s(])\*([^*\n]+)\*(?=[\s).,!?]|$)/g, '$1<i>$2</i>');
}
function md(text) {
  const parts = String(text).split('```');
  let out = '';
  parts.forEach((p, i) => {
    if (i % 2 === 1) {
      const nl = p.indexOf('\n');
      const code = nl >= 0 ? p.slice(nl + 1) : p;
      out += '<pre class="code"><code>' + esc(code.replace(/\n$/, '')) + '</code></pre>';
      return;
    }
    const lines = esc(p).split('\n');
    let para = [], list = null;
    const flush = () => {
      if (para.length) { out += '<p>' + para.map(mdInline).join('<br>') + '</p>'; para = []; }
      if (list) { out += `<${list.t}>` + list.items.map(x => '<li>' + mdInline(x) + '</li>').join('') + `</${list.t}>`; list = null; }
    };
    for (const ln of lines) {
      let m;
      if (!ln.trim()) { flush(); continue; }
      if ((m = ln.match(/^\s*#{1,4}\s+(.*)$/))) { flush(); out += '<p><b>' + mdInline(m[1]) + '</b></p>'; continue; }
      if ((m = ln.match(/^\s*[-*]\s+(.*)$/))) { if (para.length) { out += '<p>' + para.map(mdInline).join('<br>') + '</p>'; para = []; } if (!list || list.t !== 'ul') { if (list) flush(); list = { t: 'ul', items: [] }; } list.items.push(m[1]); continue; }
      if ((m = ln.match(/^\s*\d+[.)]\s+(.*)$/))) { if (para.length) { out += '<p>' + para.map(mdInline).join('<br>') + '</p>'; para = []; } if (!list || list.t !== 'ol') { if (list) flush(); list = { t: 'ol', items: [] }; } list.items.push(m[1]); continue; }
      if (list) flush();
      para.push(ln);
    }
    flush();
  });
  return out;
}
// R1: </think> 앞은 생각
function splitThink(text, template, done) {
  if (template !== 'deepseek-r1') return { think: null, answer: text };
  let t = text;
  if (t.startsWith('<think>')) t = t.slice(7);
  const k = t.indexOf('</think>');
  if (k >= 0) return { think: t.slice(0, k).trim(), answer: t.slice(k + 8).replace(/^\s+/, '') };
  return done ? { think: null, answer: t } : { think: t.trim(), answer: '', open: true };
}
function msgEl(m, room) {
  const who = m.role === 'user' ? '나' : m.role === 'assistant' ? (modelOf(room.model) ? (modelOf(room.model).name || room.model) : room.model) : '';
  const body = h('div', { class: 'body' });
  const e = h('div', { class: 'msg ' + m.role }, h('div', { class: 'who' }, who), body);
  fillMsg(e, m, room, true);
  return e;
}
function fillMsg(e, m, room, done) {
  const body = e.querySelector('.body');
  if (m.role === 'user' || m.role === 'notice' || m.role === 'error') { body.textContent = m.content; return; }
  const tpl = m.template || (modelOf(room.model) || {}).template;
  const sp = splitThink(m.content, tpl, done && !m.stopped);
  if (done && m.stopped) sp.open = false;
  body.replaceChildren();
  if (sp.think !== null && sp.think !== undefined && sp.think !== '') {
    const label = sp.open ? '생각하는 중…' : `생각${m.stopped && !sp.answer ? ' — 멈춤' : ''} (${sp.think.length.toLocaleString()} 자)`;
    const d = h('details', { class: 'think', open: sp.open ? true : null }, h('summary', null, label), h('div', { class: 'tb' }, sp.think));
    body.append(d);
  }
  const a = h('div', { html: md(sp.answer) });
  if (!done) a.classList.add('cursor');
  body.append(a);
  let st = e.querySelector('.stats');
  if (m.stats) {
    if (!st) { st = h('div', { class: 'stats' }); e.append(st); }
    st.textContent = m.stats;
  }
}
function renderMsgs() {
  const box = $('#msgs');
  const room = curRoom();
  box.replaceChildren();
  if (!room || !room.messages.length) {
    box.append(h('div', { class: 'empty' }, h('div', { class: 'big' }, 'GeulPU 와 대화'),
      h('div', null, '모델을 고르고 메시지를 보내면 서버를 올려(처음 한 번은 커널을 이 장치에 맞춰 만듭니다) 답을 흘려 보여 줍니다.'),
      h('div', { class: 'small', style: 'margin-top:8px' }, '대화는 이 브라우저에만 저장됩니다.')));
    return;
  }
  for (const m of room.messages) box.append(msgEl(m, room));
  box.scrollTop = box.scrollHeight;
}

function buildR1Prompt(room, system) {
  let p = R1_BOS + (system || '');
  for (const m of room.messages) {
    if (m.role === 'user') p += R1_USER + m.content;
    else if (m.role === 'assistant' && !m.partial) {
      let c = m.content;
      const k = c.lastIndexOf('</think>');
      if (k >= 0) c = c.slice(k + 8);
      p += R1_ASSIST + c.trim() + R1_EOS;
    }
  }
  return p + R1_ASSIST;
}

async function ensureServer(room, notice) {
  const st = S.st;
  if (st.server.state === 'ready' && st.server.model === room.model) return true;
  if (!(st.server.state === 'starting' && st.server.model === room.model)) {
    try { await api('/api/server/start', { model: room.model }); }
    catch (e) { throw new Error('서버를 올리지 못했습니다: ' + e.message); }
  }
  // 준비될 때까지(일의 단계 · 서버 기록을 알림에)
  for (;;) {
    await new Promise(r => setTimeout(r, 1000));
    await refresh();
    const s2 = S.st;
    if (s2.server.state === 'ready' && s2.server.model === room.model) return true;
    const j = s2.job;
    if (j && j.kind === 'server' && j.state !== 'running') {
      if (j.state === 'done' && s2.server.state === 'ready') return true;
      throw new Error((j.reason || '서버를 올리지 못했습니다') + (s2.server.reason ? ' — ' + s2.server.reason.slice(-600) : ''));
    }
    if (s2.server.state === 'failed') throw new Error(s2.server.reason || '서버가 실패했습니다');
    if (notice) {
      const step = j && j.state === 'running' ? j.step : '서버 올리는 중';
      notice.content = `${step} · ${fmtDur(j ? j.seconds : s2.server.seconds)}`;
      fillMsg(notice.el, notice, room, true);
    }
    if (S.streaming && S.streaming.aborted) throw new Error('멈췄습니다');
  }
}

async function send() {
  if (S.streaming) { stopStream(); return; }
  const input = $('#input');
  const text = input.value.trim();
  if (!text) return;
  let room = curRoom();
  if (!room) { newRoom(); room = curRoom(); }
  if (!room.model) { toast('모델이 없습니다 — 모델 쪽에서 받거나 더해 주세요', 'err'); return; }
  const m = modelOf(room.model);
  if (!m || !(m.shape && m.shape.ok) || m.device_reason) { toast('이 모델은 이 장치에서 돌릴 수 없습니다: ' + ((m && (m.device_reason || (m.shape && m.shape.reason))) || ''), 'err'); return; }
  input.value = '';
  autosize();
  if (!room.messages.length) room.title = text.slice(0, 40);
  room.messages.push({ role: 'user', content: text });
  saveRooms(); renderRooms(); renderMsgs();
  const box = $('#msgs');
  S.streaming = { aborted: false, ctrl: null };
  $('#sendbtn').textContent = '멈춤';
  let notice = null;
  try {
    if (!(S.st.server.state === 'ready' && S.st.server.model === room.model)) {
      notice = { role: 'notice', content: '서버를 올립니다…' };
      notice.el = msgEl(notice, room);
      box.append(notice.el);
      box.scrollTop = box.scrollHeight;
      await ensureServer(room, notice);
      notice.el.remove();
      notice = null;
    }
    const tpl = m.template;
    const temp = parseFloat($('#opt-temp').value) || 0;
    const maxTok = parseInt($('#opt-max').value, 10) || 4096;
    const system = $('#opt-system').value.trim();
    const asst = { role: 'assistant', content: '', template: tpl, partial: true };
    let url, body;
    if (tpl === 'deepseek-r1') {
      url = '/v1/completions';
      body = { prompt: buildR1Prompt(room, system), max_tokens: maxTok, temperature: temp, stream: true, geulpu: {} };
    } else {
      url = '/v1/chat/completions';
      const msgs = [];
      if (system) msgs.push({ role: 'system', content: system });
      for (const x of room.messages) if (x.role === 'user' || (x.role === 'assistant' && !x.partial)) msgs.push({ role: x.role, content: x.content });
      body = { messages: msgs, max_tokens: maxTok, temperature: temp, stream: true, stream_options: { include_usage: true }, geulpu: {} };
    }
    room.messages.push(asst);
    const el = msgEl(asst, room);
    fillMsg(el, asst, room, false);
    box.append(el);
    box.scrollTop = box.scrollHeight;
    const ctrl = new AbortController();
    S.streaming.ctrl = ctrl;
    const t0 = performance.now();
    let tFirst = 0, usage = null, gp = null, finish = null;
    const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal: ctrl.signal });
    if (!res.ok) {
      let msg = 'HTTP ' + res.status;
      try { const j = await res.json(); msg = (j.error && j.error.message) || msg; } catch (_) { }
      throw new Error(msg);
    }
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = '', lastPaint = 0;
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let k;
      while ((k = buf.indexOf('\n\n')) >= 0) {
        const evt = buf.slice(0, k);
        buf = buf.slice(k + 2);
        for (const line of evt.split('\n')) {
          if (!line.startsWith('data:')) continue;
          const data = line.slice(5).trim();
          if (data === '[DONE]') continue;
          let j;
          try { j = JSON.parse(data); } catch (_) { continue; }
          const c = j.choices && j.choices[0];
          const piece = c ? (tpl === 'deepseek-r1' ? (c.text || '') : ((c.delta && c.delta.content) || '')) : '';
          if (piece) { if (!tFirst) tFirst = performance.now(); asst.content += piece; }
          if (c && c.finish_reason) finish = c.finish_reason;
          if (j.usage) usage = j.usage;
          if (j.geulpu) gp = j.geulpu;
        }
      }
      const now = performance.now();
      if (now - lastPaint > 60) {
        lastPaint = now;
        const nearBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 80;
        fillMsg(el, asst, room, false);
        if (nearBottom) box.scrollTop = box.scrollHeight;
      }
    }
    delete asst.partial;
    const n = (usage && usage.completion_tokens) || (gp && gp.tokens && gp.tokens.length) || 0;
    let stat = '';
    if (gp && gp.generate_us > 0 && n > 1) {
      const tps = (n - 1) / (gp.generate_us / 1e6);
      const firstMs = gp.first_token_ms / 1000; // 서버의 이 칸은 µs(이름만 ms)
      stat = `${n} 토큰 · ${tps.toFixed(1)} 토큰/초 · 첫 토큰 ${firstMs.toFixed(0)} ms`;
    } else if (tFirst) {
      stat = `${n} 토큰 · ${((performance.now() - t0) / 1000).toFixed(1)} 초`;
    }
    if (finish === 'length') stat += ' · 답 길이 상한에서 끊김';
    asst.stats = stat;
    fillMsg(el, asst, room, true);
    saveRooms();
  } catch (e) {
    if (notice && notice.el) notice.el.remove();
    const last = room.messages[room.messages.length - 1];
    if (last && last.role === 'assistant' && last.partial) {
      delete last.partial;
      if (S.streaming && S.streaming.aborted) { last.stats = '(멈춤)'; last.stopped = true; }
      else { last.stats = '(오류: ' + e.message + ')'; }
      if (!last.content) room.messages.pop();
    }
    if (!(S.streaming && S.streaming.aborted)) room.messages.push({ role: 'error', content: e.message });
    saveRooms();
    renderMsgs();
  } finally {
    S.streaming = null;
    $('#sendbtn').textContent = '보내기';
  }
}
function stopStream() {
  if (!S.streaming) return;
  S.streaming.aborted = true;
  if (S.streaming.ctrl) S.streaming.ctrl.abort();
}
function autosize() { const t = $('#input'); t.style.height = 'auto'; t.style.height = Math.min(220, t.scrollHeight) + 'px'; }
$('#input').addEventListener('input', autosize);
$('#input').addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); } });
$('#sendbtn').addEventListener('click', send);

// ---------- 모델 ----------
function checkTag(c) {
  if (c === 'crosscheck') return h('span', { class: 'tag ok', title: '교차검증의 기준 모델 — 출력이 기준 PC 와 비트까지 같은지 볼 수 있다' }, '교차검증 기준');
  return h('span', { class: 'tag', title: '엔진이 받는 꼴의 파일이지만 이 파일로는 아직 돌려 보지 않았다' }, '아직 안 돌려 봄');
}
function renderModels() {
  const st = S.st;
  $('#diskfree').textContent = `모델 폴더 여유 ${fmBytesSafe(st.app.disk_free)} · ${st.app.models_dir}`;
  const mine = st.models;
  if (sig('mymodels', [mine, st.server.model, st.server.state, st.device.layer])) {
    const box = $('#mymodels');
    if (!mine.length) box.replaceChildren(h('div', { class: 'muted' }, '아직 없습니다. 아래에서 받거나, 이미 받은 GGUF 파일을 더하세요.'));
    else box.replaceChildren(...mine.map(m => modelCard(m)));
  }
  if (sig('catalog', [st.catalog, st.device.variant, st.device.layer])) {
    $('#catalog').replaceChildren(...st.catalog.map(c => catalogCard(c)));
  }
}
function fmBytesSafe(n) { return n >= 0 ? fmtBytes(n) : '알 수 없음'; }
function modelCard(m) {
  const s = m.shape || {};
  const ok = s.ok && !m.device_reason;
  const tags = [];
  if (s.quant) tags.push(h('span', { class: 'tag acc' }, s.weight_type === s.quant ? s.quant : `${s.quant} (${s.weight_type})`));
  if (m.verified) tags.push(h('span', { class: 'tag ok', title: m.sha256 }, 'SHA-256 확인'));
  else if (m.verifying) tags.push(h('span', { class: 'tag' }, `확인 중 ${m.size > 0 ? Math.round(100 * m.verify_bytes / m.size) : 0}%`));
  else if (m.sha256) tags.push(h('span', { class: 'tag', title: m.sha256 }, '해시 잼(목록에 없음)'));
  if (m.catalog) tags.push(h('span', { class: 'tag' }, '목록: ' + m.catalog));
  if (!s.ok) tags.push(h('span', { class: 'tag err' }, '받지 않는 파일'));
  else if (m.device_reason) tags.push(h('span', { class: 'tag warn' }, '이 장치에서 안 됨'));
  const srv = S.st.server;
  if (srv.model === m.id && srv.state === 'ready') tags.push(h('span', { class: 'tag ok' }, '서버에 올라 있음'));
  const shapeLine = s.ok ? `층 ${s.layers} · 너비 ${s.width} · 머리 ${s.heads}/${s.kv_heads} · 확장폭 ${s.ffn} · 낱말 ${s.vocab.toLocaleString()} · 문맥 ${s.context.toLocaleString()} · ${m.template === 'deepseek-r1' ? 'R1 틀' : 'ChatML'}` : (s.reason || '');
  return h('div', { class: 'card' },
    h('div', { class: 'row' }, h('b', null, m.name || m.id), ...tags, h('span', { class: 'grow' }),
      h('button', { class: 'btn small primary', disabled: ok ? null : true, onclick: () => chatWith(m.id) }, '채팅'),
      h('button', { class: 'btn small', disabled: m.verifying ? true : null, onclick: () => verifyModel(m.id) }, '확인(SHA-256)'),
      h('button', { class: 'btn small danger', onclick: () => removeModel(m) }, '빼기')),
    h('div', { class: 'muted small mono', style: 'margin-top:4px;word-break:break-all' }, `${m.path} · ${fmtBytes(m.size)}`),
    h('div', { class: 'small', style: 'margin-top:2px' }, shapeLine),
    m.device_reason && s.ok ? h('div', { class: 'small', style: 'color:var(--warn)' }, m.device_reason) : null);
}
function chatWith(id) {
  show('chat');
  let r = curRoom();
  if (!r || r.messages.length) { newRoom(); r = curRoom(); }
  r.model = id;
  saveRooms();
  renderChatHead(true);
}
async function verifyModel(id) {
  try { await api('/api/models/verify', { id }); toast('SHA-256 을 잽니다 (8 GB 에 수 초~1 분)'); refresh(); }
  catch (e) { toast(e.message, 'err'); }
}
async function removeModel(m) {
  const inside = m.path.toLowerCase().startsWith(S.st.app.models_dir.toLowerCase());
  const cb = h('input', { type: 'checkbox', id: 'delfile' });
  const body = h('div', null, h('p', null, `"${m.name || m.id}" 을(를) 목록에서 뺄까요?`),
    inside ? h('label', { class: 'row' }, cb, '파일도 지우기 (', fmtBytes(m.size), ')') : h('p', { class: 'muted small' }, '바깥 폴더의 파일은 지우지 않고 목록에서만 뺍니다.'));
  if (!(await confirmBox('모델 빼기', body, '빼기', true))) return;
  try { await api('/api/models/remove', { id: m.id, delete_file: inside && cb.checked }); refresh(); }
  catch (e) { toast(e.message, 'err'); }
}
function catalogCard(c) {
  const d = c.download;
  const kind = S.st.device;
  const kBlocked = c.devices === 'k' && kind.layer === 'vulkan' && kind.variant === '공유32';
  let action;
  if (c.installed) action = h('span', { class: 'tag ok' }, '가짐');
  else if (d && (d.state === 'downloading' || d.state === 'verifying')) {
    const pct = d.state === 'verifying' ? (d.total ? 100 * d.verify_bytes / d.total : 0) : (d.total ? 100 * d.received / d.total : 0);
    const eta = d.bytes_per_s > 0 ? (d.total - d.received) / d.bytes_per_s : NaN;
    action = h('div', { class: 'col', style: 'width:100%' },
      h('div', { class: 'bar' }, h('i', { style: `width:${pct.toFixed(1)}%` })),
      h('div', { class: 'row small muted' }, d.state === 'verifying' ? `SHA-256 확인 중 ${pct.toFixed(0)}%` :
        `${fmtBytes(d.received)} / ${fmtBytes(d.total)} · ${fmtBytes(d.bytes_per_s)}/초 · 남은 ${fmtDur(eta)}`,
        h('span', { class: 'grow' }), h('button', { class: 'btn small', onclick: () => api('/api/models/cancel', { id: c.id }).then(refresh) }, '멈춤')));
  } else {
    action = h('div', { class: 'row', style: 'width:100%' },
      h('button', { class: 'btn primary small', onclick: () => startDownload(c) }, d && (d.state === 'failed' || d.state === 'cancelled') ? '이어받기' : '받기'),
      d && d.reason ? h('span', { class: 'small', style: 'color:var(--err)' }, d.reason) : null);
  }
  return h('div', { class: 'card col' },
    h('div', { class: 'row' }, h('b', null, c.name), h('span', { class: 'tag acc' }, c.quant), checkTag(c.check)),
    h('div', { class: 'small muted' }, `${fmtBytes(c.size)} · ${c.license} · `, h('a', { href: 'https://' + c.source, target: '_blank', rel: 'noopener' }, c.source)),
    h('div', { class: 'small' }, c.note),
    kBlocked ? h('div', { class: 'small', style: 'color:var(--warn)' }, '이 장치(공유 메모리 32 KB)에서는 아직 k-양자화를 돌리지 못합니다.') : null,
    action);
}
async function startDownload(c) {
  const st = S.st;
  const body = h('div', { class: 'col' },
    h('div', { class: 'kv' },
      h('div', null, '파일'), h('div', { class: 'mono' }, c.file),
      h('div', null, '출처'), h('div', { class: 'mono', style: 'word-break:break-all' }, c.url),
      h('div', null, '크기'), h('div', null, `${fmtBytes(c.size)} (${c.size.toLocaleString()} 바이트)`),
      h('div', null, 'SHA-256'), h('div', { class: 'mono small', style: 'word-break:break-all' }, c.sha256),
      h('div', null, '저장할 곳'), h('div', { class: 'mono small', style: 'word-break:break-all' }, st.app.models_dir),
      h('div', null, '디스크 여유'), h('div', null, fmBytesSafe(st.app.disk_free)),
      h('div', null, '라이선스'), h('div', null, c.license)),
    c.check !== 'crosscheck' ? h('p', { class: 'small muted' }, '이 파일로는 아직 GeulPU 에서 돌려 보지 않았습니다. 받은 뒤 앱이 GGUF 머리를 보고 받는지 알려 줍니다.') : null);
  if (!(await confirmBox('모델 받기', body, '받기'))) return;
  try { await api('/api/models/download', { id: c.id }); refresh(); }
  catch (e) { toast(e.message, 'err'); }
}
$('#openmodels').addEventListener('click', () => api('/api/open', { what: 'models' }).catch(e => toast(e.message, 'err')));
$('#addfile').addEventListener('click', () => browse(''));
async function browse(path) {
  let j;
  try { j = await api('/api/fs?path=' + encodeURIComponent(path)); }
  catch (e) { toast(e.message, 'err'); return; }
  const list = h('div', { class: 'col', style: 'max-height:52vh;overflow:auto;gap:0' });
  if (j.path) list.append(h('div', { class: 'fsitem', onclick: () => browse(j.parent || '') }, '⬆', h('span', { class: 'n' }, '위로')));
  for (const e of j.entries) {
    list.append(h('div', {
      class: 'fsitem', onclick: async () => {
        if (e.dir) { browse(e.path); return; }
        closeModal();
        try { const r = await api('/api/models/add', { path: e.path }); toast(`더했습니다: ${r.id}`, 'ok'); refresh(); }
        catch (err) { toast(err.message, 'err'); }
      }
    }, e.dir ? '📁' : '📄', h('span', { class: 'n' }, e.name), e.dir ? null : h('span', { class: 'muted small' }, fmtBytes(e.size))));
  }
  if (!j.entries.length) list.append(h('div', { class: 'muted small' }, '(.gguf 파일 · 폴더가 없습니다)'));
  modal(h('div', null, h('h3', { style: 'margin-top:0' }, 'GGUF 파일 고르기'), h('div', { class: 'muted small mono', style: 'margin-bottom:8px' }, j.path || '드라이브 · 자주 쓰는 곳'), list),
    [h('button', { class: 'btn', onclick: closeModal }, '닫기')]);
}

// ---------- 벤치 ----------
const BENCH = [
  { kind: 'diag', title: '자기 진단', needModel: true,
    desc: '이 기기의 바닥(메모리 읽기 대역 · 정수 텐서 최고치)을 재고, 엔진의 커널마다 시간과 바닥 대비 배수를 적습니다. 1~6 분.' },
  { kind: 'speed', title: '속도', needModel: true,
    desc: '서버를 슬롯 1 · 문맥 4096 으로 올려 프롬프트 512 · 2048 처리와 생성(짧은 문맥 · 문맥 1024 뒤)의 토큰/초를 세 번씩 잽니다. 1~3 분.' },
  { kind: 'crosscheck', title: '교차검증 (R1 · 32 문제)', needModel: false,
    desc: 'DeepSeek-R1-Distill-Qwen-7B Q8_0 으로 수학 문제 32 개를 탐욕 생성해 기준 PC(NVIDIA · CUDA)의 출력과 비트까지 견줍니다. 빌드 · 모듈 해시도 견줍니다. 모듈마다 5~20 분.' },
];
function renderBench() {
  const st = S.st;
  const j = st.job;
  const panel = $('#jobpanel');
  if (j) {
    panel.hidden = false;
    if (!panel.querySelector('pre.log') || panel.dataset.job != j.id) {
      panel.dataset.job = j.id;
      panel.replaceChildren(
        h('div', { class: 'row' }, h('b', { id: 'jobtitle' }), h('span', { id: 'jobstate', class: 'tag' }), h('span', { class: 'grow' }),
          h('button', { class: 'btn small', id: 'jobcancel', onclick: () => api('/api/job/cancel', {}).then(refresh) }, '멈춤')),
        h('div', { class: 'small', id: 'jobstep', style: 'margin:6px 0' }),
        h('div', { class: 'bar' }, h('i', { id: 'jobbar' })),
        h('div', { class: 'small muted', id: 'jobsum', style: 'margin-top:6px' }),
        h('pre', { class: 'log', id: 'joblog' }),
        h('details', { id: 'jobtaild' }, h('summary', { class: 'small muted' }, '지금 도는 도구의 출력'), h('pre', { class: 'log', id: 'jobtail' })));
      S.log = { job: j.id, from: 0 };
    }
    $('#jobtitle').textContent = j.title;
    const stTxt = { running: '도는 중', done: '끝', failed: '실패', cancelled: '멈춤' }[j.state] || j.state;
    const stEl = $('#jobstate');
    stEl.textContent = `${stTxt} · ${fmtDur(j.seconds)}`;
    stEl.className = 'tag ' + ({ running: 'acc', done: 'ok', failed: 'err', cancelled: 'warn' }[j.state] || '');
    $('#jobstep').textContent = j.step || '';
    $('#jobbar').style.width = (j.state === 'done' ? 100 : j.progress / 10) + '%';
    $('#jobcancel').hidden = j.state !== 'running';
    const sum = $('#jobsum');
    sum.replaceChildren();
    if (j.summary) sum.append(h('div', { style: 'color:var(--text)' }, j.summary));
    if (j.reason && j.state !== 'done') sum.append(h('div', { style: 'color:var(--err)' }, j.reason));
    if (j.result && j.state !== 'running') sum.append(h('div', { class: 'row', style: 'margin-top:6px' },
      h('button', { class: 'btn small primary', onclick: () => openResult(j.result) }, '결과 보기'),
      h('a', { class: 'btn small', href: '/api/results/zip?name=' + encodeURIComponent(j.result) }, 'zip 받기')));
    const tail = $('#jobtail');
    if (tail) tail.textContent = st.job_tail || '';
    $('#jobtaild').hidden = !st.job_tail;
  } else panel.hidden = true;
  if (sig('benchcards', [st.models.map(m => [m.id, m.device_reason, m.shape && m.shape.ok]), j && j.state])) {
    const runnable = runnableModels();
    $('#benchcards').replaceChildren(...BENCH.map(b => {
      const sel = b.needModel ? h('select', { class: 'bench-model' }, ...(runnable.length ? runnable.map(m => h('option', { value: m.id }, m.name || m.id)) : [h('option', { value: '' }, '돌릴 수 있는 모델이 없습니다')])) : null;
      let extra = null;
      if (b.kind === 'crosscheck') {
        extra = h('div', { class: 'col small' },
          h('label', { class: 'row' }, h('input', { type: 'checkbox', class: 'cc-quick' }), '줄인 판 — 문제 둘 · 토큰 64 (몇 분 — 길만 확인)'),
          h('label', { class: 'row' }, '모듈 ', h('select', { class: 'cc-mod' }, h('option', { value: 'both' }, '협력 행렬 · 기본 둘 다'), h('option', { value: 'coop' }, '협력 행렬만'), h('option', { value: 'base' }, '기본만'))));
      }
      const busy = j && j.state === 'running';
      return h('div', { class: 'card col' }, h('b', null, b.title), h('div', { class: 'small muted' }, b.desc), sel, extra,
        h('div', { class: 'row' }, h('button', {
          class: 'btn primary', disabled: busy ? true : null, onclick: async ev => {
            const card = ev.target.closest('.card');
            const body = {};
            if (b.needModel) { body.model = card.querySelector('.bench-model').value; if (!body.model) { toast('모델이 없습니다', 'err'); return; } }
            if (b.kind === 'crosscheck') { body.quick = card.querySelector('.cc-quick').checked; body.modules = card.querySelector('.cc-mod').value; }
            if (S.st.server.state === 'ready' && !(await confirmBox('GPU 를 비웁니다', h('p', null, '돌리는 동안 채팅 서버를 내립니다. 계속할까요?'), '계속'))) return;
            try { await api('/api/bench/' + b.kind, body); S.lastSig = {}; refresh(); }
            catch (e) { toast(e.message, 'err'); }
          }
        }, busy ? '다른 일이 도는 중' : '실행')));
    }));
  }
  if (Date.now() - S.resultsAt > 5000) loadResults(false);
}
async function pollLog() {
  const j = S.st && S.st.job;
  if (!j || S.view !== 'bench') return;
  if (S.log.job !== j.id) S.log = { job: j.id, from: 0 };
  const pre = $('#joblog');
  if (!pre) return;
  try {
    const r = await api('/api/job/log?from=' + S.log.from);
    if (r.id !== j.id) return;
    if (r.text) {
      const near = pre.scrollHeight - pre.scrollTop - pre.clientHeight < 40;
      pre.textContent += r.text;
      if (near) pre.scrollTop = pre.scrollHeight;
    }
    S.log.from = r.size;
  } catch (_) { }
}
const KIND = { '진단': '자기 진단', '속도': '속도', '교차검증': '교차검증' };
async function loadResults(force) {
  S.resultsAt = Date.now();
  let r;
  try { r = await api('/api/results'); } catch (_) { return; }
  if (!force && !sig('results', r)) return;
  S.results = r.results;
  const box = $('#results');
  if (!r.results.length) { box.replaceChildren(h('div', { class: 'muted' }, '아직 없습니다.')); return; }
  const rows = r.results.map(x => h('tr', null,
    h('td', null, KIND[x.kind] || x.kind),
    h('td', { class: 'mono small' }, x.stamp.replace(/^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})$/, '$1-$2-$3 $4:$5')),
    h('td', { class: 'small' }, (x.headline || '').split('\n')[0].slice(0, 160)),
    h('td', { style: 'white-space:nowrap' }, h('button', { class: 'btn small', onclick: () => openResult(x.name) }, '보기'), ' ',
      h('a', { class: 'btn small', href: '/api/results/zip?name=' + encodeURIComponent(x.name) }, 'zip'))));
  box.replaceChildren(h('div', { class: 'card', style: 'padding:4px 8px' }, h('table', null, h('thead', null, h('tr', null, h('th', null, '종류'), h('th', null, '때'), h('th', null, '결과'), h('th', null, ''))), h('tbody', null, rows))));
}
async function getFile(name, file) {
  const r = await fetch('/api/results/file?name=' + encodeURIComponent(name) + '&file=' + encodeURIComponent(file));
  if (!r.ok) return null;
  return file.endsWith('.json') ? r.json() : r.text();
}
async function openResult(name) {
  const box = $('#resultview');
  box.hidden = false;
  box.replaceChildren(h('div', { class: 'muted' }, '읽는 중…'));
  const [txt, summary, speed, diag] = await Promise.all([getFile(name, '결과.txt'), getFile(name, 'summary.json'), getFile(name, 'speed.json'), getFile(name, 'diag.json')]);
  const parts = [h('div', { class: 'row' }, h('b', null, name), h('span', { class: 'grow' }),
    h('a', { class: 'btn small primary', href: '/api/results/zip?name=' + encodeURIComponent(name) }, 'zip 받기'),
    h('button', { class: 'btn small', onclick: () => api('/api/open', { what: 'result', name }) }, '폴더 열기'),
    h('button', { class: 'btn small', onclick: () => { box.hidden = true; } }, '닫기'))];
  if (txt) parts.push(h('pre', { class: 'log' }, txt));
  if (speed && speed.cells) {
    parts.push(h('h3', null, '속도'), h('table', null, h('thead', null, h('tr', null, h('th', null, '칸'), h('th', { class: 'num' }, '시간'), h('th', { class: 'num' }, '토큰/초'))),
      h('tbody', null, speed.cells.map(c => h('tr', null, h('td', null, c.name),
        h('td', { class: 'num' }, c.prompt_ms !== undefined ? c.prompt_ms.toFixed(1) + ' ms' : c.ms_per_token.toFixed(2) + ' ms/토큰'),
        h('td', { class: 'num' }, c.tokens_per_s.toFixed(1)))))));
  }
  if (summary && summary.runs) {
    for (const run of summary.runs) {
      parts.push(h('h3', null, `${run.label} — ${run.same}/${run.total} 같음 · 슬롯 ${run.slots} · 생성 ${run.generate_minutes} 분`));
      if (run.error) parts.push(h('div', { style: 'color:var(--err)' }, run.error));
      const items = run.items || [];
      parts.push(h('div', { style: 'max-height:280px;overflow:auto' }, h('table', null,
        h('thead', null, h('tr', null, h('th', null, '문제'), h('th', null, '판정'), h('th', { class: 'num' }, '토큰'), h('th', { class: 'num' }, '기준 토큰'), h('th', null, '로짓 해시(SHA-256)'))),
        h('tbody', null, items.map(it => h('tr', null, h('td', null, it.id),
          h('td', null, h('span', { class: 'tag ' + (it.result === 'same' ? 'ok' : 'err') }, it.result === 'same' ? '같음' : it.result === 'different' ? `다름(글자 ${it.first_diff_char})` : '오류')),
          h('td', { class: 'num' }, it.n), h('td', { class: 'num' }, it.expected_n), h('td', { class: 'mono small' }, (it.logit_hashes_sha256 || '').slice(0, 16))))))));
    }
    if (summary.build) parts.push(h('h3', null, '빌드 · 모듈 해시'), h('div', { class: 'kv small mono' }, Object.entries(summary.build).flatMap(([k, v]) => [h('div', null, k), h('div', { style: 'word-break:break-all' }, v)])));
  }
  if (diag && diag['커널']) {
    const rows = Object.entries(diag['커널']).map(([k, v]) => h('tr', null, h('td', null, k), h('td', { class: 'num' }, (v['합_ms'] || 0).toFixed(2)), h('td', { class: 'num' }, v['배'] !== undefined ? v['배'].toFixed(2) : '-')));
    parts.push(h('h3', null, '자기 진단 — 칸마다'), h('table', null, h('thead', null, h('tr', null, h('th', null, '칸'), h('th', { class: 'num' }, '합(ms)'), h('th', { class: 'num' }, '바닥 대비'))), h('tbody', null, rows)));
  }
  box.replaceChildren(...parts);
  box.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ---------- 장치 ----------
async function renderDevice() {
  const d = S.st.device;
  if (sig('devsummary', d)) {
    const box = $('#devsummary');
    if (!d.checked) { box.replaceChildren(h('div', { class: 'muted' }, '확인하는 중…')); return; }
    box.replaceChildren(h('div', { class: 'kv' },
      h('div', null, 'GPU'), h('div', null, d.name || '-'),
      h('div', null, 'GPU 층'), h('div', null, d.layer ? layerName(d.layer) : h('span', { style: 'color:var(--err)' }, '없음 — ' + d.reason)),
      h('div', null, '메모리'), h('div', null, fmtBytes(d.memory)),
      h('div', null, '회사 · 드라이버'), h('div', null, `${d.vendor || '-'} · ${d.driver || '-'}`),
      h('div', null, '모듈 판'), h('div', null, d.layer === 'vulkan' ? (d.variant === '공유32' ? '공유32 — 공유 메모리 32 KB 장치의 판(셈은 같다)' : '보통') : 'CUDA(PTX)'),
      h('div', null, '협력 행렬'), h('div', null, d.layer === 'vulkan' ? (d.coop || '없음 — 텐서곱을 흉내 내는 기본 모듈') : '-'),
      h('div', null, 'CUDA · Vulkan'), h('div', null, `${d.cuda_ok ? 'CUDA 됨' : 'CUDA 안 됨'} · ${d.vulkan_ok ? 'Vulkan 됨' : 'Vulkan 안 됨'}`)));
    try {
      const raw = await api('/api/device');
      const vl = raw.vulkan && raw.vulkan['장치들'] ? raw.vulkan['장치들'] : [];
      $('#devvulkan').replaceChildren(...(vl.length ? vl.map(v => h('div', { class: 'card' },
        h('div', { class: 'row' }, h('b', null, v['이름']), v['고름'] ? h('span', { class: 'tag ok' }, 'GeulPU 가 고름') : null,
          v['돌릴수있음'] ? h('span', { class: 'tag ok' }, '돌릴 수 있음') : h('span', { class: 'tag err' }, '못 돌림')),
        h('div', { class: 'small muted' }, `Vulkan ${v['API']} · 드라이버 ${v['드라이버'] ? v['드라이버']['이름'] + ' ' + v['드라이버']['정보'] : ''} · 서브그룹 ${v['서브그룹'] ? v['서브그룹']['최소'] + '~' + v['서브그룹']['최대'] : ''} · 공유 ${(v['공유메모리'] / 1024) | 0} KB · 푸시 ${v['푸시상수']} B · 메모리 ${fmtBytes(v['장치메모리'])} · 협력 ${v['권하는_협력'] || '없음'}`),
        (v['막는것'] || []).map(x => h('div', { class: 'small', style: 'color:var(--err)' }, x)),
        (v['경고'] || []).map(x => h('div', { class: 'small', style: 'color:var(--warn)' }, x)))) : [h('div', { class: 'muted' }, '없음')]));
      const cl = raw.cuda && raw.cuda.devices ? raw.cuda.devices : [];
      $('#devcuda').replaceChildren(...(cl.length ? cl.map(c => h('div', { class: 'card' },
        h('div', { class: 'row' }, h('b', null, c.name), c.ok ? h('span', { class: 'tag ok' }, '돌릴 수 있음') : h('span', { class: 'tag err' }, '계산 능력 8.0 미만')),
        h('div', { class: 'small muted' }, `계산 능력 ${c.cc_major}.${c.cc_minor} · SM ${c.sm} · 메모리 ${fmtBytes(c.memory)} · 드라이버 CUDA ${(raw.cuda.driver_version / 1000) | 0}.${(raw.cuda.driver_version % 1000) / 10}`))) :
        [h('div', { class: 'muted' }, raw.cuda && raw.cuda.error ? raw.cuda.error : 'CUDA 없음(NVIDIA 드라이버의 nvcuda.dll)')]));
    } catch (_) { }
  }
}
$('#devcheck').addEventListener('click', () => api('/api/device/check', {}).then(() => { S.lastSig = {}; refresh(); }).catch(e => toast(e.message, 'err')));

// ---------- 설정 ----------
function renderSettings() {
  const st = S.st;
  if (sig('settings', st.settings)) {
    const s = st.settings;
    $('#set-layer').value = s.gpu_layer;
    $('#set-vkdev').value = s.vulkan_device || '';
    $('#set-slots').value = s.slots;
    $('#set-ctx').value = s.context;
    $('#set-mdir').value = s.models_dir || '';
    $('#set-update').checked = !!s.update_check;
  }
  if (sig('about', [st.app, S.update])) {
    const a = st.app;
    $('#about').replaceChildren(
      h('div', null, '판'), h('div', null, 'v' + a.version + (S.update && S.update.tag ? (newer(S.update.tag, a.version) ? ` — 새 판 ${S.update.tag}` : ' — 최신') : '')),
      h('div', null, '커밋'), h('div', { class: 'mono' }, a.commit || '(개발 빌드)'),
      h('div', null, '빌드'), h('div', null, a.built || '-'),
      h('div', null, '자료 폴더'), h('div', { class: 'mono small' }, a.data_dir),
      h('div', null, '모델 폴더'), h('div', { class: 'mono small' }, a.models_dir),
      h('div', null, '주소'), h('div', { class: 'mono small' }, `http://127.0.0.1:${a.port}/ · OpenAI 꼴 API http://127.0.0.1:${a.port}/v1`));
  }
}
$('#set-save').addEventListener('click', async () => {
  const before = S.st.settings.gpu_layer + '|' + S.st.settings.vulkan_device;
  const body = {
    gpu_layer: $('#set-layer').value, vulkan_device: $('#set-vkdev').value.trim(), slots: parseInt($('#set-slots').value, 10) || 2,
    context: parseInt($('#set-ctx').value, 10) || 8192, models_dir: $('#set-mdir').value.trim(), update_check: $('#set-update').checked,
  };
  try {
    await api('/api/settings', body);
    toast('저장했습니다', 'ok');
    if (before !== body.gpu_layer + '|' + body.vulkan_device) await api('/api/device/check', {}).catch(e => toast(e.message, 'err'));
    S.lastSig = {};
    refresh();
  } catch (e) { toast(e.message, 'err'); }
});
$('#opendata').addEventListener('click', () => api('/api/open', { what: 'data' }));
$('#theme').addEventListener('click', () => {
  const dark = matchMedia('(prefers-color-scheme: dark)').matches;
  const cur = document.documentElement.dataset.theme || (dark ? 'dark' : 'light');
  const next = cur === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = next;
  store('geulpu.theme', next);
});
$('#modal').addEventListener('click', e => { if (e.target.id === 'modal') closeModal(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape' && !$('#modal').hidden) closeModal(); });

// ---------- 시작 ----------
(async function start() {
  const th = load('geulpu.theme', null);
  if (th) document.documentElement.dataset.theme = th;
  S.rooms = load('geulpu.rooms', []);
  S.roomId = load('geulpu.room', null);
  await refresh();
  if (!S.rooms.length) newRoom(); else { if (!curRoom()) S.roomId = S.rooms[0].id; renderRooms(); renderMsgs(); }
  renderChatHead(true);
  let v = null;
  try { v = sessionStorage.getItem('geulpu.view'); } catch (_) { }
  if (v && v !== 'chat') show(v);
  checkUpdate();
})();
