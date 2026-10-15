// GeulPU 앱 화면 — 관리자(GeulPU.exe)의 /api 와 /v1 만 쓴다(바깥 자원 없음 — 새 버전 알림만 GitHub API 를 묻는다).
// 디자인: x.ai 디자인 시스템(앱/DESIGN.md) — 어둠 한 가지, 알약 버튼, 8px 카드 · 머리카락 선, 강조색 선셋 오렌지 하나.
'use strict';

// ---------- 아이콘(24 × 24, 선 1.7 — 이 앱에서 그린 것) ----------
const IC = {
  chat: '<path d="M20.5 11.5c0 4.4-3.8 8-8.5 8-1.2 0-2.3-.2-3.3-.6L3.5 20l1.3-4c-.8-1.3-1.3-2.8-1.3-4.5 0-4.4 3.8-8 8.5-8s8.5 3.6 8.5 8z"/>',
  box: '<path d="M12 2.8 20.2 7.3v9.4L12 21.2l-8.2-4.5V7.3z"/><path d="M3.8 7.3 12 11.8l8.2-4.5M12 11.8v9.4"/>',
  pulse: '<path d="M3 12h3.5l2.5-7 4 14 2.5-7H21"/>',
  cpu: '<rect x="5" y="5" width="14" height="14" rx="2"/><rect x="9" y="9" width="6" height="6" rx="1"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
  gear: '<path d="M19.15 10.08 L21.51 10.66 L21.51 13.34 L19.15 13.92 L18.41 15.70 L19.67 17.78 L17.78 19.67 L15.70 18.41 L13.92 19.15 L13.34 21.51 L10.66 21.51 L10.08 19.15 L8.30 18.41 L6.22 19.67 L4.33 17.78 L5.59 15.70 L4.85 13.92 L2.49 13.34 L2.49 10.66 L4.85 10.08 L5.59 8.30 L4.33 6.22 L6.22 4.33 L8.30 5.59 L10.08 4.85 L10.66 2.49 L13.34 2.49 L13.92 4.85 L15.70 5.59 L17.78 4.33 L19.67 6.22 L18.41 8.30 Z"/><circle cx="12" cy="12" r="3"/>',
  sliders: '<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  up: '<path d="M12 19V5M6 11l6-6 6 6"/>',
  down: '<path d="M12 5v14M6 13l6 6 6-6"/>',
  stop: '<rect x="7.5" y="7.5" width="9" height="9" rx="1.5" fill="currentColor" stroke="none"/>',
  pause: '<path d="M9 6.5v11M15 6.5v11"/>',
  download: '<path d="M12 4v11M7 10.5l5 5 5-5M5 20h14"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  checkc: '<circle cx="12" cy="12" r="8.5"/><path d="m8.5 12.2 2.4 2.4 4.6-4.8"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  trash: '<path d="M4 7h16M9.5 7V4.5h5V7M6.5 7l1 12.5h9l1-12.5M10 11v5.5M14 11v5.5"/>',
  edit: '<path d="M4.5 19.5l1-4 10-10 3 3-10 10z"/><path d="M13.5 7.5l3 3"/>',
  dots: '<circle cx="5.5" cy="12" r="1.3" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1.3" fill="currentColor" stroke="none"/><circle cx="18.5" cy="12" r="1.3" fill="currentColor" stroke="none"/>',
  folder: '<path d="M3.5 7.5A1.5 1.5 0 0 1 5 6h4.2l2 2H19a1.5 1.5 0 0 1 1.5 1.5v8A1.5 1.5 0 0 1 19 19H5a1.5 1.5 0 0 1-1.5-1.5z"/>',
  file: '<path d="M6.5 3.5h7l4 4v13h-11z"/><path d="M13.5 3.5v4h4"/>',
  refresh: '<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3M19.5 4.5v4h-4"/>',
  chevD: '<path d="M7 10l5 5 5-5"/>',
  chevR: '<path d="M10 7l5 5-5 5"/>',
  chevL: '<path d="M14 7l-5 5 5 5"/>',
  code: '<path d="m8.5 7.5-5 4.5 5 4.5M15.5 7.5l5 4.5-5 4.5"/>',
  type: '<path d="M5.5 6.5V5h13v1.5M12 5v14M9 19h6"/>',
  hash: '<path d="M10 4 8 20M16 4l-2 16M4.5 9h15M3.5 15h15"/>',
  target: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/>',
  chevU: '<path d="M7 14l5-5 5 5"/>',
  ext: '<path d="M14 4.5h5.5V10M19.5 4.5 11 13M17.5 14v4.5a1 1 0 0 1-1 1h-11a1 1 0 0 1-1-1v-11a1 1 0 0 1 1-1H10"/>',
  alert: '<path d="M12 4 2.8 19.5h18.4z"/><path d="M12 10v4.2M12 16.8v.2"/>',
  info: '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5M12 8v.2"/>',
  play: '<path d="M8 5.5v13l10.5-6.5z"/>',
  shield: '<path d="M12 3.5 19 6v5.5c0 4.4-3 7.6-7 8.9-4-1.3-7-4.5-7-8.9V6z"/><path d="M9 12l2.2 2.2L15.5 10"/>',
  copy: '<rect x="8.5" y="8.5" width="11" height="11" rx="2"/><path d="M15.5 8.5V6a1.5 1.5 0 0 0-1.5-1.5H6A1.5 1.5 0 0 0 4.5 6v8A1.5 1.5 0 0 0 6 15.5h2.5"/>',
  panel: '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M9.5 4.5v15"/>',
  spark: '<path d="M12 3.5l1.9 5.1 5.1 1.9-5.1 1.9-1.9 5.1-1.9-5.1-5.1-1.9 5.1-1.9z"/>',
  gauge: '<path d="M3.5 16a8.5 8.5 0 1 1 17 0"/><path d="M12 16l4.5-5"/><circle cx="12" cy="16" r="1.4"/><path d="M5 20h14"/>',
  layers: '<path d="M12 3.5 21 8l-9 4.5L3 8z"/><path d="M3 12.5l9 4.5 9-4.5M3 16.5 12 21l9-4.5"/>',
  bolt: '<path d="M13 3 5 13.5h6L10 21l8-10.5h-6z"/>',
  star: '<path d="M12 3.8l2.5 5.2 5.7.8-4.1 4 1 5.6L12 16.7l-5.1 2.7 1-5.6-4.1-4 5.7-.8z"/>',
  terminal: '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="m7.5 9.5 3 2.5-3 2.5M12.5 15h4"/>',
  eject: '<path d="M12 5.5 5 13.5h14z"/><path d="M5 18.5h14"/>',
  forward: '<path d="M5 12h12M12.5 6.5 18 12l-5.5 5.5"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 5 5"/>',
  heart: '<path d="M12 19.6s-7.6-4.5-7.6-9.8A4.2 4.2 0 0 1 12 7.4a4.2 4.2 0 0 1 7.6 2.4c0 5.3-7.6 9.8-7.6 9.8z"/>',
  clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
};
const svg = (n, cls) => `<svg class="i ${cls || ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${IC[n] || ''}</svg>`;

// ---------- 도움 ----------
const $ = (s, r = document) => r.querySelector(s);
const keep = a => a.flat(Infinity).filter(x => x !== null && x !== undefined && x !== false);
function h(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  if (attrs) for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') e.className = v;
    else if (k === 'html') e.innerHTML = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? '' : v);
  }
  for (const k of keep(kids)) e.append(k instanceof Node ? k : document.createTextNode(String(k)));
  return e;
}
// 자식 갈기 — null · undefined · false 는 빼고(화면에 "null" 이 찍히지 않게)
const put = (el, ...kids) => { if (el) el.replaceChildren(...keep(kids)); return el; };
const I = (n, cls) => { const t = document.createElement('template'); t.innerHTML = svg(n, cls); return t.content.firstChild; };
const esc = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const NB = '\u00a0· ';   // 가운뎃점이 줄 머리에 오지 않게
const GIB = 1073741824;
// 크기는 1024 단위(윈도 탐색기와 같은 수 — VRAM 12 GB 카드는 12.0 GB)
function fmtBytes(n) {
  if (!(n >= 0)) return '-';
  const M = 1048576, K = 1024;
  if (n >= GIB) return (n / GIB).toFixed(n >= 100 * GIB ? 0 : 1) + '\u00a0GB';
  if (n >= M) return Math.round(n / M) + '\u00a0MB';
  if (n >= K) return Math.round(n / K) + '\u00a0KB';
  return n + '\u00a0B';
}
const fmtNum = (x, d) => Number(x).toLocaleString('ko-KR', { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 });
// 하드웨어 한계 대비 — 진단 도구의 '배'(잰 시간 ÷ 한계 시간)를 백분율로(높을수록 한계에 가깝다)
const effOf = x => (x > 0 ? Math.round(100 / x) : NaN);
const fmtEff = p => (p >= 0 ? p + '%' : '-');
function fmtClock(s) {
  if (!(s >= 0) || !isFinite(s)) return '-';
  s = Math.round(s);
  const m = Math.floor(s / 60), r = s % 60;
  if (m < 60) return m + ':' + String(r).padStart(2, '0');
  return Math.floor(m / 60) + ':' + String(m % 60).padStart(2, '0') + ':' + String(r).padStart(2, '0');
}
function fmtLeft(s) {
  if (!(s >= 0) || !isFinite(s)) return '남은 시간 계산 중';
  s = Math.round(s);
  if (s < 60) return '1분 안에 끝남';
  const m = Math.round(s / 60);
  if (m < 60) return `약 ${m}분 남음`;
  return `약 ${Math.floor(m / 60)}시간 ${m % 60}분 남음`;
}
const fmtCtx = n => (n >= 1024 && n % 1024 === 0 ? (n / 1024) + 'K' : fmtNum(n || 0));
async function api(path, body) {
  const opt = body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
  const r = await fetch(path, opt);
  let j = null;
  try { j = await r.json(); } catch (_) { }
  if (!r.ok) throw new Error((j && j.error && j.error.message) || ('HTTP ' + r.status));
  return j;
}
function toast(msg, kind) {
  const close = h('button', { class: 'icon-btn', 'aria-label': '알림 닫기' }, I('x', 's'));
  const d = h('div', { class: kind || '', role: kind === 'err' ? 'alert' : 'status' }, I(kind === 'err' ? 'alert' : kind === 'ok' ? 'check' : 'info', 's'), h('span', null, msg), close);
  close.addEventListener('click', () => d.remove());
  $('#toast').append(d);
  setTimeout(() => d.remove(), kind === 'err' ? 10000 : 4000);
}
const announce = t => { const e = $('#sr-live'); if (e) { e.textContent = ''; setTimeout(() => { e.textContent = t; }, 50); } };
let storeWarned = false;
function store(key, val) {
  try { localStorage.setItem(key, JSON.stringify(val)); }
  catch (_) { if (key === 'geulpu.rooms' && !storeWarned) { storeWarned = true; toast('브라우저 저장 공간이 부족해 채팅을 저장하지 못했습니다 — 오래된 채팅을 삭제하세요', 'err'); } }
}
function load(key, dflt) { try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : dflt; } catch (_) { return dflt; } }
const SIG = {};
function changed(name, obj) { const s = JSON.stringify(obj); if (SIG[name] === s) return false; SIG[name] = s; return true; }
const resetSig = () => { for (const k of Object.keys(SIG)) delete SIG[k]; };
async function copyText(text) {
  try { await navigator.clipboard.writeText(text); return true; } catch (_) { toast('복사하지 못했습니다', 'err'); return false; }
}

// 창(가운데) — 머리(닫기)와 바닥(단추)은 그대로, 가운데만 스크롤. 초점은 창 안에 가두고, 닫으면 연 자리로 돌려준다
let modalReturn = null, modalOnClose = null;
function modal(content, buttons, wide, focusSel, onClose) {
  const box = $('#modalbox');
  if ($('#modal').hidden) modalReturn = document.activeElement;
  modalOnClose = onClose || null;
  box.className = 'box' + (wide ? ' wide' : '');
  const body = h('div', { class: 'mb' }, content);
  put(box, body, buttons && buttons.length ? h('div', { class: 'foot' }, buttons) : null,
    h('button', { class: 'icon-btn x', 'aria-label': '닫기', onclick: () => closeModal() }, I('x')));
  const t = box.querySelector('h2');
  if (t) t.id = 'modal-title';
  $('#modal').hidden = false;
  body.scrollTop = 0;
  const f = (focusSel && box.querySelector(focusSel)) || box.querySelector('.foot .primary') || box.querySelector('.mb input, .mb textarea') || box.querySelector('.foot button, .foot a') || box.querySelector('.x');
  if (f) setTimeout(() => { f.focus({ preventScroll: true }); if (f.select && f.type === 'text') f.select(); }, 0);
}
function closeModal() {
  if ($('#modal').hidden) return;
  $('#modal').hidden = true;
  put($('#modalbox'));
  const cb = modalOnClose;
  modalOnClose = null;
  if (cb) cb();
  if (modalReturn && modalReturn.isConnected && modalReturn.focus) modalReturn.focus({ preventScroll: true });
  modalReturn = null;
}
// kind: 'danger'(지우기 등) · 'quiet'(권하지 않는 동작 — 흰 채움 없이, 초점은 취소에)
function confirmBox(title, body, okText, kind) {
  return new Promise(res => {
    let done = false;
    const fin = v => { if (!done) { done = true; res(v); } };
    const no = h('button', { class: 'btn ghost', onclick: () => closeModal() }, '취소');
    const ok = h('button', { class: 'btn ' + (kind === 'danger' ? 'danger' : kind === 'quiet' ? '' : 'primary'), onclick: () => { fin(true); closeModal(); } }, okText || '확인');
    modal(h('div', null, h('h2', null, title), body), [no, ok], false, kind ? '.foot .btn.ghost' : null, () => fin(false));
  });
}
$('#modal').addEventListener('click', e => { if (e.target.id === 'modal') closeModal(); });
$('#modal').addEventListener('keydown', e => {
  if (e.key !== 'Tab') return;
  const f = [...$('#modalbox').querySelectorAll('button, a[href], input, textarea, select, summary')].filter(x => !x.disabled && x.offsetParent);
  if (!f.length) return;
  const first = f[0], last = f[f.length - 1];
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
});

// 뜨는 판(메뉴) — 기준 요소 아래
let POP = null, POPANCHOR = null;
function closePop() {
  if (POP) { POP.remove(); POP = null; }
  if (POPANCHOR) { POPANCHOR.setAttribute('aria-expanded', 'false'); POPANCHOR = null; }
}
// 판의 자리 — 기준 요소 아래, 모자라면 위. 내용이 자란 뒤에도 다시 부른다(다운로드 목록)
function placePop(p, anchor, align) {
  const r = anchor.getBoundingClientRect();
  const w = p.offsetWidth, hh = p.offsetHeight;
  let x = align === 'right' ? r.right - w : r.left;
  x = Math.max(8, Math.min(x, innerWidth - w - 8));
  let y = r.bottom + 6;
  if (y + hh > innerHeight - 8) y = Math.max(8, r.top - hh - 6);
  p.style.left = x + 'px';
  p.style.top = y + 'px';
}
function openPop(anchor, content, align) {
  closePop();
  const p = h('div', { class: 'pop' }, content);
  document.body.append(p);
  placePop(p, anchor, align);
  POP = p;
  POPANCHOR = anchor;
  anchor.setAttribute('aria-expanded', 'true');
  // 판 밖으로 초점이 나가면 닫는다(창 꼴의 판 — 메뉴는 Tab 에서 닫힌다)
  p.addEventListener('focusout', e => { if (POP === p && e.relatedTarget && !p.contains(e.relatedTarget) && e.relatedTarget !== POPANCHOR) closePop(); });
  const f = p.querySelector('.opt.sel:not(:disabled)') || p.querySelector('.opt:not(:disabled), input, textarea, button');
  if (f) setTimeout(() => f.focus({ preventScroll: true }), 0);
  return p;
}
function menu(anchor, label, items, align) {
  const opts = items.filter(Boolean).map(it => it === '-' ? h('div', { class: 'sep', role: 'separator' }) : h('button', {
    class: 'opt' + (it.danger ? ' danger' : ''), role: 'menuitem', disabled: it.disabled ? true : null,
    onclick: () => { closePop(); it.run(); },
  }, I(it.icon, 's'), h('span', { class: 'main' }, h('div', { class: 't' }, it.label), it.sub ? h('div', { class: 's' }, it.sub) : null)));
  openPop(anchor, h('div', { role: 'menu', 'aria-label': label }, opts), align);
}
document.addEventListener('mousedown', e => { if (POP && !POP.contains(e.target) && !(POPANCHOR && POPANCHOR.contains(e.target))) closePop(); });
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    if (POP) { const a = POPANCHOR; closePop(); if (a) a.focus(); }
    else if (!$('#modal').hidden) closeModal();
    else if (overlayConvos() && !$('#convos').classList.contains('closed')) setConvos(false);
    else if (streamingHere() && S.view === 'chat') stopStream();
  }
  // 메뉴: 위아래 화살표로 고르고, Tab 은 메뉴를 닫고 다음 요소로(메뉴 항목은 Tab 정거장이 아니다)
  if (POP && POP.querySelector('[role=menu]') && POP.contains(document.activeElement)) {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Home' || e.key === 'End') {
      const opts = [...POP.querySelectorAll('.opt:not(:disabled)')];
      if (!opts.length) return;
      e.preventDefault();
      let i = opts.indexOf(document.activeElement);
      i = e.key === 'Home' ? 0 : e.key === 'End' ? opts.length - 1 : e.key === 'ArrowDown' ? (i + 1) % opts.length : (i - 1 + opts.length) % opts.length;
      opts[i].focus();
    } else if (e.key === 'Tab') { const a = POPANCHOR; closePop(); if (a) a.focus(); }
  }
});

// 도움말(말풍선) — 떠 있는 요소 하나로(넘침을 잘라 내는 상자 안에서도). 마우스는 잠깐 머문 뒤, 키보드 초점은 바로
const TIP = h('div', { id: 'tip', role: 'tooltip', hidden: true });
document.body.append(TIP);
let tipEl = null, tipTimer = 0;
const noHover = matchMedia('(hover: none)');
function hideTip() { clearTimeout(tipTimer); if (tipEl) tipEl.removeAttribute('aria-describedby'); tipEl = null; TIP.hidden = true; }
function showTip(el) {
  if (!el.isConnected || !el.dataset.tip) return;
  tipEl = el;
  TIP.textContent = el.dataset.tip;
  TIP.hidden = false;
  if (!el.hasAttribute('aria-label') || el.getAttribute('aria-label') !== el.dataset.tip) el.setAttribute('aria-describedby', 'tip');
  const r = el.getBoundingClientRect(), w = TIP.offsetWidth, hh = TIP.offsetHeight, gap = 8;
  const fits = { right: r.right + gap + w <= innerWidth - 8, left: r.left - gap - w >= 8, top: r.top - gap - hh >= 8, bottom: r.bottom + gap + hh <= innerHeight - 8 };
  const want = el.dataset.tipPos || 'right';
  const p = [want, { right: 'left', left: 'right', top: 'bottom', bottom: 'top' }[want], 'bottom', 'top'].find(o => fits[o]) || want;
  let x, y;
  if (p === 'right' || p === 'left') { x = p === 'right' ? r.right + gap : r.left - gap - w; y = r.top + r.height / 2 - hh / 2; }
  else { x = r.left + r.width / 2 - w / 2; y = p === 'bottom' ? r.bottom + gap : r.top - gap - hh; }
  TIP.style.left = Math.round(Math.max(8, Math.min(x, innerWidth - w - 8))) + 'px';
  TIP.style.top = Math.round(Math.max(8, Math.min(y, innerHeight - hh - 8))) + 'px';
}
document.addEventListener('mouseover', e => {
  if (noHover.matches) return;
  const el = e.target.closest ? e.target.closest('[data-tip]') : null;
  if (el === tipEl) return;
  hideTip();
  if (el) tipTimer = setTimeout(() => showTip(el), 450);
});
document.addEventListener('focusin', e => {
  const el = e.target.closest ? e.target.closest('[data-tip]') : null;
  hideTip();
  if (el && el === e.target && el.matches(':focus-visible')) showTip(el);
});
document.addEventListener('focusout', hideTip);
document.addEventListener('mousedown', hideTip, true);
document.addEventListener('scroll', hideTip, true);
document.addEventListener('keydown', e => { if (e.key === 'Escape' || e.key === 'Enter') hideTip(); }, true);

// ---------- 상태 ----------
// streaming: 지금 흐르는 답 하나 — { roomId, msg, el(지금 그려진 요소), notice(불러오기 카드), ctrl, aborted, loading }
// editing: 고치는 중인 사용자 메시지 { roomId, k } · jobHide: 닫은 '끝난 작업' 카드
const S = { st: null, view: 'chat', rooms: [], roomId: null, streaming: null, editing: null, log: { job: 0, from: 0 }, results: null, resultsAt: 0, update: null, conn: true, setDirty: false, vk: null, benchModel: load('geulpu.benchModel', ''), catSel: {}, jobHide: load('geulpu.jobHide', '') };
const streamingHere = () => !!(S.streaming && S.streaming.roomId === S.roomId);
let failCount = 0;
async function refresh() {
  try {
    const st = await api('/api/state');
    S.st = st;
    failCount = 0;
    if (!S.conn) { S.conn = true; setOffline(false); }
    renderAll();
    await pollLog();
  } catch (_) {
    failCount++;
    if (failCount >= 2 && S.conn) { S.conn = false; setOffline(true); }
  }
}
setInterval(() => { if (!document.hidden) refresh(); }, 1000);
function setOffline(off) {
  document.body.classList.toggle('offline', off);
  renderStatus();
  updateComposer();
  const b = $('#banner');
  if (off) {
    put(b, I('alert', 's'), h('span', null, 'GeulPU.exe와 연결이 끊겼습니다. 다시 연결하는 중… GeulPU.exe가 실행 중인지 확인하세요.'));
    b.className = 'offline';
    b.hidden = false;
  } else if (b.classList.contains('offline')) { b.className = ''; b.hidden = true; checkUpdate(); }
}
function renderAll() {
  if (!S.st) return;
  renderStatus();
  if (S.view === 'chat') { renderChatTop(); if (!curRoom() || !curRoom().messages.length) renderMsgsIfChanged(); }
  else if (S.view === 'models') renderModels();
  else if (S.view === 'bench') renderBench();
  else if (S.view === 'device') renderDevice();
  else if (S.view === 'settings') renderSettings();
  if (POP && POP.dataset.kind === 'dl') refreshDlPop();
  if (POPANCHOR && !POPANCHOR.isConnected) closePop();   // 다시 그려 기준 단추가 사라졌으면 판도 닫는다
  updateDlBars();
}
// 화면을 다시 그려도 키보드 초점을 같은 자리(data-fk)로 돌려준다
function rebuild(page, ...kids) {
  const a = document.activeElement;
  const key = a && page.contains(a) ? a.dataset.fk : null;
  put(page, ...kids);
  if (key) { const b = page.querySelector(`[data-fk="${CSS.escape(key)}"]`); if (b) b.focus({ preventScroll: true }); }
}

// ---------- 이름 ----------
const LAYER = { cuda: 'CUDA', vulkan: 'Vulkan' };
// GGUF 의 이름(띄어 씀)을 목록의 꼴(하이픈)로 — 한 모델은 어디서나 한 이름
function prettyName(n) { return String(n || '').trim().replace(/\s+/g, '-'); }
function catalogOf(m) { return m && m.catalog && S.st ? S.st.catalog.find(c => c.id === m.catalog) : null; }
function displayName(m) {
  if (!m) return '';
  const c = catalogOf(m);
  return c ? c.name : prettyName(m.name || m.id);
}
function modelOf(id) { return S.st ? S.st.models.find(m => m.id === id) : null; }
function labelById(id) {
  const m = modelOf(id);
  if (m) return `${displayName(m)} · ${quantOf(m)}`;
  const c = S.st && S.st.catalog.find(x => x.id === id);
  return c ? `${c.name} · ${c.quant}` : (id || '');
}
// 양자화 이름 — k-양자화 파일은 관리자가 "K" 로만 알려 주므로 목록의 이름(Q4_K_M 등)이나 가중치 형식으로 채운다
function quantOf(m) {
  const s = (m && m.shape) || {};
  if (s.quant && s.quant !== 'K') return s.quant;
  const c = catalogOf(m);
  if (c && c.quant) return c.quant;
  return s.weight_type || s.quant || '';
}
const QORDER = ['F32', 'F16', 'BF16', 'Q8_0', 'Q6_K', 'Q5_K_M', 'Q5_K_S', 'Q4_K_M', 'Q4_K_S', 'Q4_0'];
const qRank = q => { const i = QORDER.indexOf(q); return i < 0 ? 99 : i; };
const byName = (a, b) => a.localeCompare(b, 'en', { numeric: true });
// 같은 모델의 양자화들이 붙어 있게: 이름(숫자는 크기 순) → 양자화
function sortedModels() {
  return [...S.st.models].sort((a, b) => byName(displayName(a), displayName(b)) || qRank(quantOf(a)) - qRank(quantOf(b)));
}
// 모델의 종류 — 추론(생각을 먼저 쓰는 R1) · 코드(Coder) · 일반 대화. 이름은 GGUF(띄어 씀)와 목록(하이픈) 어느 꼴이든.
// 이름 앞에 종류 아이콘(동그라미)은 두지 않는다 — 종류는 글로 보인다
function kindKey(x) {
  const n = [x && x.catalog, x && x.id, x && x.name].filter(Boolean).join(' ').toLowerCase();
  if ((x && x.template === 'deepseek-r1') || /deepseek[\s_-]*r1/.test(n)) return 'think';
  if (/(^|[^a-z])coder/.test(n)) return 'code';          // 'text-encoder' 는 코드 모델이 아니다
  if ((x && x.template === 'qwen3') || /qwen3/.test(n)) return 'think';   // Qwen3 — 생각 켬 · 끔을 고르는 모델
  return 'chat';
}
const qtag = m => (quantOf(m) ? h('span', { class: 'qlab' }, quantOf(m)) : null);
const kindOf = m => ({ think: '추론 모델', code: '코드 모델', chat: '일반 모델' })[kindKey(m)];
function jobName(j) { return { diag: '하드웨어 진단', speed: '속도 측정', crosscheck: '재현성 검증', server: '모델 불러오기', device: '하드웨어 확인' }[j.kind] || j.title; }
const jobModel = j => String(j.title || '').split(' — ')[1] || '';
function jobTitle(j) {
  if (j.kind === 'diag' || j.kind === 'speed' || j.kind === 'server') return `${jobName(j)} · ${labelById(jobModel(j))}`;
  if (j.kind === 'crosscheck') return /줄인|빠른/.test(j.title) ? '재현성 검증 · 빠른 확인(문제 2개)' : '재현성 검증 · 문제 32개';
  return j.title;
}
// 재현성 검증의 경로 이름(관리자의 "협력 행렬 모듈 …" 등)을 쓰는 사람의 말로
function pathLabel(l) {
  return String(l || '').replace(/협력 행렬 모듈\s*([0-9x]*)/g, (_, s) => '텐서 코어 경로' + (s ? ` (${s})` : '')).replace(/기본 모듈/g, '기본 경로').replace(/CUDA 모듈/g, 'CUDA 경로');
}
// 10B 이상이면 문맥 · 작업 메모리를 더 크게 어림한다(목록의 "14B" · Hugging Face 에서 더한 "14.8B" 모두)
const isBig = c => { const p = parseFloat(String(c.params || '').replace(/[^\d.]/g, '')); return p >= 10 || (!(p > 0) && /\b(1[0-9]|[2-9]\d)b\b/i.test(c.id || '')); };
// 이 PC 의 그래픽 메모리에 맞는가(목록의 크기 + 문맥 · 작업 메모리 어림)
function fitOf(c) {
  const d = S.st && S.st.device;
  if (!d || !d.checked) return null;
  if (!d.layer) return { k: 'nogpu', t: '쓸 수 있는 GPU 없음' };
  if (c.devices === 'k' && d.layer === 'vulkan' && d.variant === '공유32') return { k: 'unsup', t: '이 GPU 미지원' };
  const big = isBig(c);
  const mem = d.memory / GIB, size = c.size / GIB;
  if (mem >= size + (big ? 4 : 2.5)) return { k: 'ok', t: '이 PC에 맞음' };
  if (mem >= size + (big ? 1.5 : 1)) return { k: 'tight', t: '빠듯함 · 문맥이 줄어듦' };
  return { k: 'no', t: '그래픽 메모리 부족' };
}
const FITRANK = { ok: 0, tight: 1, no: 2, unsup: 3, nogpu: 4 };
function fitTag(f) {
  if (!f) return null;
  if (f.k === 'ok') return h('span', { class: 'tag' }, I('check'), f.t);
  if (f.k === 'tight') return h('span', { class: 'tag', 'data-tip': '실행되지만 그래픽 메모리에 맞추느라 문맥 길이가 줄어듭니다', 'data-tip-pos': 'top' }, I('info'), f.t);
  return h('span', { class: 'tag dim' }, I('alert'), f.t);
}

// ---------- 레일 · 상태 막대 ----------
const RAIL_ICON = { chat: 'chat', models: 'box', bench: 'gauge', device: 'cpu', settings: 'gear' };
document.querySelectorAll('.rail-btn').forEach(b => {
  b.innerHTML = svg(RAIL_ICON[b.dataset.view], 'l') + `<span class="lbl" aria-hidden="true">${esc(b.getAttribute('aria-label'))}</span>`;
  b.addEventListener('click', () => show(b.dataset.view));
});
function show(view) {
  closePop();
  const same = S.view === view;
  S.view = view;
  document.querySelectorAll('.rail-btn').forEach(b => {
    const on = b.dataset.view === view;
    b.classList.toggle('active', on);
    if (on) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current');
  });
  document.querySelectorAll('.view').forEach(v => v.classList.toggle('active', v.id === 'view-' + view));
  resetSig();
  renderAll();
  if (view === 'bench') loadResults(true);
  if (view === 'settings') loadVk();
  if (view === 'chat') { if (!same) renderMsgs(); setTimeout(() => { if (!$('#input').disabled) $('#input').focus(); }, 0); }
  try { sessionStorage.setItem('geulpu.view', view); } catch (_) { }
}
// 상태 막대는 칸마다 제자리에서 고친다 — 초점이 있는 단추를 갈아 끼우지 않게
function renderStatus() {
  const bar = $('#statusbar');
  const segs = [];
  if (!S.conn) segs.push({ key: 'off', dot: 'err', text: 'GeulPU.exe와 연결 끊김' });
  else if (S.st) {
    const st = S.st, d = st.device, sv = st.server, j = st.job;
    if (!d.checked) segs.push({ key: 'gpu', dot: 'busy', text: '하드웨어 확인 중' });
    else if (!d.layer) segs.push({ key: 'gpu', btn: () => show('device'), tip: d.reason, dot: 'err', text: '쓸 수 있는 GPU 없음' });
    else segs.push({ key: 'gpu', btn: () => show('device'), tip: '하드웨어 보기', dot: 'ok', text: `${d.name} · ${LAYER[d.layer]} · ${fmtBytes(d.memory)}` });
    const svDot = { starting: 'busy', ready: 'ok', failed: 'err' }[sv.state] || '';
    const svTxt = sv.state === 'ready' ? `${labelById(sv.model)} · 동시 ${sv.slots}개 · 문맥 ${fmtCtx(sv.context)}`
      : sv.state === 'starting' ? `모델 불러오는 중 · ${fmtClock(sv.seconds)}` : sv.state === 'failed' ? '모델 불러오기 실패' : '불러온 모델 없음';
    segs.push({ key: 'srv', tip: sv.reason || '', dot: svDot, text: svTxt });
    if (j && j.state === 'running' && j.kind !== 'server' && j.kind !== 'device') segs.push({ key: 'job', btn: () => show('bench'), tip: '벤치마크 보기', mini: j.progress / 10, text: `${jobName(j)} ${Math.round(j.progress / 10)}%` });
    // 다운로드 — 받는 중이면 진행, 멈춤 · 실패만 남았으면 그 수. 누르면 다운로드 목록
    const all = dlList(), act = all.filter(c => c.download.state === 'downloading' || c.download.state === 'verifying');
    const openDl = ev => openDownloads(ev.currentTarget);
    if (act.length) {
      const tot = act.reduce((a, c) => a + c.download.total, 0), got = act.reduce((a, c) => a + c.download.received, 0);
      const bps = act.reduce((a, c) => a + (c.download.bytes_per_s || 0), 0);
      const fail = all.filter(c => dlStateOf(c) === 'fail').length, pause = all.length - act.length - fail;
      segs.push({ key: 'dl', btn: openDl, tip: '다운로드 목록', icon: 'download',
        text: `다운로드 ${act.length}개 · ${Math.round(100 * got / Math.max(1, tot))}% · ${fmtBytes(bps)}/s${pause ? ` · 멈춤 ${pause}개` : ''}${fail ? ` · 실패 ${fail}개` : ''}` });
    } else if (all.length) {
      const fail = all.filter(c => dlStateOf(c) === 'fail').length, pause = all.length - fail;
      segs.push({ key: 'dl', btn: openDl, tip: '다운로드 목록', dot: fail ? 'err' : undefined, icon: fail ? null : 'pause',
        text: ['다운로드', pause ? `멈춤 ${pause}개` : null, fail ? `실패 ${fail}개` : null].filter(Boolean).join(' · ') });
    }
    segs.push({ key: 'grow', grow: true }, { key: 'ver', text: 'v' + st.app.version });
  }
  const old = new Map([...bar.children].map(e => [e.dataset.key, e]));
  let prev = null;
  for (const sp of segs) {
    const tag = sp.grow ? 'span' : sp.btn ? 'button' : 'span';
    let e = old.get(sp.key);
    if (e && e.tagName.toLowerCase() !== tag) { e.remove(); e = null; }
    if (!e) e = h(tag, { class: sp.grow ? 'grow' : 'seg', 'data-key': sp.key });
    old.delete(sp.key);
    if (!sp.grow) {
      e.onclick = sp.btn || null;
      if (sp.key === 'dl') e.setAttribute('aria-haspopup', 'dialog'); else e.removeAttribute('aria-haspopup');
      if (sp.tip) { e.dataset.tip = sp.tip; e.dataset.tipPos = 'top'; } else delete e.dataset.tip;
      const sig = JSON.stringify([sp.dot, sp.icon, sp.mini !== undefined, sp.text]);
      if (e.dataset.sig !== sig) {
        e.dataset.sig = sig;
        put(e, sp.dot !== undefined ? h('i', { class: 'dot ' + sp.dot }) : null, sp.icon ? I(sp.icon, 's') : null,
          sp.mini !== undefined ? h('span', { class: 'mini' }, h('i', { style: `width:${sp.mini}%` })) : null, h('span', null, sp.text));
      }
    }
    if (prev ? prev.nextSibling !== e : bar.firstChild !== e) { if (prev) prev.after(e); else bar.prepend(e); }
    prev = e;
  }
  for (const e of old.values()) e.remove();
}

// 새 버전 알림
function verNum(v) { return String(v || '').replace(/^v/, '').split('.').map(x => parseInt(x, 10) || 0); }
function newer(a, b) { const x = verNum(a), y = verNum(b); for (let i = 0; i < 3; i++) { if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) > (y[i] || 0); } return false; }
async function checkUpdate() {
  if (!S.st || !S.st.settings.update_check || !S.conn) return;
  let rel = null;
  try { const c = JSON.parse(sessionStorage.getItem('geulpu.rel') || 'null'); if (c && Date.now() - c.t < 3600e3) rel = c.r; } catch (_) { }
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
  const b = $('#banner');
  if (b.classList.contains('offline')) return;
  if (rel && newer(rel.tag, S.st.app.version)) {
    put(b, h('i', { class: 'dot acc' }), h('span', null, `새 버전이 나왔습니다: ${rel.tag}(지금 v${S.st.app.version}). 새 폴더에 압축을 풀고 실행하면 모델과 결과는 그대로 이어집니다.`),
      h('span', { class: 'grow' }), h('a', { class: 'btn sm', href: rel.url, target: '_blank', rel: 'noopener' }, '다운로드 페이지', I('ext', 's')),
      h('button', { class: 'icon-btn', 'aria-label': '알림 닫기', onclick: () => { b.hidden = true; } }, I('x', 's')));
    b.hidden = false;
  } else b.hidden = true;
}

// ---------- 채팅 ----------
const R1_BOS = '<｜begin▁of▁sentence｜>', R1_USER = '<｜User｜>', R1_ASSIST = '<｜Assistant｜>', R1_EOS = '<｜end▁of▁sentence｜>';
const THINK_END_ID = 151649;   // R1-Distill-Qwen 의 </think> — GGUF 토큰 종류 4(사용자 정의). 서버는 글로 내지 않는다.
const OPT = Object.assign({ temp: 0, max: 4096, system: '', think: true }, load('geulpu.opt', {}));
function saveRooms() { store('geulpu.rooms', S.rooms); store('geulpu.room', S.roomId); }
function curRoom() { return S.rooms.find(r => r.id === S.roomId) || null; }
function runnable(m) { return !!(m && m.shape && m.shape.ok && !m.device_reason); }
function defaultModel() {
  const st = S.st;
  if (st && st.server.state === 'ready' && st.server.model) return st.server.model;
  const r = st ? sortedModels().filter(runnable) : [];
  return r.length ? r[0].id : '';
}
const overlayConvos = () => innerWidth <= 900;
function setConvos(open, remember) {
  $('#convos').classList.toggle('closed', !open);
  $('#show-convos').hidden = open;
  $('#scrim').hidden = !(open && overlayConvos());
  if (remember !== false && !overlayConvos()) store('geulpu.convos', open);
  if (open && overlayConvos()) setTimeout(() => $('#newroom').focus(), 0);
}
$('#scrim').addEventListener('click', () => setConvos(false));
let wasOverlay = overlayConvos();
addEventListener('resize', () => { const o = overlayConvos(); if (o !== wasOverlay) { wasOverlay = o; setConvos(o ? false : load('geulpu.convos', true), false); } });
// 답이 흐르는 동안에도 다른 채팅을 보거나 새 채팅을 열 수 있다 — 답은 제 채팅에 계속 쌓인다
function pickRoom(id) {
  S.rooms = S.rooms.filter(r => r.messages.length || r.id === id);
  S.roomId = id;
  S.editing = null;
  saveRooms(); renderRooms(); renderMsgs(); renderChatTop(true);
  if (overlayConvos()) setConvos(false);
}
function newRoom() {
  const cur = curRoom();
  if (cur && !cur.messages.length) { if (overlayConvos()) setConvos(false); $('#input').focus(); return; }
  S.rooms = S.rooms.filter(r => r.messages.length);
  const r = { id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6), title: '새 채팅', model: (cur && cur.model) || defaultModel(), messages: [], created: Date.now(), updated: Date.now() };
  S.rooms.unshift(r);
  S.roomId = r.id;
  S.editing = null;
  saveRooms();
  renderRooms();
  renderMsgs();
  renderChatTop(true);
  if (overlayConvos()) setConvos(false);
  $('#input').focus();
}
put($('#newroom'), I('plus', 's'), h('span', null, '새 채팅'));
$('#newroom').addEventListener('click', newRoom);
$('#hide-convos').innerHTML = svg('panel', 's');
$('#show-convos').innerHTML = svg('panel', 's');
$('#hide-convos').addEventListener('click', () => setConvos(false));
$('#show-convos').addEventListener('click', () => setConvos(true));
function dayGroup(t) {
  const d0 = new Date(); d0.setHours(0, 0, 0, 0);
  const day = 864e5;
  if (t >= d0.getTime()) return '오늘';
  if (t >= d0.getTime() - day) return '어제';
  if (t >= d0.getTime() - 7 * day) return '지난 7일';
  return '이전';
}
function renderRooms() {
  const list = $('#roomlist');
  const shown = S.rooms.filter(r => r.messages.length).sort((a, b) => (b.updated || b.created) - (a.updated || a.created));
  const out = [];
  let g = null;
  for (const r of shown) {
    const gg = dayGroup(r.updated || r.created);
    if (gg !== g) { g = gg; out.push(h('div', { class: 'room-group eyebrow' }, gg)); }
    const busy = S.streaming && S.streaming.roomId === r.id;
    out.push(h('div', { class: 'room' + (r.id === S.roomId ? ' active' : '') },
      h('button', { class: 'pick', 'data-tip': r.title.length > 18 ? r.title : null, 'aria-current': r.id === S.roomId ? 'true' : null, onclick: () => pickRoom(r.id) },
        busy ? h('i', { class: 'dot busy', 'aria-hidden': 'true' }) : null, h('span', null, r.title), busy ? h('span', { class: 'sr' }, ' — 답을 쓰는 중') : null),
      h('button', {
        class: 'icon-btn more', 'aria-label': `'${r.title}' 메뉴`, 'aria-haspopup': 'menu', 'aria-expanded': 'false',
        onclick: ev => menu(ev.currentTarget, '채팅 메뉴', [
          { icon: 'edit', label: '이름 바꾸기', run: () => renameRoom(r) },
          { icon: 'trash', label: '삭제', danger: true, disabled: busy, sub: busy ? '답이 끝난 뒤 삭제할 수 있습니다' : null, run: () => delRoom(r.id) }], 'right'),
      }, I('dots', 's'))));
  }
  if (!shown.length) out.push(h('div', { class: 'room-group eyebrow' }, '아직 채팅이 없습니다'));
  put(list, out);
}
function renameRoom(r) {
  const inp = h('input', { type: 'text', value: r.title, class: 'w100', 'aria-label': '채팅 이름' });
  const ok = () => { const v = inp.value.trim(); if (v) { r.title = v; saveRooms(); renderRooms(); } closeModal(); };
  inp.addEventListener('keydown', e => { if (e.key === 'Enter') ok(); });
  modal(h('div', { class: 'col g16' }, h('h2', null, '채팅 이름 바꾸기'), inp), [h('button', { class: 'btn ghost', onclick: () => closeModal() }, '취소'), h('button', { class: 'btn primary', onclick: ok }, '저장')], false, 'input');
}
async function delRoom(id) {
  if (S.streaming && S.streaming.roomId === id) return;
  const r = S.rooms.find(x => x.id === id);
  if (r && r.messages.length && !(await confirmBox('채팅 삭제', h('p', { class: 'muted m0' }, `'${r.title}' 채팅을 삭제할까요? 채팅은 이 브라우저에만 저장되어 있어 되돌릴 수 없습니다.`), '삭제', 'danger'))) return;
  S.rooms = S.rooms.filter(x => x.id !== id);
  if (S.roomId === id) { S.roomId = null; newRoom(); }
  saveRooms(); renderRooms(); renderMsgs(); renderChatTop(true);
}

// 입력창: 보낼 수 없는 상태면 막고 이유를 자리 글로
function updateComposer() {
  const inp = $('#input');
  const hs = helloState(S.st);
  let why = '';
  if (!S.conn) why = 'GeulPU.exe와 연결이 끊겼습니다';
  else if (hs === 'checking' || hs === 'loading') why = '하드웨어 확인이 끝나면 입력할 수 있습니다';
  else if (hs === 'nogpu') why = '쓸 수 있는 GPU가 없어 채팅할 수 없습니다';
  else if (hs === 'nomodel' || hs === 'unsupported') why = '모델을 다운로드하면 채팅을 시작할 수 있습니다';
  inp.disabled = !!why;
  inp.placeholder = why || '메시지 입력';
  updateSend();
}
const HINT = 'Enter 보내기 · Shift+Enter 줄바꿈';
// 보내기 단추 · 도움말 — 이 채팅이 답을 쓰는 중이면 중지, 다른 채팅이 쓰는 중이면 끝날 때까지 기다림
function updateSend() {
  const b = $('#sendbtn'), inp = $('#input'), hint = $('#composer-hint');
  const here = streamingHere(), other = !!S.streaming && !here;
  b.classList.toggle('stop', here);
  const icon = here ? 'stop' : 'up';
  if (b.dataset.icon !== icon) { b.innerHTML = svg(icon, 's'); b.dataset.icon = icon; }
  b.setAttribute('aria-label', here ? '중지' : '보내기');
  const bench = !here && !other && benchBusy();   // 벤치마크 중에도 미리 써 둘 수는 있다
  b.dataset.tip = here ? '중지(Esc)' : other ? '다른 채팅의 답이 끝나면 보낼 수 있습니다' : bench ? '벤치마크가 끝나면 보낼 수 있습니다' : '보내기(Enter)';
  b.dataset.tipPos = 'top';
  b.disabled = here ? false : (other || bench || !inp.value.trim() || !S.conn || inp.disabled);
  hint.textContent = here ? '답이 끝나면 보낼 수 있습니다 · Esc 중지' : other ? '다른 채팅의 답이 끝나면 보낼 수 있습니다' : bench ? '벤치마크가 끝나면 보낼 수 있습니다' : HINT;
  hint.hidden = inp.disabled || (!S.streaming && !bench && !!load('geulpu.hinted', false));
}
function renderChatTop(force) {
  const room = curRoom();
  const st = S.st;
  if (!st) return;
  if (room && (!room.model || !st.models.some(m => m.id === room.model)) && st.models.length) { room.model = defaultModel(); saveRooms(); }
  const m = room && modelOf(room.model);
  const sv = st.server, d = st.device;
  if (!changed('chattop', [room && room.model, m && [displayName(m), quantOf(m), m.device_reason, runnable(m)], sv.state, sv.model, sv.layer, st.models.length, d.checked, d.layer, S.conn, !!S.streaming, benchBusy()]) && !force) return;
  put($('#model-pill'), h('span', { class: 'name' }, m ? displayName(m) : (st.models.length ? '모델 선택' : '모델 없음')), m && quantOf(m) ? h('span', { class: 'q' }, quantOf(m)) : null, I('chevD', 's'));
  const ms = $('#model-state');
  delete ms.dataset.tip;
  if (!S.conn) put(ms, h('i', { class: 'dot err' }), h('span', null, '연결 끊김'));
  else if (!d.checked) put(ms, h('i', { class: 'dot busy' }), h('span', null, '하드웨어 확인 중'));
  else if (benchBusy() && !(sv.model === (m && m.id) && sv.state === 'ready')) put(ms, h('i', { class: 'dot busy' }), h('span', null, '벤치마크 실행 중 · 끝나면 보낼 수 있습니다'));
  else if (!d.layer) put(ms, h('i', { class: 'dot err' }), h('span', null, '쓸 수 있는 GPU 없음'));
  else if (!m) put(ms);
  else if (sv.model === m.id && sv.state === 'ready') put(ms, h('i', { class: 'dot ok' }), h('span', null, `준비됨 · ${LAYER[sv.layer] || ''}`));
  else if (sv.model === m.id && sv.state === 'starting') put(ms, h('i', { class: 'dot busy' }), h('span', null, '불러오는 중'));
  else if (!runnable(m)) put(ms, h('i', { class: 'dot err' }), h('span', null, '이 PC에서 실행할 수 없음'));
  else if (sv.state === 'failed') put(ms, h('i', { class: 'dot err' }), h('span', null, '불러오기 실패 · 보내면 다시 시도합니다'));
  else if (sv.state === 'ready' || sv.state === 'starting') { put(ms, h('i', { class: 'dot' }), h('span', null, '보내면 이 모델로 바뀝니다')); ms.dataset.tip = `지금 불러온 모델: ${labelById(sv.model)}`; ms.dataset.tipPos = 'bottom'; }
  else put(ms, h('i', { class: 'dot' }), h('span', null, '보내면 불러옵니다'));
  updateComposer();
}
$('#model-pill').addEventListener('click', e => {
  const st = S.st;
  if (!st) return;
  if (POP) { closePop(); return; }
  const room = curRoom();
  const sv = st.server;
  const locked = streamingHere();
  const groups = [];
  for (const m of sortedModels()) {
    const name = displayName(m);
    let g = groups[groups.length - 1];
    if (!g || g.name !== name) { g = { name, items: [] }; groups.push(g); }
    g.items.push(m);
  }
  const body = [];
  if (locked) body.push(h('div', { class: 'pad small muted' }, '답이 끝나면 모델을 바꿀 수 있습니다.'));
  // 모델마다 머리(이름 · 종류) 아래에 양자화 줄 — 이 PC 에서 도는 모델이 먼저
  groups.sort((a, b) => (a.items.some(runnable) ? 0 : 1) - (b.items.some(runnable) ? 0 : 1));
  for (const g of groups) {
    const g0 = g.items[0];
    body.push(h('div', { role: 'group', 'aria-label': g.name },
      h('div', { class: 'mhd', 'aria-hidden': 'true' }, h('span', { class: 'nm' }, g.name), h('span', { class: 'kd' }, kindOf(g0))),
      g.items.map(m => {
        const ok = runnable(m);
        const sel = room && room.model === m.id;
        const loaded = sv.model === m.id && sv.state === 'ready';
        const reason = m.device_reason || (m.shape && m.shape.reason) || '';
        const label = `${g.name} ${quantOf(m)}, ${fmtBytes(m.size)}${loaded ? ', 불러옴' : ''}${ok ? '' : ', 이 PC에서 실행할 수 없음: ' + reason}`;
        return h('button', {
          class: 'opt q' + (sel ? ' sel' : ''), role: 'menuitemradio', 'aria-checked': sel ? 'true' : 'false', 'aria-label': label, disabled: (ok && !locked) ? null : true,
          onclick: () => { closePop(); if (!room) return; room.model = m.id; saveRooms(); renderChatTop(true); renderMsgs(); $('#input').focus(); },
        }, h('span', { class: 'qlab' }, quantOf(m)), h('span', { class: 'sz' }, fmtBytes(m.size)),
          ok ? null : h('span', { class: 'why' }, m.device_reason ? '이 GPU 미지원' : '지원하지 않는 파일'),
          h('span', { class: 'grow' }), loaded ? h('span', { class: 'tag' }, h('i', { class: 'dot ok' }), '불러옴') : null, sel ? I('check', 's') : null);
      })));
  }
  if (!st.models.length) body.push(h('div', { class: 'pad muted' }, '아직 모델이 없습니다.'));
  body.push(h('div', { class: 'sep', role: 'separator' }), h('button', { class: 'opt', role: 'menuitem', onclick: () => { closePop(); show('models'); } }, I('download', 's'), h('span', { class: 'main' }, h('div', { class: 't' }, '모델 다운로드 · 추가'))));
  if (sv.state === 'ready' || sv.state === 'starting') body.push(h('button', { class: 'opt', role: 'menuitem', disabled: S.streaming ? true : null, onclick: () => { closePop(); unloadModel(); } }, I('eject', 's'), h('span', { class: 'main' }, h('div', { class: 't' }, '불러온 모델 내리기'), h('div', { class: 's' }, 'GPU 메모리를 비웁니다'))));
  openPop(e.currentTarget, h('div', { role: 'menu', 'aria-label': '모델 선택' }, body));
});
$('#optbtn').innerHTML = svg('sliders');
$('#optbtn').addEventListener('click', e => {
  if (POP) { closePop(); return; }
  const temp = h('input', { type: 'number', min: '0', max: '2', step: '0.1', value: OPT.temp, 'aria-label': '온도' });
  const max = h('input', { type: 'number', min: '16', max: '32768', step: '256', value: OPT.max, 'aria-label': '최대 답변 길이(토큰)' });
  const sys = h('textarea', { rows: '4', placeholder: '비워 두면 모델 기본값', 'aria-label': '시스템 프롬프트', class: 'w100' }, OPT.system || '');
  const think = h('input', { type: 'checkbox', 'aria-label': '생각 과정 쓰기(Qwen3)', onchange: () => { OPT.think = think.checked; store('geulpu.opt', OPT); } });
  think.checked = OPT.think !== false;
  // 쓰는 동안은 그대로 두고, 칸을 떠날 때(또는 Enter) 범위에 맞춰 칸에도 다시 적는다(온도 0~2 · 길이 16~32768)
  const clampNum = (v, lo, hi, d) => { const n = Number(v); return Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : d; };
  const save = () => { OPT.temp = clampNum(parseFloat(temp.value), 0, 2, 0); OPT.max = Math.round(clampNum(parseInt(max.value, 10), 16, 32768, 4096)); OPT.system = sys.value; store('geulpu.opt', OPT); };
  const settle = () => { save(); temp.value = OPT.temp; max.value = OPT.max; };
  [temp, max, sys].forEach(x => x.addEventListener('input', save));
  [temp, max].forEach(x => { x.addEventListener('change', settle); x.addEventListener('keydown', ev => { if (ev.key === 'Enter') settle(); }); });
  openPop(e.currentTarget, h('div', { class: 'pad w360', role: 'dialog', 'aria-label': '생성 설정' },
    h('div', { class: 'eyebrow' }, '생성 설정 · 이 브라우저에 저장'),
    h('div', { class: 'lrow' }, h('div', null, h('div', { class: 'ink' }, '온도'), h('div', { class: 'small muted' }, '0이면 같은 질문에 늘 같은 답')), temp),
    h('div', { class: 'lrow' }, h('div', null, h('div', { class: 'ink' }, '최대 답변 길이'), h('div', { class: 'small muted' }, '토큰 · 추론 모델은 생각 과정도 포함')), max),
    h('div', { class: 'lrow' }, h('div', null, h('div', { class: 'ink' }, '생각 과정 쓰기'), h('div', { class: 'small muted' }, 'Qwen3 · 끄면 생각 없이 바로 답합니다')), h('label', { class: 'switch' }, think, h('i'))),
    h('div', { class: 'col' }, h('div', { class: 'ink' }, '시스템 프롬프트'), sys)), 'right');
});

// ---------- 마크다운 · 수식(앱 안에서 — 바깥 라이브러리 없음, 글은 늘 탈출해서 넣는다) ----------
const TEXSYM = {
  times: '×', cdot: '·', div: '÷', pm: '±', mp: '∓', leq: '≤', le: '≤', geq: '≥', ge: '≥', neq: '≠', ne: '≠', approx: '≈', equiv: '≡',
  sim: '∼', simeq: '≃', cong: '≅', propto: '∝', infty: '∞', to: '→', rightarrow: '→', leftarrow: '←', Rightarrow: '⇒', Leftarrow: '⇐',
  leftrightarrow: '↔', Leftrightarrow: '⇔', iff: '⟺', implies: '⟹', mapsto: '↦', ldots: '…', cdots: '⋯', dots: '…', vdots: '⋮',
  sum: '∑', prod: '∏', int: '∫', oint: '∮', partial: '∂', nabla: '∇', forall: '∀', exists: '∃', in: '∈', notin: '∉', ni: '∋',
  subset: '⊂', subseteq: '⊆', supset: '⊃', supseteq: '⊇', cup: '∪', cap: '∩', emptyset: '∅', varnothing: '∅', angle: '∠', circ: '∘',
  degree: '°', perp: '⊥', parallel: '∥', mid: '∣', nmid: '∤', lfloor: '⌊', rfloor: '⌋', lceil: '⌈', rceil: '⌉', langle: '⟨', rangle: '⟩',
  neg: '¬', lnot: '¬', land: '∧', lor: '∨', wedge: '∧', vee: '∨', oplus: '⊕', otimes: '⊗', star: '⋆', ast: '∗', bullet: '•', prime: '′',
  hbar: 'ℏ', ell: 'ℓ', aleph: 'ℵ', therefore: '∴', because: '∵', checkmark: '✓',
  alpha: 'α', beta: 'β', gamma: 'γ', delta: 'δ', epsilon: 'ϵ', varepsilon: 'ε', zeta: 'ζ', eta: 'η', theta: 'θ', vartheta: 'ϑ', iota: 'ι',
  kappa: 'κ', lambda: 'λ', mu: 'μ', nu: 'ν', xi: 'ξ', pi: 'π', varpi: 'ϖ', rho: 'ρ', varrho: 'ϱ', sigma: 'σ', varsigma: 'ς', tau: 'τ',
  upsilon: 'υ', phi: 'ϕ', varphi: 'φ', chi: 'χ', psi: 'ψ', omega: 'ω', Gamma: 'Γ', Delta: 'Δ', Theta: 'Θ', Lambda: 'Λ', Xi: 'Ξ', Pi: 'Π',
  Sigma: 'Σ', Upsilon: 'Υ', Phi: 'Φ', Psi: 'Ψ', Omega: 'Ω',
  quad: '\u2003', qquad: '\u2003\u2003', ',': '\u2009', ';': '\u2005', ':': '\u2005', '>': '\u2005', '!': '', ' ': ' ',
  '{': '{', '}': '}', '%': '%', '$': '$', '#': '#', '&': '&amp;', '_': '_', '|': '‖',
};
const TEXFN = new Set(['sin', 'cos', 'tan', 'cot', 'sec', 'csc', 'arcsin', 'arccos', 'arctan', 'sinh', 'cosh', 'tanh', 'log', 'ln', 'lg', 'exp', 'lim',
  'max', 'min', 'sup', 'inf', 'det', 'gcd', 'lcm', 'deg', 'dim', 'ker', 'arg', 'Pr', 'mod', 'bmod']);
function tex(src) {
  const s = String(src);
  let i = 0;
  const group = () => {   // '{' 다음부터 짝 '}' 까지
    let depth = 1;
    const a = i;
    while (i < s.length && depth) { if (s[i] === '\\') { i += 2; continue; } if (s[i] === '{') depth++; else if (s[i] === '}') depth--; i++; }
    return s.slice(a, depth ? i : i - 1);
  };
  const raw = () => { while (s[i] === ' ') i++; if (s[i] === '{') { i++; return group(); } return s[i++] || ''; };
  const opt = () => { if (s[i] !== '[') return null; const j = s.indexOf(']', i); if (j < 0) return null; const v = s.slice(i + 1, j); i = j + 1; return v; };
  const arg = () => {
    while (s[i] === ' ') i++;
    if (s[i] === '{') { i++; return tex(group()); }
    if (s[i] === '\\') { const m = /^\\([A-Za-z]+|.)/.exec(s.slice(i)); if (!m) { i++; return ''; } i += m[0].length; return cmd(m[1]); }
    return i < s.length ? chr(s[i++]) : '';
  };
  const chr = c => (/[A-Za-z]/.test(c) ? `<i>${c}</i>` : c === '&' ? ' ' : c === '~' ? '\u00a0' : esc(c));
  function cmd(n) {
    switch (n) {
      case 'frac': case 'dfrac': case 'tfrac': case 'cfrac': { const a = arg(), b = arg(); return `<span class="frac"><span>${a}</span><span>${b}</span></span>`; }
      case 'binom': case 'dbinom': case 'tbinom': { const a = arg(), b = arg(); return `(<span class="frac nb"><span>${a}</span><span>${b}</span></span>)`; }
      case 'sqrt': { const k = opt(); const a = arg(); return (k ? `<sup>${esc(k)}</sup>` : '') + `√<span class="ov">${a}</span>`; }
      case 'boxed': case 'fbox': case 'framebox': return `<span class="boxed">${arg()}</span>`;
      case 'text': case 'textrm': case 'textnormal': case 'mathrm': case 'operatorname': case 'textit': case 'mbox': case 'textsf': case 'texttt':
        return `<span class="tx">${esc(raw())}</span>`;
      case 'textbf': case 'mathbf': case 'boldsymbol': case 'bm': return `<b>${arg()}</b>`;
      case 'mathit': case 'emph': return arg();
      case 'mathbb': { const a = raw(); return esc({ R: 'ℝ', N: 'ℕ', Z: 'ℤ', Q: 'ℚ', C: 'ℂ', P: 'ℙ' }[a] || a); }
      case 'mathcal': case 'mathscr': case 'mathfrak': case 'mathsf': case 'mathtt': return arg();
      case 'overline': case 'bar': return `<span class="ov">${arg()}</span>`;
      case 'hat': case 'widehat': return arg() + '\u0302';
      case 'vec': return arg() + '\u20d7';
      case 'dot': return arg() + '\u0307';
      case 'ddot': return arg() + '\u0308';
      case 'tilde': case 'widetilde': return arg() + '\u0303';
      case 'pmod': return `\u2005(<span class="fn">mod</span> ${arg()})`;
      case 'not': return arg() + '\u0338';
      case 'left': case 'right': case 'big': case 'Big': case 'bigg': case 'Bigg': case 'bigl': case 'bigr': case 'Bigl': case 'Bigr':
      case 'displaystyle': case 'textstyle': case 'scriptstyle': case 'limits': case 'nolimits': case 'nonumber': case 'notag': return '';
      case 'begin': case 'end': raw(); if (s[i] === '{') { i++; group(); } return '';
      case '\\': return '<br>';
      default:
        if (TEXFN.has(n)) return `<span class="fn">${n === 'bmod' ? 'mod' : n}</span>`;
        if (n in TEXSYM) return TEXSYM[n];
        return `<span class="tx">${esc(n)}</span>`;
    }
  }
  let out = '';
  while (i < s.length) {
    const c = s[i];
    if (c === '\\') { const m = /^\\([A-Za-z]+|.)/.exec(s.slice(i)); if (!m) { i++; continue; } i += m[0].length; out += cmd(m[1]); continue; }
    if (c === '^') { i++; out += `<sup>${arg()}</sup>`; continue; }
    if (c === '_') { i++; out += `<sub>${arg()}</sub>`; continue; }
    if (c === '{') { i++; out += tex(group()); continue; }
    if (c === '}') { i++; continue; }
    out += chr(c);
    i++;
  }
  return out;
}
const mathInline = t => `<span class="math">${tex(t)}</span>`;
const mathBlock = t => `<div class="math block">${tex(t)}</div>`;
function codeBlock(code, lang) {
  return `<div class="codeblk"><div class="ch"><span>${esc(lang || '코드')}</span><button class="cp" type="button">${svg('copy', 's')}<span>복사</span></button></div><pre><code>${esc(code)}</code></pre></div>`;
}
function inline(src) {
  const slots = [];
  const hold = html => { slots.push(html); return '\u0000' + (slots.length - 1) + '\u0000'; };
  let s = String(src);
  s = s.replace(/`([^`\n]+)`/g, (_, c) => hold('<code class="inl">' + esc(c) + '</code>'));
  s = s.replace(/\\\((.+?)\\\)/g, (_, t) => hold(mathInline(t)));
  s = s.replace(/\\\[(.+?)\\\]/g, (_, t) => hold(mathInline(t)));
  s = s.replace(/\$\$(.+?)\$\$/g, (_, t) => hold(mathInline(t)));
  s = s.replace(/(^|[^\\$\w])\$([^\s$](?:[^$\n]*?[^\s$])?)\$(?![\w$])/g, (all, pre, t) =>
    (/[\\^_={}]/.test(t) || /^[A-Za-z]{1,2}$/.test(t) || (/\d/.test(t) && /[A-Za-z+\-*/<>]/.test(t))) ? pre + hold(mathInline(t)) : all);
  s = s.replace(/\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)/g, (_, t, u) => hold(`<a href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(t)}</a>`));
  s = esc(s);
  s = s.replace(/\*\*([^*\n]+)\*\*/g, '<b>$1</b>').replace(/__([^_\n]+)__/g, '<b>$1</b>')
    .replace(/(^|[\s(])\*([^*\n]+)\*(?=[\s).,!?:;]|$)/g, '$1<i>$2</i>')
    .replace(/~~([^~\n]+)~~/g, '<s>$1</s>');
  return s.replace(/\u0000(\d+)\u0000/g, (_, n) => slots[+n]);
}
const inlineLines = t => t.split('\n').map(inline).join('<br>');
// 목록 항목 안에 여러 줄 수식(\[ … \]) · 코드 블록이 있으면 블록으로 그린다
const itemHtml = t => (/(^|\n)\s*(\\\[|\$\$|```|~~~)/.test(t) ? md(t) : inlineLines(t));
const LIST_RE = /^(\s*)([-*+]|(\d+)[.)])\s+(.*)$/;
function parseList(lines, i) {
  const items = [];
  while (i < lines.length) {
    const ln = lines[i];
    const m = LIST_RE.exec(ln);
    if (m) { items.push({ ind: m[1].replace(/\t/g, '    ').length, ord: !!m[3], num: m[3] ? parseInt(m[3], 10) : 0, text: m[4] }); i++; continue; }
    if (!ln.trim()) {
      let j = i + 1;
      while (j < lines.length && !lines[j].trim()) j++;
      if (j < lines.length && (LIST_RE.test(lines[j]) || /^\s{2,}\S/.test(lines[j]))) { i = j; continue; }
      break;
    }
    if (items.length && (/^\s{2,}\S/.test(ln) || !/^\s*(#|>|```|~~~|\||\\\[|\$\$)/.test(ln))) { items[items.length - 1].text += '\n' + ln.trim(); i++; continue; }
    break;
  }
  return { html: buildList(items, 0, items.length), next: i };
}
function buildList(items, a, b) {
  let html = '';
  let k = a;
  while (k < b) {
    const base = items[k].ind, ord = items[k].ord;
    html += ord ? (items[k].num > 1 ? `<ol start="${items[k].num}">` : '<ol>') : '<ul>';
    while (k < b && items[k].ind < base + 2 && items[k].ord === ord) {
      let c = k + 1;
      while (c < b && items[c].ind >= base + 2) c++;
      html += '<li>' + itemHtml(items[k].text) + (c > k + 1 ? buildList(items, k + 1, c) : '') + '</li>';
      k = c;
    }
    html += ord ? '</ol>' : '</ul>';
  }
  return html;
}
function md(text) {
  const lines = String(text || '').replace(/\r\n?/g, '\n').split('\n');
  let out = '';
  const para = [];
  const flush = () => { if (para.length) { out += '<p>' + para.map(inline).join('<br>') + '</p>'; para.length = 0; } };
  let i = 0;
  while (i < lines.length) {
    const ln = lines[i];
    let m;
    if ((m = /^\s*(```+|~~~+)\s*([\w#+.-]*)\s*$/.exec(ln))) {
      flush();
      const fence = m[1], buf = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith(fence)) { buf.push(lines[i]); i++; }
      i++;
      out += codeBlock(buf.join('\n'), m[2]);
      continue;
    }
    if ((m = /^\s*(\\\[|\$\$)(.*)$/.exec(ln))) {
      flush();
      const close = m[1] === '\\[' ? '\\]' : '$$';
      const first = m[2];
      const j0 = first.indexOf(close);
      if (j0 >= 0) {
        out += mathBlock(first.slice(0, j0));
        const rest = first.slice(j0 + close.length).trim();
        if (rest) para.push(rest);
        i++;
        continue;
      }
      const buf = [first];
      i++;
      while (i < lines.length && lines[i].indexOf(close) < 0) { buf.push(lines[i]); i++; }
      if (i < lines.length) { buf.push(lines[i].slice(0, lines[i].indexOf(close))); i++; }
      out += mathBlock(buf.join(' '));
      continue;
    }
    if (!ln.trim()) { flush(); i++; continue; }
    if ((m = /^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$/.exec(ln))) { flush(); out += `<h4>${inline(m[2])}</h4>`; i++; continue; }
    if (/^\s{0,3}([-*_])(\s*\1){2,}\s*$/.test(ln)) { flush(); out += '<hr>'; i++; continue; }
    if (/^\s{0,3}>/.test(ln)) {
      flush();
      const buf = [];
      while (i < lines.length && /^\s{0,3}>/.test(lines[i])) { buf.push(lines[i].replace(/^\s{0,3}>\s?/, '')); i++; }
      out += '<blockquote>' + md(buf.join('\n')) + '</blockquote>';
      continue;
    }
    if (ln.includes('|') && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(lines[i + 1])) {
      flush();
      const cells = s => s.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(x => x.trim());
      const head = cells(ln);
      const al = cells(lines[i + 1]).map(x => (x.startsWith(':') && x.endsWith(':') ? 'center' : x.endsWith(':') ? 'right' : ''));
      // 짧은 칸(18자 이하)은 한 줄로 — 좁으면 표가 가로로 스크롤한다(낱말 · 음절 단위로 부서지지 않게)
      const at = (k, t) => (al[k] ? ` style="text-align:${al[k]}"` : '') + (String(t || '').length <= 18 ? ' class="nw"' : '');
      i += 2;
      const rows = [];
      while (i < lines.length && lines[i].includes('|') && lines[i].trim()) { rows.push(cells(lines[i])); i++; }
      out += '<div class="tbl"><table><thead><tr>' + head.map((c, k) => `<th${at(k, c)}>${inline(c)}</th>`).join('') + '</tr></thead><tbody>'
        + rows.map(r => '<tr>' + head.map((_, k) => `<td${at(k, r[k])}>${inline(r[k] || '')}</td>`).join('') + '</tr>').join('') + '</tbody></table></div>';
      continue;
    }
    if (LIST_RE.test(ln)) { flush(); const r = parseList(lines, i); out += r.html; i = r.next; continue; }
    para.push(ln);
    i++;
  }
  flush();
  return out;
}
// 흐르는 중: 아직 닫히지 않은 수식(\( \[ $$)은 닫힐 때까지 그리지 않는다(날 TeX 가 잠깐 보이지 않게)
function holdOpenMath(t) {
  const last = (open, close) => { const a = t.lastIndexOf(open); return a >= 0 && t.indexOf(close, a + open.length) < 0 ? a : -1; };
  let cut = -1;
  for (const [o, c] of [['\\(', '\\)'], ['\\[', '\\]']]) { const a = last(o, c); if (a >= 0 && (cut < 0 || a < cut)) cut = a; }
  const dd = t.split('$$').length - 1;
  if (dd % 2 === 1) { const a = t.lastIndexOf('$$'); if (cut < 0 || a < cut) cut = a; }
  return cut >= 0 ? t.slice(0, cut) : t;
}
$('#msgs').addEventListener('click', async e => {
  const b = e.target.closest('.codeblk .cp');
  if (!b) return;
  if (await copyText(b.closest('.codeblk').querySelector('code').textContent)) {
    b.lastChild.textContent = '복사함';
    setTimeout(() => { b.lastChild.textContent = '복사'; }, 1200);
  }
});

// R1 의 생각 · 답 나누기. 서버는 <think> · </think>(토큰 종류 4)를 글로 내지 않아 "\n</think>\n\n" 자리에 줄바꿈 셋이 남는다 —
// 교차검증 응답 64개를 토큰 번호로 풀어 보니 </think> 가 있는 40개 모두 첫 "\n\n\n" 이 바로 그 경계였다(다른 곳에 먼저 나온 것 0).
// Qwen3 — 화면이 geulpu.special 로 <think> · </think> 를 글로 받으므로 토큰 경계(</think>, 151668) 그대로 나눈다. 생각 끔이면
// 답이 <think> 없이 바로 온다(채팅 틀이 빈 생각을 프롬프트에 넣는다).
function splitThinkQwen3(t0, done) {
  if (!t0.startsWith('<think>')) return { think: null, answer: t0 };
  const t = t0.slice(7);
  const k = t.indexOf('</think>');
  if (k >= 0) return { think: t.slice(0, k).trim() || null, answer: t.slice(k + 8).replace(/^\s+/, '') };
  if (!done) return { think: t.trim(), answer: '', open: true };
  return { think: t.trim(), answer: '', unfinished: true };
}
function splitThink(m, done) {
  const t0 = String(m.content || '');
  if (m.template === 'qwen3') return splitThinkQwen3(t0, done);
  if (m.template !== 'deepseek-r1') return { think: null, answer: t0 };
  let t = t0.startsWith('<think>') ? t0.slice(7) : t0;
  let k = t.indexOf('</think>');
  if (k >= 0) return { think: t.slice(0, k).trim(), answer: t.slice(k + 8).replace(/^\s+/, '') };
  k = t.indexOf('\n\n\n');
  if (k >= 0) return { think: t.slice(0, k).trim(), answer: t.slice(k).replace(/^\s+/, '') };
  if (!done) return { think: t.trim(), answer: '', open: true };
  if (m.thinkEnded) return { think: null, answer: t.replace(/^\s+/, '') };
  return { think: t.trim(), answer: '', unfinished: true };
}
// 같은 이름에서 더 작은(설치되고 실행되는) 양자화
function smallerSibling(m) {
  if (!m || !S.st) return null;
  const name = displayName(m);
  return sortedModels().filter(x => x.id !== m.id && displayName(x) === name && x.size < m.size && runnable(x)).sort((a, b) => b.size - a.size)[0] || null;
}
// 채팅 오류를 쉬운 말로 — [제목, 도움말, 단추들]
function humanError(msg, room) {
  const s = String(msg || '');
  const m = room && modelOf(room.model);
  if (/out of memory|OUT_OF_MEMORY|메모리가 (모자|부족)|ERROR_OUT_OF_DEVICE_MEMORY/i.test(s)) {
    const sib = smallerSibling(m);
    if (sib) return ['그래픽 메모리가 부족합니다', `같은 모델의 더 작은 파일(${quantOf(sib)} · ${fmtBytes(sib.size)})로 바꾸면 실행될 수 있습니다.`,
      [h('button', { class: 'btn sm', onclick: () => { room.model = sib.id; saveRooms(); renderChatTop(true); retryLast(); } }, I('refresh', 's'), `${quantOf(sib)} 파일로 다시 시도`)]];
    return ['그래픽 메모리가 부족합니다', '설정에서 동시 처리 수나 채팅마다 문맥 길이를 줄이거나, 더 작은 모델을 쓰세요.',
      [h('button', { class: 'btn sm', onclick: () => show('settings') }, I('gear', 's'), '설정 열기'), h('button', { class: 'btn sm ghost', onclick: () => $('#model-pill').click() }, I('box', 's'), '모델 바꾸기')]];
  }
  const retry = h('button', { class: 'btn sm needs-conn', onclick: () => retryLast() }, I('refresh', 's'), '다시 시도');
  const swap = h('button', { class: 'btn sm ghost', onclick: () => $('#model-pill').click() }, I('box', 's'), '모델 바꾸기');
  if (/Failed to fetch|NetworkError|연결이 끊/.test(s)) return ['GeulPU.exe와 연결이 끊겼습니다', 'GeulPU.exe가 실행 중인지 확인한 뒤 다시 시도하세요.', [retry]];
  if (/다른 (일이 돌고|작업이 실행 중)/.test(s)) return ['다른 작업이 실행 중입니다', '벤치마크가 끝나거나 중지된 뒤 다시 시도하세요.', [retry, h('button', { class: 'btn sm ghost', onclick: () => show('bench') }, I('gauge', 's'), '벤치마크 보기')]];
  if (/모델을 불러오지|추론 서버|서버/.test(s)) return ['모델을 불러오지 못했습니다', '자세히를 열어 원인을 확인하세요. 다른 모델로 바꾸거나 다시 시도할 수 있습니다.', [retry, swap]];
  if (/HTTP 503/.test(s)) return ['모델이 아직 준비되지 않았습니다', '잠시 뒤 다시 시도하세요.', [retry]];
  return ['답을 받지 못했습니다', '다시 시도하거나 다른 모델로 바꿔 보세요.', [retry, swap]];
}
// 벤치마크 실패 까닭 — 아는 꼴이면 쉬운 말로(원문은 자세히에)
function humanJob(reason) {
  const s = String(reason || '');
  if (/out of memory|OUT_OF_MEMORY|ERROR_OUT_OF_DEVICE_MEMORY|들어가지 않습니다/i.test(s)) return ['그래픽 메모리가 부족합니다', '더 작은 모델로 측정하거나 다른 프로그램의 GPU 사용을 줄여 보세요.'];
  if (/DEVICE_LOST|장치를 잃/.test(s)) return ['GPU 드라이버가 작업을 멈췄습니다', '그래픽 드라이버를 최신으로 업데이트한 뒤 다시 실행해 보세요.'];
  if (/중지/.test(s)) return ['중지했습니다', ''];
  return ['측정을 끝내지 못했습니다', '자세히를 열어 원인을 확인하세요.'];
}
// live: 새로 생긴 오류만 화면 읽기 프로그램에 알린다(다시 그릴 때마다 지난 오류를 또 읽지 않게)
function errorCard(title, desc, actions, raw, live) {
  return h('div', { class: 'ecard', role: live ? 'alert' : null },
    h('div', { class: 't' }, I('alert', 's'), h('span', null, title)), desc ? h('div', { class: 'd' }, desc) : null,
    actions && actions.length ? h('div', { class: 'row' }, actions) : null,
    raw ? h('details', { class: 'fold' }, h('summary', null, I('chevR', 's'), '자세히'), h('pre', { class: 'log sans' }, raw)) : null);
}
function addCaret(root) {
  let last = root;
  for (;;) {
    const c = last.lastElementChild;
    if (!c) break;
    if (/^(P|LI|UL|OL|H4|BLOCKQUOTE)$/.test(c.tagName)) { last = c; continue; }
    if (c.classList.contains('codeblk')) { last = c.querySelector('code'); }
    break;
  }
  last.append(h('span', { class: 'caret', 'aria-hidden': 'true' }));
}
const KERNEL_NOTE = '처음 한 번은 이 GPU에 맞는 커널을 만들고 가장 빠른 실행 방식을 측정합니다(보통 수십 초~2분). 다음부터는 더 빨리 준비됩니다.';
const FRESH = new WeakSet();   // 방금 생긴 오류(한 번만 알린다)
function msgEl(m, room, opts) {
  opts = opts || {};
  if (m.role === 'user') {
    const k = room.messages.indexOf(m);
    if (S.editing && S.editing.roomId === room.id && S.editing.k === k) return editBox(m, room, k);
    return h('div', { class: 'msg user' },
      !S.streaming ? h('button', { class: 'icon-btn edit', 'data-tip': '수정', 'data-tip-pos': 'top', 'aria-label': '이 메시지 수정', onclick: () => startEdit(room, k) }, I('edit', 's')) : null,
      h('div', { class: 'bubble' }, m.content));
  }
  if (m.role === 'notice') {
    return h('div', { class: 'msg notice' }, h('div', { class: 'ncard', role: 'status' },
      h('div', { class: 'row' }, h('i', { class: 'dot busy' }), h('span', { class: 't' }, m.text || m.content)),
      h('div', { class: 'bar' }, h('i', { class: 'nbar', style: `width:${m.pct || 0}%` })),
      h('div', { class: 's' }, m.kernel ? KERNEL_NOTE : '모델을 GPU에 올리는 중입니다.')));
  }
  if (m.role === 'note') return h('div', { class: 'msg note' }, I('info', 's'), h('span', null, m.content));
  if (m.role === 'error') {
    const [t, d, acts] = humanError(m.content, room);
    const live = FRESH.has(m);
    FRESH.delete(m);
    return h('div', { class: 'msg error' }, errorCard(t, d, opts.last ? acts : null, m.content, live));
  }
  const mm = modelOf(m.model || room.model);
  const e = h('div', { class: 'msg assistant' },
    opts.who ? h('div', { class: 'who' }, h('span', { class: 'eyebrow' }, mm ? `${displayName(mm)} · ${quantOf(mm)}` : labelById(m.model || room.model))) : null,
    h('div', { class: 'body' }), h('div', { class: 'tools' }));
  e._last = !!opts.last;
  e._vk = opts.vk;   // 이 답이 끝맺는 차례(사용자 메시지 번호) — 버전 넘기기
  if (S.streaming && S.streaming.msg === m) S.streaming.el = e;   // 다시 그려도 흐름은 새 요소에 이어 그린다
  fillMsg(e, m, room, !m.partial);
  return e;
}
// 멈춘 자리에 남은 짝 없는 마크다운 표시(**, `, _)는 지운다
const trimDangling = s => String(s).replace(/(\*\*|\*|__|`+|~~)\s*$/, '');
function fillMsg(e, m, room, done) {
  const body = e.querySelector('.body');
  if (!body) return;
  if (!m.template) m.template = (modelOf(m.model || room.model) || {}).template;
  const sp = splitThink(m, done && !m.stopped);
  if (done && m.stopped) sp.answer = trimDangling(sp.answer);
  // 흐르는 중이거나 중지로 끊긴 답: 닫히지 않은 수식은 날 TeX 로 보이지 않게 그 앞에서 자른다
  if (!done || m.stopped) { sp.answer = holdOpenMath(sp.answer); if (sp.think) sp.think = holdOpenMath(sp.think); }
  put(body);
  const cut = done && !m.stopped && (m.finish === 'length' || sp.unfinished || /최대 길이에서 끊김/.test(m.stats || ''));
  if (sp.think) {
    const stopped = done && m.stopped && !sp.answer;
    const live = sp.open && !done;
    const label = live ? '생각하는 중' : stopped ? '생각 과정 · 중지됨' : (sp.unfinished || (sp.open && done)) ? '생각 과정 · 끊김'
      : m.thinkMs ? `${Math.max(1, Math.round(m.thinkMs / 1000))}초 동안 생각함` : '생각 과정';
    const user = e.dataset.thinkOpen;
    body.append(h('details', { class: 'think', open: (user ? user === '1' : live) ? true : null },
      h('summary', { onclick: ev => { e.dataset.thinkOpen = ev.currentTarget.parentElement.open ? '0' : '1'; } },
        live ? h('i', { class: 'dot busy' }) : I('spark', 's'), h('span', null, label), I('chevR', 's chev')),
      h('div', { class: 'tb md', html: md(trimDangling(sp.think)) })));
  }
  const a = h('div', { class: 'md', html: md(sp.answer) });
  if (!done && (!sp.open || !sp.think)) addCaret(a);
  body.append(a);
  if (cut) {
    const r1 = m.template === 'deepseek-r1';
    const noAns = (r1 || m.template === 'qwen3') && !sp.answer;
    const max = (m.max || OPT.max);
    body.append(h('div', { class: 'cut-note' }, I('info', 's'),
      h('div', { class: 'col g12' },
        h('span', null, noAns ? `답을 쓰기 전에 최대 답변 길이(${fmtNum(max)}토큰)에 닿았습니다.` : `최대 답변 길이(${fmtNum(max)}토큰)에서 답이 끊겼습니다.`),
        e._last && !S.streaming ? h('div', { class: 'row' },
          r1 ? h('button', { class: 'btn sm needs-conn', onclick: continueLast }, I('forward', 's'), '이어서 생성') : null,
          h('button', { class: 'btn sm ghost needs-conn', onclick: () => retryLast(Math.min(32768, max * 2)) }, I('refresh', 's'), `${fmtNum(Math.min(32768, max * 2))}토큰으로 다시 생성`)) : null)));
  }
  const tools = e.querySelector('.tools');
  put(tools,
    e._vk !== undefined ? verSwitch(room, e._vk) : null,
    done && m.content ? h('button', {
      class: 'icon-btn', 'data-tip': '답 복사', 'data-tip-pos': 'top', 'aria-label': '답 복사', onclick: async ev => {
        const btn = ev.currentTarget;
        if (await copyText(sp.answer || m.content)) { btn.innerHTML = svg('check', 's'); announce('복사했습니다'); setTimeout(() => { btn.innerHTML = svg('copy', 's'); }, 1200); }
      },
    }, I('copy', 's')) : null,
    done && e._last && !S.streaming ? h('button', { class: 'icon-btn needs-conn', 'data-tip': '다시 생성 — 지금 답은 버전으로 남습니다', 'data-tip-pos': 'top', 'aria-label': '다시 생성', onclick: () => retryLast() }, I('refresh', 's')) : null,
    m.stats ? h('span', { class: 'stats' }, statsText(m.stats)) : null);
}
// 지난 기록의 통계 글도 지금 꼴로(“412 토큰” → “412토큰”)
// 숫자와 '토큰'은 붙여 쓴다(“412토큰 · 59.8토큰/초”) — 지난 기록의 띄어 쓴 꼴도 이렇게 보인다
const statsText = s => String(s).replace(/ · 최대 길이에서 끊김$/, '').replace(/(\d) 토큰/g, '$1토큰');
// 버전 넘기기 ‹ 2 / 3 › — 고쳐 보내기 · 다시 생성이 남긴 앞 버전
function verSwitch(room, k) {
  const u = room.messages[k];
  if (!u || !u.vers || u.vers.length < 2) return null;
  const busy = !!S.streaming;
  return h('span', { class: 'vers', role: 'group', 'aria-label': `버전 ${u.vi + 1} / ${u.vers.length}` },
    h('button', { class: 'icon-btn', 'data-tip': '이전 버전', 'data-tip-pos': 'top', 'aria-label': '이전 버전', disabled: (busy || u.vi === 0) ? true : null, onclick: () => switchVersion(room, k, u.vi - 1) }, I('chevL', 's')),
    h('span', { class: 'n', 'aria-hidden': 'true' }, `${u.vi + 1} / ${u.vers.length}`),
    h('button', { class: 'icon-btn', 'data-tip': '다음 버전', 'data-tip-pos': 'top', 'aria-label': '다음 버전', disabled: (busy || u.vi === u.vers.length - 1) ? true : null, onclick: () => switchVersion(room, k, u.vi + 1) }, I('chevR', 's')));
}
// 제안은 입력창을 채우기만 한다(보내기는 사람이 — 모델을 불러오는 일이 뜻밖에 시작되지 않게)
const SUGGEST = [
  { t: '다음 문장을 자연스러운 영어로 바꿔 줘: 내일 회의는 3시로 미뤄졌습니다' },
  { t: '파이썬으로 피보나치 함수를 작성해 줘' },
  { t: '봄을 주제로 짧은 시를 써 줘' },
  { t: '아래 글을 세 줄로 요약해 줘', fill: '아래 글을 세 줄로 요약해 줘.\n\n' },
];
function fillComposer(text) {
  const inp = $('#input');
  if (inp.disabled) return;
  inp.value = text;
  autosize();
  inp.focus();
  inp.setSelectionRange(text.length, text.length);
}
// 이 PC 에 맞는 추천: 맞는 것 가운데 7B 일반 모델 Q8_0 → Q4_K_M → 맞는 어떤 것이든(작은 것부터)
function recommendId(st) {
  const d = st.device;
  if (!d || !d.layer) return null;
  const pref = ['qwen2.5-7b-instruct-q8_0', 'qwen2.5-7b-instruct-q4_k_m'];
  for (const id of pref) { const c = st.catalog.find(x => x.id === id); if (c) { const f = fitOf(c); if (f && f.k === 'ok') return id; } }
  const ok = st.catalog.filter(c => { const f = fitOf(c); return f && (f.k === 'ok' || f.k === 'tight'); }).sort((a, b) => a.size - b.size);
  return ok.length ? ok[0].id : null;
}
function helloState(st) {
  if (!st) return 'loading';
  if (!st.device.checked) return 'checking';
  if (!st.device.layer) return 'nogpu';
  if (st.models.some(runnable)) return 'ready';
  if (st.models.length) return 'unsupported';
  return 'nomodel';
}
function renderMsgsIfChanged() {
  const st = S.st;
  if (changed('hello', [helloState(st), recommendId(st), st.catalog.map(c => [c.installed, c.download && c.download.state])])) renderMsgs();
}
// bare: 일시정지 단추 없이(다운로드 목록은 단추를 따로 둔다)
function dlBox(c, bare) {
  const d = c.download || {};
  const paused = d.state === 'cancelled' || d.state === 'failed';
  return h('div', { class: 'dl', 'data-dl': c.id },
    h('div', { class: 'bar' + (paused ? ' paused' : '') }, h('i', { style: 'width:0%' })),
    h('div', { class: 'line' }, h('span', { class: 'txt' }, ''),
      !bare && d.state === 'downloading' ? h('button', { class: 'btn sm ghost needs-conn', 'data-fk': 'pause:' + c.id, onclick: () => pauseDownload(c) }, I('pause', 's'), '일시정지') : null),
    h('div', { class: 'sub' }, ''));
}
// 내려받기 막대는 1초마다 글과 폭만 고친다(모델 화면 · 첫 화면 · 다운로드 목록 · 양자화 칸)
function updateDlBars() {
  if (!S.st) return;
  for (const el of document.querySelectorAll('[data-dlp]')) {
    const c = S.st.catalog.find(x => x.id === el.dataset.dlp);
    const d = c && c.download;
    if (!d) continue;
    const ver = d.state === 'verifying';
    const pct = d.total ? 100 * (ver ? d.verify_bytes : d.received) / d.total : 0;
    const t = (ver ? '확인 ' : '') + pct.toFixed(0) + '%';
    if (el.textContent !== t) el.textContent = t;
  }
  for (const el of document.querySelectorAll('[data-dl]')) {
    const c = S.st.catalog.find(x => x.id === el.dataset.dl);
    const d = c && c.download;
    if (!d) continue;
    const ver = d.state === 'verifying', paused = d.state === 'cancelled' || d.state === 'failed';
    const pct = ver ? (d.total ? 100 * d.verify_bytes / d.total : 0) : (d.total ? 100 * d.received / d.total : 0);
    el.querySelector('.bar > i').style.width = pct.toFixed(1) + '%';
    const eta = d.bytes_per_s > 0 ? (d.total - d.received) / d.bytes_per_s : NaN;
    el.querySelector('.txt').textContent = ver ? `무결성 확인 중${NB}${pct.toFixed(0)}%` : paused ? `${pct.toFixed(0)}%에서 멈춤` : `${pct.toFixed(0)}%${NB}${fmtLeft(eta)}`;
    el.querySelector('.sub').textContent = ver ? `SHA-256${NB}${fmtBytes(d.total)}` : paused ? `${fmtBytes(d.received)} / ${fmtBytes(d.total)}` : `${fmtBytes(d.received)} / ${fmtBytes(d.total)}${NB}${fmtBytes(d.bytes_per_s)}/s`;
  }
}
let stickNext = false;   // 다음 그리기는 맨 아래로(보낼 때)
function renderMsgs() {
  const box = $('#msgs');
  const room = curRoom();
  const chat = $('#chat');
  if (!room || !room.messages.length) {
    box.dataset.room = room ? room.id : '';
    chat.classList.add('empty');
    $('#tobottom').hidden = true;
    const st = S.st;
    const hs = helloState(st);
    const rec = st && recommendId(st);
    const recC = rec && st.catalog.find(c => c.id === rec);
    const recDl = recC && recC.download && (recC.download.state === 'downloading' || recC.download.state === 'verifying');
    const head = h('div', { class: 'row g12' }, h('span', { class: 'eyebrow caps' }, 'GeulPU'), h('span', { class: 'eyebrow' }, '글(geul) 언어로 만든 로컬 LLM'));
    let title, lede, actions = null;
    if (hs === 'ready') {
      title = '무엇을 도와드릴까요?';
      lede = null;
      actions = h('div', { class: 'chips' }, SUGGEST.map(s => h('button', { class: 'chip-btn needs-conn', onclick: () => fillComposer(s.fill || s.t) }, s.t)));
    } else if (hs === 'checking' || hs === 'loading') {
      title = '하드웨어를 확인하는 중입니다';
      lede = '처음 실행할 때 GPU와 드라이버를 확인합니다. 잠시만 기다려 주세요.';
    } else if (hs === 'nogpu') {
      title = '쓸 수 있는 GPU를 찾지 못했습니다';
      lede = 'NVIDIA RTX 30 시리즈 이상(CUDA) 또는 Vulkan 1.3을 지원하는 GPU와 최신 그래픽 드라이버가 필요합니다.';
      actions = h('div', { class: 'col g16 mt20' },
        st.device.reason ? h('details', { class: 'fold' }, h('summary', null, I('chevR', 's'), '확인한 내용'), h('pre', { class: 'log sans' }, st.device.reason)) : null,
        h('div', { class: 'row' }, h('button', { class: 'btn', onclick: () => show('device') }, I('cpu', 's'), '하드웨어 보기')));
    } else if (hs === 'unsupported') {
      title = '이 PC에서 실행할 수 있는 모델이 없습니다';
      lede = '설치된 모델을 이 GPU나 GeulPU가 지원하지 않습니다. 모델 화면에서 이유를 확인하고 다른 모델을 다운로드하세요.';
      actions = h('div', { class: 'row mt24' }, h('button', { class: 'btn', onclick: () => show('models') }, I('box', 's'), '모델 보기'));
    } else {
      title = '먼저 모델이 필요합니다';
      // 맞는 것이 없을 때 — 공유 메모리 32 KB GPU(AMD 등)는 형식 제약까지 그대로 밝힌다(흔한 Q4_0 파일도 출력이 Q6_K 라 아직 받지 않음)
      lede = recC ? `이 PC에는 ${recC.name} ${recC.quant}(${fmtBytes(recC.size)}) 모델을 추천합니다.`
        : st.device.variant === '공유32' ? `이 GPU(공유 메모리 32 KB)는 가중치가 모두 Q8_0이거나 모두 Q4_0인 파일만 실행합니다. 목록의 Q8_0 7B는 그래픽 메모리가 10 GB 이상 필요하고(이 PC ${fmtBytes(st.device.memory)}), 흔한 Q4_0 파일은 출력 가중치가 Q6_K라 아직 받지 않습니다. 지금은 이 PC에서 실행할 수 있는 파일이 없습니다.`
          : `목록의 모델 가운데 이 PC의 그래픽 메모리(${fmtBytes(st.device.memory)})에 맞는 것이 없습니다. Hugging Face에서 더 작은 파일을 찾아볼 수 있습니다 — 받기 전에 실행되는지 확인합니다.`;
      actions = h('div', { class: 'col g0' },
        recDl ? dlBox(recC) : null,
        h('div', { class: 'row mt24' },
          recC && !recC.installed && !recDl ? h('button', { class: 'btn primary needs-conn', onclick: () => startDownload(recC) }, I('download', 's'), '추천 모델 다운로드') : null,
          !recC && st.device.variant !== '공유32' ? h('button', { class: 'btn primary needs-conn', onclick: openHfSearch }, I('search', 's'), '모델 찾기') : null,
          !recC ? h('button', { class: 'btn needs-conn', onclick: () => browse('') }, I('plus', 's'), 'GGUF 파일 추가') : null,
          !recC && st.device.variant === '공유32' ? h('button', { class: 'btn ghost', onclick: () => show('device') }, I('cpu', 's'), '하드웨어 보기') : null,
          recC ? h('button', { class: 'btn' + (!recDl ? ' ghost' : ''), onclick: () => show('models') }, recDl ? '다운로드 진행 보기' : '모델 둘러보기') : null));
    }
    put(box, h('div', { class: 'hello' }, head, h('h1', null, title), lede ? h('p', null, lede) : null, actions));
    updateDlBars();
    updateComposer();
    return;
  }
  chat.classList.remove('empty');
  const th = h('div', { class: 'thread' });
  let prevModel = null;
  const msgs = room.messages, n = msgs.length;
  // 차례 = 사용자 메시지 + 그 뒤의 답 · 오류. 차례의 마지막 요소에 버전 넘기기를 단다
  let uk = -1;
  msgs.forEach((m, k) => {
    if (m.role === 'user') uk = k;
    const vk = (k === n - 1 || msgs[k + 1].role === 'user') && uk >= 0 && m.role !== 'user' ? uk : undefined;
    if (m.role === 'assistant') {
      const mid = m.model || room.model;
      th.append(msgEl(m, room, { who: mid !== prevModel, last: k === n - 1, vk }));
      prevModel = mid;
    } else {
      th.append(msgEl(m, room, { last: k === n - 1 }));
      const vs = vk !== undefined ? verSwitch(room, vk) : null;
      if (vs) th.append(h('div', { class: 'msg-vers' }, vs));
    }
  });
  const sn = S.streaming && S.streaming.roomId === room.id && S.streaming.notice;
  if (sn) { sn.el = msgEl(sn, room); th.append(sn.el); }
  // 맨 아래로는 새 채팅을 열 때 · 보낼 때 · 이미 맨 아래 근처일 때만 — 위를 읽는 중이면 그 자리를 지킨다(고치기 취소 · 모델 바꾸기 등)
  const y = box.scrollTop, near = box.scrollHeight - y - box.clientHeight < 160, other = box.dataset.room !== room.id;
  put(box, th);
  box.scrollTop = stickNext || other || near ? box.scrollHeight : y;
  stickNext = false;
  box.dataset.room = room.id;
  $('#tobottom').hidden = box.scrollHeight - box.scrollTop - box.clientHeight < 240;
  updateComposer();
}
$('#tobottom').innerHTML = svg('down', 's');
$('#tobottom').addEventListener('click', () => { const b = $('#msgs'); b.scrollTo({ top: b.scrollHeight, behavior: 'smooth' }); });
$('#msgs').addEventListener('scroll', () => {
  const b = $('#msgs');
  $('#tobottom').hidden = $('#chat').classList.contains('empty') || b.scrollHeight - b.scrollTop - b.clientHeight < 240;
});
function buildR1Prompt(room, system) {
  let p = R1_BOS + (system || '');
  for (const m of room.messages) {
    if (m.role === 'user') p += R1_USER + m.content;
    else if (m.role === 'assistant' && !m.partial) {
      const ans = splitThink(Object.assign({ template: 'deepseek-r1' }, m), true).answer.trim();   // 앞 차례의 생각은 다시 보내지 않는다
      if (ans) p += R1_ASSIST + ans + R1_EOS;
    }
  }
  return p + R1_ASSIST;
}
async function ensureServer(modelId, notice) {
  const st = S.st;
  if (st.server.state === 'ready' && st.server.model === modelId) return;
  if (S.streaming) S.streaming.loading = true;
  if (!(st.server.state === 'starting' && st.server.model === modelId)) {
    try { await api('/api/server/start', { model: modelId }); }
    catch (e) { throw new Error('모델을 불러오지 못했습니다 — ' + e.message); }
  }
  for (;;) {
    await new Promise(r => setTimeout(r, 1000));
    if (S.streaming && S.streaming.aborted) throw new Error('중지했습니다');
    await refresh();
    const s2 = S.st;
    if (s2.server.state === 'ready' && s2.server.model === modelId) break;
    const j = s2.job;
    if (j && j.kind === 'server' && j.state !== 'running') {
      if (j.state === 'done' && s2.server.state === 'ready') break;
      throw new Error((j.reason || '모델을 불러오지 못했습니다') + (s2.server.reason ? ' — ' + s2.server.reason.slice(-400) : ''));
    }
    if (s2.server.state === 'failed') throw new Error('모델을 불러오지 못했습니다 — ' + (s2.server.reason || ''));
    if (notice) {
      notice.kernel = notice.kernel || !!(j && /커널/.test(j.step || ''));
      notice.text = `${labelById(modelId)} 불러오는 중 · ${fmtClock(j ? j.seconds : s2.server.seconds)}${notice.kernel ? ' · 커널 준비 중' : ''}`;
      notice.pct = j ? Math.min(100, j.progress / 10) : 0;
      const el = notice.el;
      if (el && el.isConnected) {
        el.querySelector('.t').textContent = notice.text;
        el.querySelector('.nbar').style.width = notice.pct + '%';
        if (notice.kernel) el.querySelector('.s').textContent = KERNEL_NOTE;
      }
    }
  }
  if (S.streaming) S.streaming.loading = false;
}
// 벤치마크 · 재현성 검증이 GPU 를 쓰는 중인가(그동안 채팅 모델을 불러올 수 없다)
const benchBusy = () => { const j = S.st && S.st.job; return !!(j && j.state === 'running' && j.kind !== 'server' && j.kind !== 'device'); };
// 보낼 수 없는 까닭(없으면 '') — 아무것도 바꾸지 않고 먼저 묻는다
function sendBlock(room) {
  if (S.streaming) return '다른 채팅의 답이 끝나면 보낼 수 있습니다';
  if (!S.conn) return 'GeulPU.exe와 연결이 끊겨 보낼 수 없습니다';
  if (benchBusy()) return '벤치마크가 끝나면 보낼 수 있습니다';
  const m = room && modelOf(room.model);
  if (!m) return S.st && S.st.models.length ? '위의 모델 선택에서 모델을 고르세요' : '먼저 모델 화면에서 모델을 다운로드하거나 추가하세요';
  if (!runnable(m)) return '이 모델은 이 PC에서 실행할 수 없습니다 — ' + (m.device_reason || (m.shape && m.shape.reason) || '');
  return '';
}
// 차례 k(사용자 메시지)의 새 버전을 연다 — 지금 뒤의 대화(답 · 그 뒤의 차례)는 앞 버전으로 남긴다.
// 버전은 사용자 메시지에 { content, rest } 로: rest 는 그 버전의 뒤 대화(지금 버전은 room.messages 에 있어 null)
function branch(room, k, text) {
  const u = room.messages[k];
  const rest = room.messages.slice(k + 1);
  if (rest.some(x => (x.role === 'assistant' && x.content) || x.role === 'user')) {   // 답이 없던(오류뿐인) 꼴은 남기지 않는다
    if (!u.vers) { u.vers = [{ content: u.content, rest: null }]; u.vi = 0; }
    u.vers[u.vi] = { content: u.content, rest };
    u.vers.push({ content: text, rest: null });
    u.vi = u.vers.length - 1;
  }
  u.content = text;
  room.messages.length = k + 1;
}
function switchVersion(room, k, j) {
  if (S.streaming) return;
  const u = room.messages[k];
  if (!u || !u.vers || j < 0 || j >= u.vers.length || j === u.vi) return;
  u.vers[u.vi] = { content: u.content, rest: room.messages.slice(k + 1) };
  const v = u.vers[j];
  u.content = v.content;
  room.messages.splice(k + 1, room.messages.length, ...(v.rest || []));
  v.rest = null;
  u.vi = j;
  S.editing = null;
  saveRooms();
  const keepY = $('#msgs').scrollTop;
  renderMsgs();
  $('#msgs').scrollTop = keepY;
  announce(`버전 ${j + 1} / ${u.vers.length}`);
}
function retryLast(maxOverride) {
  const room = curRoom();
  if (!room || S.streaming) return;
  const k = room.messages.map(x => x.role).lastIndexOf('user');
  if (k < 0) return;
  const why = sendBlock(room);
  if (why) { toast(why, 'err'); return; }
  branch(room, k, room.messages[k].content);
  replyTo(room, maxOverride);
}
// 메시지 고치기 — 말풍선 자리에서 고치고, 보내면 새 버전(지금 대화는 앞 버전으로 남는다). 취소하면 아무것도 바뀌지 않는다
function startEdit(room, k) {
  if (S.streaming) return;
  S.editing = { roomId: room.id, k };
  renderMsgs();
}
function editBox(m, room, k) {
  const ta = h('textarea', { class: 'edit-input', rows: '1', 'aria-label': '메시지 수정' });
  ta.value = m.content;
  const later = room.messages.slice(k + 1).some(x => x.role === 'user');   // 이 뒤에 다른 차례가 있는가
  const send = h('button', { class: 'btn sm primary needs-conn', onclick: () => submitEdit(room, k, ta.value) }, '보내기');
  const cancel = () => { S.editing = null; renderMsgs(); };
  const fit = () => { ta.style.height = 'auto'; ta.style.height = Math.min(320, ta.scrollHeight) + 'px'; send.disabled = !ta.value.trim(); };
  ta.addEventListener('input', fit);
  ta.addEventListener('keydown', e => {
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); cancel(); }
    else if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); submitEdit(room, k, ta.value); }
  });
  setTimeout(() => { fit(); ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length); }, 0);
  return h('div', { class: 'msg user editing' }, h('div', { class: 'edit-box' }, ta,
    h('div', { class: 'edit-bar' }, h('span', { class: 'hint' }, later ? '보내면 지금 대화는 이전 버전으로 남습니다 · Esc 취소' : '보내면 지금 답은 이전 버전으로 남습니다 · Esc 취소'),
      h('span', { class: 'grow' }), h('button', { class: 'btn sm ghost', onclick: cancel }, '취소'), send)));
}
function submitEdit(room, k, text) {
  text = String(text || '').trim();
  if (!text) return;
  const why = sendBlock(room);
  if (why) { toast(why, 'err'); return; }
  S.editing = null;
  branch(room, k, text);
  replyTo(room);
}
// 흘림 하나를 받아 asst 에 붙인다(보내기 · 이어서 생성이 함께 쓴다). 그릴 요소는 늘 S.streaming.el(다시 그려도 이어진다)
async function streamReply(asst, room, url, body) {
  const tpl = asst.template;
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
        if (piece) {
          if (!tFirst) tFirst = performance.now();
          asst.content += piece;
          if (tpl === 'deepseek-r1' && !asst.thinkMs && (asst.content.includes('</think>') || asst.content.includes('\n\n\n'))) asst.thinkMs = performance.now() - tFirst;
          if (tpl === 'qwen3' && !asst.thinkMs && asst.content.startsWith('<think>') && asst.content.includes('</think>')) asst.thinkMs = performance.now() - tFirst;
        }
        if (c && c.finish_reason) finish = c.finish_reason;
        if (j.usage) usage = j.usage;
        if (j.geulpu) gp = j.geulpu;
      }
    }
    const now = performance.now();
    if (now - lastPaint > 60) {
      lastPaint = now;
      const el = S.streaming && S.streaming.el;
      if (el && el.isConnected) {
        const box = $('#msgs');
        const near = box.scrollHeight - box.scrollTop - box.clientHeight < 120;
        fillMsg(el, asst, room, false);
        if (near) box.scrollTop = box.scrollHeight;
      }
    }
  }
  delete asst.partial;
  asst.finish = finish;
  if (tpl === 'deepseek-r1' && gp && Array.isArray(gp.tokens) && gp.tokens.includes(THINK_END_ID)) asst.thinkEnded = true;
  const n = (usage && usage.completion_tokens) || (gp && gp.tokens && gp.tokens.length) || 0;
  if (gp && gp.generate_us > 0 && n > 1) {
    const tps = (n - 1) / (gp.generate_us / 1e6);
    return `${fmtNum(n)}토큰 · ${tps.toFixed(1)}토큰/초 · 첫 토큰 ${(gp.first_token_ms / 1000).toFixed(0)} ms`;   // 서버의 이 칸은 µs(이름만 ms)
  }
  return tFirst ? `${fmtNum(n)}토큰 · ${((performance.now() - t0) / 1000).toFixed(1)}초` : '';
}
async function send(textOverride) {
  if (S.streaming) { if (!streamingHere()) toast('다른 채팅의 답이 끝나면 보낼 수 있습니다'); return; }
  const input = $('#input');
  const text = (typeof textOverride === 'string' ? textOverride : input.value).trim();
  if (!text) return;
  let room = curRoom();
  if (!room) { newRoom(); room = curRoom(); }
  const why = sendBlock(room);
  if (why) { toast(why, 'err'); return; }
  if (typeof textOverride !== 'string') { input.value = ''; autosize(); }
  if (!room.messages.length) room.title = text.slice(0, 40);
  room.messages.push({ role: 'user', content: text });
  await replyTo(room);
}
// 방의 마지막 사용자 메시지에 답한다(보내기 · 다시 생성 · 고쳐 보내기가 함께 쓴다)
async function replyTo(room, maxOverride) {
  const m = modelOf(room.model);
  const max = maxOverride || OPT.max;
  room.updated = Date.now();
  stickNext = true;
  S.streaming = { aborted: false, ctrl: null, loading: false, roomId: room.id, msg: null, el: null, notice: null };
  saveRooms(); renderRooms(); renderMsgs(); renderChatTop(true);
  try {
    if (!(S.st.server.state === 'ready' && S.st.server.model === room.model)) {
      const notice = { role: 'notice', text: `${labelById(room.model)} 불러오는 중`, pct: 0, kernel: false, el: null };
      S.streaming.notice = notice;
      if (S.roomId === room.id) renderMsgs();
      await ensureServer(room.model, notice);
      S.streaming.notice = null;
      if (notice.el) notice.el.remove();
    }
    const tpl = m.template;
    const asst = { role: 'assistant', content: '', template: tpl, model: room.model, max, partial: true };
    let url, body;
    if (tpl === 'deepseek-r1') {
      url = '/v1/completions';
      body = { prompt: buildR1Prompt(room, OPT.system), max_tokens: max, temperature: OPT.temp, stream: true, geulpu: {} };
    } else {
      url = '/v1/chat/completions';
      const msgs = [];
      if (OPT.system) msgs.push({ role: 'system', content: OPT.system });
      for (const x of room.messages) if (x.role === 'user' || (x.role === 'assistant' && !x.partial)) msgs.push({ role: x.role, content: x.content });
      body = { messages: msgs, max_tokens: max, temperature: OPT.temp, stream: true, stream_options: { include_usage: true }, geulpu: {} };
      if (tpl === 'qwen3') {                 // 서버의 Qwen3 틀 — 앞 답의 생각은 서버가 뗀다, <think> 는 글로 받아 접는다
        body.geulpu.special = true;
        body.chat_template_kwargs = { enable_thinking: OPT.think !== false };
      }
    }
    room.messages.push(asst);
    S.streaming.msg = asst;
    if (S.roomId === room.id) renderMsgs();
    asst.stats = await streamReply(asst, room, url, body);
    room.updated = Date.now();
    store('geulpu.hinted', true);
    saveRooms();
    announce('답변이 끝났습니다');
  } catch (e) {
    const aborted = S.streaming && S.streaming.aborted;
    const last = room.messages[room.messages.length - 1];
    if (last && last.role === 'assistant' && last.partial) {
      delete last.partial;
      if (aborted) { last.stats = '중지됨'; last.stopped = true; }
      else last.stats = '오류';
      if (!last.content) room.messages.pop();
    }
    if (aborted && room.messages[room.messages.length - 1].role === 'user') room.messages.push({ role: 'note', content: '불러오기를 중지했습니다' });
    else if (!aborted) { const em = { role: 'error', content: e.message }; FRESH.add(em); room.messages.push(em); }
    saveRooms();
  } finally {
    S.streaming = null;
    renderRooms();
    renderMsgs();
    renderChatTop(true);
  }
}
// R1 이 길이에서 끊겼을 때 — 받은 글을 그대로 앞에 두고 이어서 생성한다
async function continueLast() {
  const room = curRoom();
  if (!room || S.streaming || !S.conn) return;
  const k = room.messages.length - 1;
  const m = room.messages[k];
  if (!m || m.role !== 'assistant' || m.template !== 'deepseek-r1') return;
  const mm = modelOf(m.model || room.model);
  if (!runnable(mm)) return;
  S.streaming = { aborted: false, ctrl: null, loading: false, roomId: room.id, msg: m, el: null, notice: null };
  m.partial = true;
  m.finish = null;
  m.max = OPT.max;
  renderRooms(); renderMsgs(); renderChatTop(true);
  const before = m.content.length;
  try {
    if (!(S.st.server.state === 'ready' && S.st.server.model === mm.id)) await ensureServer(mm.id, null);
    const hist = Object.assign({}, room, { messages: room.messages.slice(0, k) });
    const prompt = buildR1Prompt(hist, OPT.system) + '<think>' + m.content;
    const stat = await streamReply(m, room, '/v1/completions', { prompt, max_tokens: OPT.max, temperature: OPT.temp, stream: true, geulpu: {} });
    m.stats = stat ? '이어서 ' + stat : m.stats;
    room.updated = Date.now();
    saveRooms();
    announce('답변이 끝났습니다');
  } catch (e) {
    delete m.partial;
    if (!(S.streaming && S.streaming.aborted)) { const em = { role: 'error', content: e.message }; FRESH.add(em); room.messages.push(em); }
    else if (m.content.length > before) { m.stopped = true; m.stats = '중지됨'; }
    saveRooms();
  } finally {
    S.streaming = null;
    renderRooms();
    renderMsgs();
    renderChatTop(true);
  }
}
function stopStream() {
  if (!S.streaming) return;
  S.streaming.aborted = true;
  if (S.streaming.ctrl) S.streaming.ctrl.abort();
  if (S.streaming.loading) api('/api/job/cancel', {}).catch(() => { });
}
function autosize() { const t = $('#input'); t.style.height = 'auto'; t.style.height = Math.min(240, t.scrollHeight) + 'px'; updateSend(); }
$('#input').addEventListener('input', autosize);
// 답이 흐르는 동안 Enter 는 아무것도 하지 않는다(입력은 그대로 — 끝나면 보낸다). 중지는 단추나 Esc.
$('#input').addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); if (!S.streaming) send(); } });
$('#sendbtn').addEventListener('click', () => (streamingHere() ? stopStream() : send()));
document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'o') { e.preventDefault(); show('chat'); newRoom(); }
});

// ---------- 모델 ----------
function pageHead(eyebrow, title, lede, actions) {
  return h('header', { class: 'page-head' }, h('div', { class: 't' }, h('div', { class: 'eyebrow' }, eyebrow || '\u00a0'), h('h1', null, title), lede ? h('p', null, lede) : null),
    actions ? h('div', { class: 'row' }, actions) : null);
}
function catDesc(c) {
  return /r1/i.test(c.id) ? `생각을 먼저 쓰고 답하는 추론 모델${NB}수학${NB}논리` : /coder/i.test(c.id) ? `코드 작성${NB}설명`
    : /qwen3/i.test(c.id) ? `생각 켬${NB}끔을 고르는 대화 모델${NB}한국어${NB}영어` : `한국어${NB}영어 일반 대화`;
}
const vramNeed = c => Math.ceil((c.size + (isBig(c) ? 4 : 2.5) * GIB) / GIB);
// 모델 화면은 두 칸 — 내 모델(받는 중 · 설치된 모델) · 모델 찾기(Hugging Face 의 GGUF 저장소 전체를 정렬해 둘러보고, 고르면 옆에 자세히)
function modelsTab() {
  if (!S.mtab) S.mtab = load('geulpu.mtab', '') || (S.st && (S.st.models.length || dlList().length) ? 'mine' : 'find');
  return S.mtab;
}
function setModelsTab(t, focus) {
  if (S.mtab !== t) {
    S.mtab = t;
    store('geulpu.mtab', t);
    resetSig();
    renderModels();
  }
  if (focus) { const b = document.querySelector(`[data-fk="mtab:${t}"]`); if (b) b.focus({ preventScroll: true }); }
}
function modelTabs(tab) {
  const n = S.st.models.length + dlList().length;
  const b = (t, label, extra) => h('button', {
    role: 'tab', class: tab === t ? 'on' : '', 'aria-selected': tab === t ? 'true' : 'false', tabindex: tab === t ? '0' : '-1', 'data-fk': 'mtab:' + t,
    onclick: () => setModelsTab(t),
  }, label, extra);
  return h('div', {
    class: 'seg-ctl mtabs', role: 'tablist', 'aria-label': '모델 화면',
    onkeydown: ev => { if (ev.key === 'ArrowLeft' || ev.key === 'ArrowRight') { ev.preventDefault(); setModelsTab(tab === 'mine' ? 'find' : 'mine', true); } },
  }, b('mine', '내 모델', n ? h('span', { class: 'cnt' }, String(n)) : null), b('find', '모델 찾기'));
}
function renderModels() {
  const st = S.st;
  const page = $('#page-models');
  const tab = modelsTab();
  const rec = recommendId(st);
  const dls = dlList();
  const eyebrow = `설치 ${st.models.length}개${dls.length ? NB + '받는 중 ' + dls.length + '개' : ''}${st.app.disk_free >= 0 ? NB + '여유 ' + fmtBytes(st.app.disk_free) : ''}`;
  // 받는 동안 바뀌는 수(받은 바이트 · 여유 공간)는 넣지 않는다 — 제자리에서 고친다(다시 그리면 초점 · 열린 메뉴가 사라진다).
  // 모델 찾기는 칸(목록 · 자세히)을 한 번 만들어 두고 다시 쓴다 — 상태가 바뀌어도 목록의 스크롤 · 고른 것이 그대로다
  const struct = tab === 'mine'
    ? [tab, st.models.map(m => [m.id, m.name, m.size, m.verified, !!m.verifying, m.sha256, m.catalog, m.device_reason, m.shape && m.shape.ok]),
      dls.map(c => [c.id, dlStateOf(c), c.download.state, c.download.reason]), st.device.checked, st.device.layer, st.server.model, st.server.state,
      st.settings.context, !!S.streaming]
    : [tab, st.models.length + dls.length];
  if (changed('models', struct)) {
    page.classList.toggle('wide', tab === 'find');
    rebuild(page,
      pageHead(eyebrow, '모델', null,
        [h('button', { class: 'btn needs-conn', 'data-fk': 'add', onclick: () => browse('') }, I('plus', 's'), 'GGUF 파일 추가'),
          h('button', { class: 'icon-btn needs-conn', 'data-tip': '모델 폴더 열기', 'data-tip-pos': 'bottom', 'aria-label': '모델 폴더 열기', onclick: () => api('/api/open', { what: 'models' }).catch(e => toast(e.message, 'err')) }, I('folder'))]),
      modelTabs(tab),
      tab === 'mine' ? mineView() : finderEl());
    if (tab === 'find') finderStart();
  } else {
    const e = page.querySelector('.page-head .eyebrow');
    if (e && e.textContent !== eyebrow) e.textContent = eyebrow;
  }
  // 모델 찾기의 파일 줄(설치됨 · 받는 중 · 이 PC 에 맞는지)은 목록 · 장치가 바뀔 때만 다시 그린다(받는 % 는 updateDlBars 가 제자리에서)
  if (tab === 'find' && changed('finder-st', [st.device.checked, st.device.layer, st.device.variant, st.device.memory, rec,
    st.catalog.map(c => [c.id, c.installed, dlStateOf(c), c.download && c.download.state]), st.models.map(m => m.path)])) fdRedraw();
  for (const m of st.models) {
    const e = document.getElementById('vf-' + m.id);
    if (e && m.verifying) e.textContent = `무결성 확인 중${NB}${m.size > 0 ? Math.round(100 * m.verify_bytes / m.size) : 0}%`;
  }
}
// 내 모델 — 받는 중(멈춤 · 실패 포함)과 설치된 모델
function mineView() {
  const st = S.st;
  const nInst = st.models.length;
  const reasons = [...new Set(st.models.filter(m => m.shape && m.shape.ok && m.device_reason).map(m => m.device_reason))];
  const dls = dlList();
  return h('div', { class: 'mine' },
    dls.length ? h('div', { class: 'section mt0' }, h('div', { class: 'section-head' }, h('span', { class: 'sec' }, '받는 중')),
      h('div', { class: 'list dllist' }, dls.map(dlRow))) : null,
    h('div', { class: 'section' + (dls.length ? '' : ' mt0') }, h('div', { class: 'section-head' }, h('span', { class: 'sec' }, '설치된 모델')),
      // 이 GPU 에서 못 도는 까닭은 여기 한 번만(줄에는 꼬리표만)
      reasons.length ? h('div', { class: 'note-line note-gap' }, I('info', 's'), h('span', null, reasons.length === 1 ? reasons[0] : '일부 모델은 이 GPU에서 실행할 수 없습니다. 꼬리표에 마우스를 올리면 까닭이 보입니다.')) : null,
      nInst ? h('div', { class: 'list mlist' }, modelBlocks())
        : h('div', { class: 'empty-box' }, h('div', { class: 'big' }, '아직 설치된 모델이 없습니다'),
          h('div', null, 'Hugging Face의 모델을 둘러보고 받거나, 이미 있는 GGUF 파일을 추가하세요.'),
          h('div', { class: 'row center mt16' },
            h('button', { class: 'btn primary needs-conn', onclick: () => setModelsTab('find') }, I('search', 's'), '모델 찾기'),
            h('button', { class: 'btn needs-conn', onclick: () => browse('') }, I('plus', 's'), 'GGUF 파일 추가')))));
}
// 받는 중인 파일 한 줄 — 상태 막대의 다운로드 목록과 같은 단추(이름 앞 동그라미 아이콘은 두지 않는다)
function dlRow(c) {
  const ds = dlStateOf(c), d = c.download;
  return h('div', { class: 'item dlitem' },
    h('div', { class: 'main' },
      h('div', { class: 'title' }, h('span', { class: 'nm' }, c.name), h('span', { class: 'qlab' }, c.quant)),
      ds === 'fail' ? dlWhyLine(d.reason, c) : dlBox(c, true)),
    h('div', { class: 'acts needs-conn' },
      ds === 'run' && d.state === 'downloading' ? h('button', { class: 'btn sm ghost', onclick: () => pauseDownload(c) }, I('pause', 's'), '일시정지') : null,
      ds === 'pause' ? h('button', { class: 'btn sm', onclick: () => resumeDownload(c) }, I('download', 's'), '이어서 다운로드') : null,
      ds === 'fail' ? h('button', { class: 'btn sm', onclick: () => startDownload(c) }, I('refresh', 's'), '다시 다운로드') : null,
      ds !== 'run' ? h('button', { class: 'icon-btn', 'data-tip': '받은 것 지우기', 'data-tip-pos': 'top', 'aria-label': `받은 것 지우기: ${c.name} ${c.quant}`, onclick: () => discardDownload(c) }, I('trash', 's')) : null));
}
// 설치된 모델 — 모델마다 머리(이름 · 크기 · 종류 · 문맥) 하나, 그 아래 양자화 줄(양자화 · 파일 크기 · 상태 · 동작)
function modelBlocks() {
  const groups = [];
  for (const m of sortedModels()) {
    const name = displayName(m);
    const g = groups[groups.length - 1];
    if (g && g.name === name) g.items.push(m); else groups.push({ name, items: [m] });
  }
  return groups.map(g => {
    const head = g.items.find(m => m.shape && m.shape.ok) || g.items[0];
    const s = head.shape || {};
    const ctxNow = Math.min(s.context || 0, S.st.settings.context || s.context || 0);
    const sub = s.ok ? `${s.params ? (s.params / 1e9).toFixed(1) + 'B' + NB : ''}${kindOf(head)}${NB}문맥 ${fmtCtx(ctxNow)}${s.context > ctxNow ? ` (최대 ${fmtCtx(s.context)})` : ''}` : kindOf(head);
    return h('div', { class: 'mblock' },
      h('div', { class: 'mhead' },
        h('div', { class: 'main' }, h('div', { class: 'title' }, h('span', { class: 'nm' }, g.name)), h('div', { class: 'sub' }, sub))),
      g.items.map(quantLine));
  });
}
function quantLine(m) {
  const s = m.shape || {};
  const ok = runnable(m);
  const srv = S.st.server;
  const loaded = srv.model === m.id && (srv.state === 'ready' || srv.state === 'starting');
  const name = displayName(m), q = quantOf(m);
  const tags = [];
  if (loaded) tags.push(h('span', { class: 'tag' }, h('i', { class: srv.state === 'ready' ? 'dot ok' : 'dot busy' }), srv.state === 'ready' ? '불러옴' : '불러오는 중'));
  if (!s.ok) tags.push(h('span', { class: 'tag err' }, I('alert'), '지원하지 않는 파일'));
  else if (m.device_reason) tags.push(h('span', { class: 'tag dim', 'data-tip': m.device_reason, 'data-tip-pos': 'top' }, '이 GPU 미지원'));
  if (m.verifying) tags.push(h('span', { class: 'tag', id: 'vf-' + m.id }, '무결성 확인 중'));
  else if (m.catalog && m.sha256 && !m.verified) tags.push(h('span', { class: 'tag err' }, I('alert'), '무결성 확인 안 됨'));
  return h('div', { class: 'qline' + (s.ok && m.device_reason ? ' dimmed' : '') },
    h('span', { class: 'qlab', 'data-tip': m.path, 'data-tip-pos': 'top' }, q || '-'),
    h('span', { class: 'sz' }, fmtBytes(m.size)),
    tags.length ? h('span', { class: 'qtags' }, tags) : null,
    h('span', { class: 'grow' }),
    h('div', { class: 'acts needs-conn' },
      h('button', { class: 'btn sm ghost', 'data-fk': 'chat:' + m.id, 'aria-label': `이 모델로 채팅: ${name} ${q}`, disabled: ok ? null : true, onclick: () => chatWith(m.id) }, I('chat', 's'), '채팅'),
      h('button', {
        class: 'icon-btn', 'data-fk': 'more:' + m.id, 'aria-label': `메뉴: ${name} ${q}`, 'aria-haspopup': 'menu', 'aria-expanded': 'false',
        onclick: ev => menu(ev.currentTarget, '모델 메뉴', [
          loaded ? { icon: 'eject', label: '모델 내리기', sub: 'GPU 메모리를 비웁니다', disabled: !!S.streaming, run: unloadModel } : null,
          { icon: 'hash', label: '파일 무결성 다시 확인', sub: m.verified ? '받은 그대로임을 확인했습니다(SHA-256) · 몇 초' : '받은 그대로인지 SHA-256으로 확인 · 몇 초', disabled: m.verifying, run: () => verifyModel(m.id) },
          '-',
          { icon: 'trash', label: loaded ? '내리고 목록에서 제거' : '목록에서 제거', danger: true, disabled: loaded && !!S.streaming, run: () => removeModel(m, loaded) }], 'right'),
      }, I('dots'))),
    !s.ok && s.reason ? h('div', { class: 'qwhy' }, s.reason) : null);
}
async function unloadModel() {
  if (S.streaming) return;
  try { await api('/api/server/stop', {}); toast('모델을 내렸습니다', 'ok'); resetSig(); refresh(); }
  catch (e) { toast(e.message, 'err'); }
}
// 이 모델로 채팅 — 늘 새 채팅(흐르는 채팅의 모델을 바꾸지 않는다)
function chatWith(id) {
  show('chat');
  const cur = curRoom();
  if (cur && !cur.messages.length && !(S.streaming && S.streaming.roomId === cur.id)) cur.model = id;
  else {
    S.rooms = S.rooms.filter(r => r.messages.length);
    const r = { id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6), title: '새 채팅', model: id, messages: [], created: Date.now(), updated: Date.now() };
    S.rooms.unshift(r);
    S.roomId = r.id;
  }
  S.editing = null;
  saveRooms(); renderRooms(); renderMsgs(); renderChatTop(true);
  $('#input').focus();
}
async function verifyModel(id) {
  try { await api('/api/models/verify', { id }); toast('파일 무결성(SHA-256)을 확인합니다 — 8 GB 파일에 몇 초 걸립니다', 'ok'); resetSig(); refresh(); }
  catch (e) { toast(e.message, 'err'); }
}
async function removeModel(m, loaded) {
  const inside = m.path.toLowerCase().startsWith(S.st.app.models_dir.toLowerCase());
  const cb = h('input', { type: 'checkbox' });
  const body = h('div', { class: 'col g16' }, h('p', { class: 'muted m0' }, `${displayName(m)} ${quantOf(m)} — ${loaded ? '불러온 모델을 내리고 ' : ''}목록에서 제거합니다.`),
    inside ? h('label', { class: 'check' }, cb, `파일도 삭제 (${fmtBytes(m.size)})`) : h('p', { class: 'small muted m0' }, 'GeulPU 모델 폴더 밖의 파일은 삭제하지 않고 목록에서만 제거합니다.'));
  if (!(await confirmBox('모델 제거', body, '제거', 'danger'))) return;
  try {
    if (loaded) await api('/api/server/stop', {});
    await api('/api/models/remove', { id: m.id, delete_file: inside && cb.checked });
    resetSig(); refresh();
  } catch (e) { toast(e.message, 'err'); }
}
// 받는 일의 상태 — 'run'(받는 중 · 확인 중) · 'pause'(멈춤 — 받은 데서 이어받음) · 'fail'(처음부터 다시) · null
function dlStateOf(c) {
  const d = c && c.download;
  if (!d || c.installed) return null;
  if (d.state === 'downloading' || d.state === 'verifying') return 'run';
  const again = d.state === 'failed' && /SHA-256|지웠|크기보다/.test(d.reason || '');
  if ((d.state === 'cancelled' || (d.state === 'failed' && !again)) && d.received > 0) return 'pause';
  if (d.state === 'failed') return 'fail';
  return null;
}
const dlList = () => ((S.st && S.st.catalog) || []).filter(c => dlStateOf(c));
// 다운로드 실패 까닭을 한 문장으로 — 누를 단추(이 상태의 단추)를 말하고, 윈도(WinHTTP) 오류 번호는 도움말로.
// 관리자가 붙이는 "— 다시 누르면 이어서 받습니다"는 뺀다(받은 것이 없으면 이어받기가 아니다)
const WINHTTP = { 12002: '서버가 응답하지 않음(시간 초과)', 12007: '서버 주소를 찾지 못함', 12029: '서버에 연결하지 못함', 12030: '연결이 끊김',
  12031: '서버가 연결을 끊음', 12152: '서버의 응답이 올바르지 않음', 12175: '보안 연결(HTTPS)을 맺지 못함' };
function dlWhy(reason, c) {
  const s = String(reason || '').replace(/\s*—\s*다시 누르면 이어서 받습니다\.?\s*$/, '');
  const m = /\(오류 (\d+)\)/.exec(s);
  const tip = m ? `WinHTTP 오류 ${m[1]}${WINHTTP[+m[1]] ? ' — ' + WINHTTP[+m[1]] : ''}` : '';
  const ds = c ? dlStateOf(c) : null;
  const btn = ds === 'pause' ? "'이어서 다운로드'" : "'다시 다운로드'";
  const d = c && c.download;
  const pct = d && d.total ? Math.floor(100 * d.received / d.total) : 0;
  let text;
  if (/연결이 끊겼|연결하지 못했|요청을 열지/.test(s)) text = ds === 'pause' ? `연결이 끊겨 ${pct}%에서 멈췄습니다. 인터넷 연결을 확인한 뒤 ${btn}를 누르세요.`
    : `다운로드 서버에 연결하지 못했습니다. 인터넷 · 방화벽 · 프록시를 확인한 뒤 ${btn}를 누르세요.`;
  else if (/HTTP (\d+)/.test(s)) text = `다운로드 서버가 오류(HTTP ${/HTTP (\d+)/.exec(s)[1]})를 보냈습니다. 잠시 뒤 ${btn}를 누르세요.`;
  else if (/디스크에 쓰지|쓸 수 없습니다/.test(s)) text = `${s.replace(/\s*\([^)]*\)\s*$/, '')}. 여유 공간과 폴더 권한을 확인한 뒤 ${btn}를 누르세요.`;
  else if (/SHA-256/.test(s)) text = `받은 파일이 원본과 다릅니다(SHA-256 불일치). 받은 것을 지웠으니 ${btn}를 누르세요.`;
  else text = s.replace(/\(오류 \d+\)/, '').trim() || '다운로드하지 못했습니다';
  return { text, tip };
}
const dlWhyLine = (reason, c) => { const w = dlWhy(reason, c); return h('div', { class: 'note-line err', 'data-tip': w.tip || null, 'data-tip-pos': 'top' }, I('alert', 's'), h('span', null, w.text)); };
// 받기 전 확인이 실패한 까닭(파일 앞부분을 받지 못함)
function checkWhy(reason) {
  const s = String(reason || '');
  if (/연결이 끊겼|연결하지 못했|요청을 열지/.test(s)) return 'Hugging Face에서 파일 앞부분을 받지 못했습니다. 인터넷 연결을 확인한 뒤 다시 확인하세요.';
  const m = /HTTP (\d+)/.exec(s);
  if (m) return `Hugging Face가 오류(HTTP ${m[1]})를 보냈습니다. 잠시 뒤 다시 확인하세요.`;
  return s || '확인하지 못했습니다';
}
async function resumeDownload(c) {
  try { await api('/api/models/download', { id: c.id }); resetSig(); refresh(); }
  catch (e) { toast(e.message, 'err'); }
}
function pauseDownload(c) {
  api('/api/models/cancel', { id: c.id }).then(() => { resetSig(); refresh(); }).catch(e => toast(e.message, 'err'));
}
// 단일 선택(radiogroup) — 화살표로 옮기고 고른다(다시 그려지면 새로 고른 것에 초점)
function radioKeys(ev) {
  if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(ev.key)) return;
  const bs = [...ev.currentTarget.querySelectorAll('[role=radio]')];
  if (!bs.length) return;
  const i = Math.max(0, bs.findIndex(b => b.getAttribute('aria-checked') === 'true'));
  const nx = bs[(i + (ev.key === 'ArrowRight' || ev.key === 'ArrowDown' ? 1 : bs.length - 1)) % bs.length];
  ev.preventDefault();
  const fk = nx.dataset.fk;
  nx.click();
  const again = fk ? document.querySelector(`[data-fk="${CSS.escape(fk)}"]`) : null;
  (again || nx).focus();
}
// 다운로드 목록(상태 막대에서 연다) — 받는 중 · 멈춤 · 실패를 모두, 그 자리에서 멈추고 잇는다
function dlPopBody() {
  const rows = dlList().map(c => {
    const ds = dlStateOf(c), d = c.download;
    return h('div', { class: 'dlrow' },
      h('div', { class: 'dlh' }, h('span', { class: 'nm' }, c.name), h('span', { class: 'qlab' }, c.quant)),
      ds === 'fail' ? dlWhyLine(d.reason, c) : dlBox(c, true),
      h('div', { class: 'row' },
        ds === 'run' && d.state === 'downloading' ? h('button', { class: 'btn sm ghost needs-conn', onclick: () => pauseDownload(c) }, I('pause', 's'), '일시정지') : null,
        ds === 'pause' ? h('button', { class: 'btn sm needs-conn', onclick: () => resumeDownload(c) }, I('download', 's'), '이어서 다운로드') : null,
        ds !== 'run' ? h('button', { class: 'btn sm ghost needs-conn', onclick: () => { closePop(); discardDownload(c); } }, I('trash', 's'), '지우기') : null,
        ds === 'fail' ? h('button', { class: 'btn sm needs-conn', onclick: () => { closePop(); startDownload(c); } }, I('refresh', 's'), '다시 다운로드') : null));
  });
  return h('div', { class: 'dlpop', role: 'dialog', 'aria-label': '다운로드' },
    h('div', { class: 'pop-title' }, '다운로드'),
    rows.length ? rows : h('div', { class: 'pad small muted' }, '진행 중인 다운로드가 없습니다.'),
    h('div', { class: 'sep', role: 'separator' }),
    h('button', { class: 'opt', onclick: () => { closePop(); show('models'); } }, I('box', 's'), h('span', { class: 'main' }, h('div', { class: 't' }, '모델 화면에서 보기'))));
}
const dlSig = () => JSON.stringify(dlList().map(c => [c.id, dlStateOf(c), c.download.state, c.download.reason]));
function openDownloads(anchor) {
  if (POP && POPANCHOR === anchor) { closePop(); return; }
  const p = openPop(anchor, dlPopBody(), 'left');
  p.dataset.kind = 'dl';
  p.dataset.sig = dlSig();
  updateDlBars();
  placePop(p, anchor, 'left');   // 막대의 글이 채워져 키가 자란 뒤에 자리를 다시
}
function refreshDlPop() {
  const s = dlSig();
  if (POP.dataset.sig === s) return;
  POP.dataset.sig = s;
  put(POP, dlPopBody());
  updateDlBars();
  if (POPANCHOR) placePop(POP, POPANCHOR, 'left');
}
async function startDownload(c) {
  const st = S.st;
  const f = fitOf(c);
  const bad = f && (f.k === 'no' || f.k === 'nogpu');
  const warn = !f ? null : f.k === 'nogpu' ? '이 PC에서는 쓸 수 있는 GPU를 찾지 못해 이 모델을 실행할 수 없습니다. 다른 PC로 옮겨 쓸 파일이면 그대로 다운로드할 수 있습니다.'
    : f.k === 'no' ? `이 PC의 그래픽 메모리(${fmtBytes(st.device.memory)})로는 실행되지 않을 수 있습니다. 그래픽 메모리 ${vramNeed(c)} GB 이상을 권장합니다.`
      : f.k === 'tight' ? `이 PC의 그래픽 메모리(${fmtBytes(st.device.memory)})에서는 문맥 길이가 줄어듭니다.` : null;
  const body = h('div', { class: 'col g20' },
    h('p', { class: 'muted m0' }, `${c.name} ${c.quant}${NB}${catDesc(c)}`),
    warn ? h('div', { class: 'note-line' + (bad ? ' err' : '') }, I(bad ? 'alert' : 'info', 's'), h('span', null, warn)) : null,
    h('div', { class: 'kv' },
      h('div', { class: 'k' }, '파일'), h('div', { class: 'v mono small break' }, c.file),
      h('div', { class: 'k' }, '크기'), h('div', { class: 'v' }, `${fmtBytes(c.size)} (${fmtNum(c.size)} 바이트)`),
      h('div', { class: 'k' }, '저장 위치'), h('div', { class: 'v small break' }, `${st.app.models_dir}${NB}여유 ${st.app.disk_free >= 0 ? fmtBytes(st.app.disk_free) : '알 수 없음'}`),
      h('div', { class: 'k' }, '출처'), h('div', { class: 'v small break' }, h('a', { href: c.url, target: '_blank', rel: 'noopener' }, c.source)),
      h('div', { class: 'k' }, '라이선스'), h('div', { class: 'v' }, c.license)),
    h('details', { class: 'fold' }, h('summary', null, I('chevR', 's'), '기술 정보'),
      h('div', { class: 'col g8' }, h('div', { class: 'small muted' }, c.note), h('div', { class: 'small mono muted break' }, 'SHA-256 ' + c.sha256))),
    c.check === 'untested' ? h('div', { class: 'note-line' }, I('info', 's'), h('span', null, '이 파일로는 아직 GeulPU에서 실행해 보지 않았습니다. 다운로드가 끝나면 지원 여부를 바로 알려 드립니다.')) : null,
    h('div', { class: 'note-line' }, I('info', 's'), h('span', null, '중간에 끊겨도 다시 누르면 이어서 받고, 다 받으면 SHA-256으로 파일이 맞는지 확인합니다.')));
  if (!(await confirmBox('모델 다운로드', body, '다운로드', bad ? 'quiet' : null))) return;
  try { await api('/api/models/download', { id: c.id }); resetSig(); refresh(); }
  catch (e) { toast(e.message, 'err'); }
}
// 파일 고르기 — pick 이 있으면 폴더 고르기(설정의 모델 폴더): 파일은 감추고 '이 폴더 선택'
async function browse(path, pick) {
  let j;
  try { j = await api('/api/fs?path=' + encodeURIComponent(path)); }
  catch (e) { toast(e.message, 'err'); return; }
  const list = h('div', { class: 'fs-list' });
  if (j.path) list.append(h('button', { class: 'fs-item', onclick: () => browse(j.parent || '', pick) }, I('chevU', 's'), h('span', { class: 'n' }, '상위 폴더')));
  const entries = pick ? j.entries.filter(e => e.dir) : j.entries;
  for (const e of entries) {
    list.append(h('button', {
      class: 'fs-item', onclick: async () => {
        if (e.dir) { browse(e.path, pick); return; }
        closeModal();
        try { await api('/api/models/add', { path: e.path }); toast(`추가했습니다: ${e.name}`, 'ok'); resetSig(); refresh(); }
        catch (err) { toast(err.message, 'err'); }
      },
    }, I(e.dir ? 'folder' : 'file', 's'), h('span', { class: 'n' }, e.name), e.dir ? I('chevR', 's') : h('span', { class: 'num muted small' }, fmtBytes(e.size))));
  }
  if (!entries.length) list.append(h('div', { class: 'fs-item muted' }, pick ? '하위 폴더가 없습니다' : '이 폴더에는 .gguf 파일이나 하위 폴더가 없습니다'));
  const inp = h('input', { type: 'text', value: j.path || '', placeholder: '폴더 경로(예: D:\\models)', 'aria-label': '폴더 경로' });
  const go = () => browse(inp.value.trim(), pick);
  inp.addEventListener('keydown', ev => { if (ev.key === 'Enter') go(); });
  modal(h('div', null, h('h2', null, pick ? '모델 폴더 고르기' : 'GGUF 파일 추가'),
    h('p', { class: 'small muted m0 mb12' }, pick ? '받은 모델을 둘 폴더를 고르세요. 다음 실행부터 적용됩니다.' : 'GeulPU는 qwen2 구조(Qwen2.5 · DeepSeek-R1-Distill-Qwen, 7B 이상)와 qwen3 구조(Qwen3 1.7B · 8B · 14B)의 GGUF를 실행합니다. 추가하면 지원 여부를 바로 확인합니다.'),
    h('div', { class: 'fs-path' }, inp, h('button', { class: 'btn', onclick: go }, '이동')), list),
    [h('button', { class: 'btn ghost', onclick: () => closeModal() }, '닫기'),
      pick ? h('button', { class: 'btn primary', disabled: j.path ? null : true, onclick: () => { closeModal(); pick(j.path); } }, '이 폴더 선택') : null].filter(Boolean), false, '.fs-item');
}

// ---------- 모델 찾기 — Hugging Face 의 GGUF 저장소 전체를 정렬해 둘러본다(검색은 좁히는 도구) ----------
// 목록 · 자세히 · 파일 목록 · 모델 설명(README)은 브라우저가 Hugging Face API 에 바로 묻는다(정렬 · 거르기 · 검색어가 Hugging Face 로 간다).
// 받기 전 확인(파일 앞 몇 MB 의 GGUF 머리)과 받기는 관리자가 — 주소는 관리자가 저장소 · 파일 이름으로 짓는다.
const HFHOST = 'https://huggingface.co';
// GeulPU 가 받는 형식(엔진: Q8_0 · Q4_0 · Q4_K · Q5_K · Q6_K) — 파일 이름으로 먼저 어림한다(확인은 GGUF 머리로)
const quantFromName = n => { const m = /(IQ\d_[A-Z]+|Q\d_K(?:_[SML])?|Q\d_\d|BF16|F16|F32)/i.exec(n || ''); return m ? m[1].toUpperCase() : ''; };
const quantOk = q => /^(Q8_0|Q4_0|Q4_K(_[SM])?|Q5_K(_[SM])?|Q6_K)$/.test(q);
const hfName = id => String(id).split('/').pop().replace(/[-_.]?GGUF$/i, '');
const archOk = a => a === 'qwen2' || a === 'qwen3';
// 크기로 어림하는 지원 여부(확인은 받기 전에 GGUF 머리로) — 매개변수 수(미세조정도 바탕과 같고, 출력을 따로 둔 변환은 낱말표만큼 크다).
// Qwen3: 1.7B · 8B · 14B 는 실행(질의 폭 = 너비), 0.6B · 4B · 32B 는 아직 아님(질의 폭 ≠ 너비), 그 밖의 크기는 받기 전 확인.
// Qwen2: 헤드 크기 64 인 작은 것(0.5B 등)은 아직 아님
const Q3OK = [[1.6e9, 2.1e9], [7.9e9, 8.4e9], [14.5e9, 15.0e9]];
const Q3BAD = [[0.55e9, 0.8e9], [3.9e9, 4.5e9], [32e9, 33.5e9]];
const inRange = (p, rs) => rs.some(([lo, hi]) => p >= lo && p <= hi);
// 대화용이 아닌 모델(이미지 생성의 텍스트 인코더 · 임베딩 · 순위 매기기 · 음성) — 같은 구조라도 채팅에 쓰지 못한다(꼬리표 · 용도 · 이름으로)
const NONCHAT = ['text-to-image', 'image-to-image', 'feature-extraction', 'sentence-similarity', 'text-classification', 'text-ranking',
  'text-to-speech', 'automatic-speech-recognition', 'text-to-audio', 'audio-to-audio'];
const fdNonChat = m => {
  const pipe = m && m.cardData && m.cardData.pipeline_tag;
  return (pipe && NONCHAT.includes(pipe)) || ((m && m.tags) || []).some(t => NONCHAT.includes(t)) || /text[-_ ]?encoder|embedding|reranker|[-_]tts\b/i.test((m && m.id) || '');
};
function fdSupport(m) {
  const g = (m && m.gguf) || {};
  const a = g.architecture, p = g.total || 0;
  if (!a) return { k: 'unknown', t: '구조 정보 없음' };
  if (!archOk(a)) return { k: 'arch', t: `${a} · 미지원 구조` };
  if (fdNonChat(m)) return { k: 'task', t: '대화용 모델 아님', why: '이미지 생성용 텍스트 인코더 · 임베딩 · 음성처럼 채팅에 쓰는 모델이 아닙니다.' };
  if (a === 'qwen3') {
    if (inRange(p, Q3OK)) return { k: 'ok', t: 'GeulPU에서 실행됨' };
    if (inRange(p, Q3BAD)) return { k: 'size', t: '이 크기는 아직 미지원', why: 'Qwen3의 0.6B · 4B · 32B는 질의 폭이 너비와 달라 GeulPU가 아직 실행하지 않습니다.' };
    return { k: 'check', t: '크기 확인 필요', why: '흔한 Qwen3 크기(1.7B · 8B · 14B)가 아닙니다. 받기 전에 파일 앞부분을 받아 실행되는지 확인합니다.' };
  }
  if (p > 0 && p < 1.4e9) return { k: 'size', t: '이 크기는 아직 미지원', why: '헤드 크기가 64인 작은 Qwen2(0.5B 등)는 GeulPU가 아직 실행하지 않습니다.' };
  return { k: 'ok', t: 'GeulPU에서 실행됨' };
}
const fmtParams = p => (p >= 1e9 ? (p / 1e9).toFixed(p >= 1e10 ? 0 : 1) + 'B' : Math.round(p / 1e6) + 'M');
// 수는 만 · 억으로(55.5만 · 1.2억)
function fmtCount(n) {
  n = n || 0;
  if (n >= 1e8) return (n / 1e8).toFixed(1).replace(/\.0$/, '') + '억';
  if (n >= 1e4) return (n >= 1e6 ? String(Math.round(n / 1e4)) : (n / 1e4).toFixed(1).replace(/\.0$/, '')) + '만';
  return fmtNum(n);
}
function fmtAgo(iso) {
  const t = Date.parse(iso || '');
  if (!(t > 0)) return '-';
  const d = Math.floor((Date.now() - t) / 86400000);
  if (d < 1) return '오늘';
  if (d < 2) return '어제';
  if (d < 7) return `${d}일 전`;
  if (d < 31) return `${Math.floor(d / 7)}주 전`;
  if (d < 365) return `${Math.floor(d / 30)}개월 전`;
  return `${Math.floor(d / 365)}년 전`;
}
const fmtDate = iso => { const t = Date.parse(iso || ''); return t > 0 ? new Date(t).toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' }) : '-'; };
const asList = v => (Array.isArray(v) ? v : v ? [v] : []).map(String);
// 저장소의 라이선스 — cardData.license, 없으면 꼬리표(license:…)
const fdLicense = m => (m && m.cardData && m.cardData.license) || ((m && m.tags) || []).map(String).filter(t => t.startsWith('license:')).map(t => t.slice(8))[0] || '';
// 목록(앱에 든 받을 수 있는 모델 · Hugging Face 에서 더한 것)의 항목이 어느 저장소의 것인가
const fdRepoOf = c => { const m = /huggingface\.co\/([^/]+\/[^/]+)\/resolve\//.exec(c.url || ''); return m ? m[1] : String(c.source || '').replace(/^huggingface\.co\//, ''); };
const fdCat = repo => ((S.st && S.st.catalog) || []).filter(c => fdRepoOf(c).toLowerCase() === String(repo).toLowerCase());
const fdChecked = repo => fdCat(repo).some(c => c.check === 'tested' || c.check === 'crosscheck');
// 매개변수 수로 Q4_K_M 파일 크기를 어림한다(4.85 비트/매개변수) — '이 PC 메모리에 맞는 크기' 거르기
const fdEst = p => p * 4.85 / 8;
const fdFits = p => { const f = fitOf({ size: fdEst(p), params: fmtParams(p), id: '' }); return !!f && (f.k === 'ok' || f.k === 'tight'); };

// 기본은 '요즘 뜨는'(Hugging Face 의 트렌드 점수) — 30일 다운로드 순은 다운로드가 부풀려진 저장소가 위에 오기 쉽다
const FD_SORTS = [['trendingScore', '요즘 뜨는', 'Hugging Face의 트렌드 점수 순'], ['downloads', '인기', '최근 30일 다운로드가 많은 순'],
  ['likes', '좋아요', '좋아요가 많은 순'], ['lastModified', '최근 업데이트', '최근에 고친 저장소 순']];
const FD_SIZES = [['all', '모든 크기'], ['s', '~4B'], ['m', '4~10B'], ['l', '10~20B'], ['xl', '20B~']];
const FD_EXPAND = ['gguf', 'downloads', 'likes', 'lastModified', 'cardData', 'trendingScore', 'author', 'createdAt', 'tags'].map(x => 'expand[]=' + x).join('&');
const FD = {
  el: null, bar: null, sum: null, list: null, more: null, scroll: null, det: null, y: [0, 0],
  // only: GeulPU 에서 실행되는 것만 — 늘 켠 채로 시작한다(실행 안 되는 모델도 보기는 그때그때 켠다 — 저장하지 않음)
  sort: load('geulpu.fd.sort', 'trendingScore'), only: true, size: load('geulpu.fd.size', 'all'), fit: load('geulpu.fd.fit', false),
  checked: false, q: '', draft: '',
  items: [], seen: new Set(), srcs: [], busy: false, done: false, err: '', seq: 0, started: false, dry: 0,
  sel: null, modal: null, info: {}, chk: new Map(), readmeOpen: {},
};
// 모델 화면의 '모델 찾기' 칸으로(첫 화면의 단추 등) — 검색 칸에 초점
function openHfSearch() {
  show('models');
  setModelsTab('find');
  setTimeout(() => { const i = FD.bar && FD.bar.querySelector('input'); if (i) i.focus({ preventScroll: true }); }, 60);
}
// 찾기 칸 — 한 번 만들어 두고 다시 쓴다(위: 검색 · 정렬 · 거르기, 아래: 왼쪽 목록 · 오른쪽 자세히).
// 넓은 창에서는 화면 전체가 아니라 목록 칸과 자세히 칸이 저마다 스크롤된다 — 좁은 창은 목록 하나라 화면 전체가 스크롤되고, 자세히는 창으로 연다
function finderEl() {
  if (FD.el) return FD.el;
  FD.bar = h('div', { class: 'fd-bar' });
  FD.sum = h('div', { class: 'fd-sum', 'aria-live': 'polite' });
  FD.list = h('div', { class: 'fd-list', 'aria-label': '모델 목록' });
  FD.more = h('div', { class: 'fd-more' });
  FD.scroll = h('div', { class: 'fd-scroll' }, FD.list, FD.more);
  FD.det = h('aside', { class: 'fd-detail', 'aria-label': '모델 자세히' });
  FD.el = h('div', { class: 'finder' }, FD.bar, h('div', { class: 'fd-body' }, FD.sum, FD.scroll, FD.det));
  fdBar();
  // 두 칸의 스크롤 자리를 적어 둔다 — 화면을 다시 짜면(받기를 시작해 칸 수가 바뀔 때 · 다른 화면에 다녀올 때) 칸이 떨어졌다 붙어 처음으로 가므로 되돌린다
  [FD.scroll, FD.det].forEach((el, i) => el.addEventListener('scroll', () => { if (el.getClientRects().length) FD.y[i] = el.scrollTop; }, { passive: true }));
  // 목록 끝이 가까워지면 더 불러온다('더 보기' 단추도 그대로 둔다 — 키보드 · 화면 낭독기)
  FD.scroll.addEventListener('scroll', fdAutoMore, { passive: true });
  $('#view-models').addEventListener('scroll', fdAutoMore, { passive: true });
  return FD.el;
}
function finderStart() {
  if (!FD.started) { FD.started = true; fdReload(); return; }
  FD.scroll.scrollTop = FD.y[0];
  FD.det.scrollTop = FD.y[1];
  fdDrawList();
  fdRedraw();
}
function fdAutoMore() { if (FD.started && !FD.busy && !FD.done && !FD.err && fdNearEnd()) fdMore(); }
function fdBarFocus(fn) {
  const a = document.activeElement;
  const fk = a && FD.bar.contains(a) ? a.dataset.fk : null;
  fn();
  if (fk) { const b = FD.bar.querySelector(`[data-fk="${CSS.escape(fk)}"]`); if (b) b.focus({ preventScroll: true }); }
}
function fdBar() {
  fdBarFocus(() => {
    const inp = h('input', { type: 'text', placeholder: '이름으로 좁히기 — 예: qwen3, coder, r1, 14b', 'aria-label': '모델 이름으로 좁히기', 'data-fk': 'fd-q', enterkeyhint: 'search' });
    inp.value = FD.draft;
    let t = 0;
    inp.addEventListener('input', () => { FD.draft = inp.value; clearTimeout(t); t = setTimeout(() => fdSearch(inp.value.trim()), 450); fdClearBtn(); });
    inp.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.isComposing) { e.preventDefault(); clearTimeout(t); fdSearch(inp.value.trim()); }
      if (e.key === 'Escape' && inp.value) { e.preventDefault(); inp.value = ''; FD.draft = ''; clearTimeout(t); fdSearch(''); fdClearBtn(); }
    });
    const clear = h('button', { class: 'icon-btn sm', 'aria-label': '검색어 지우기', 'data-fk': 'fd-qx', hidden: FD.draft ? null : true,
      onclick: () => { inp.value = ''; FD.draft = ''; fdSearch(''); fdClearBtn(); inp.focus(); } }, I('x', 's'));
    const radio = (list, cur, label, fk, set) => h('div', { class: 'seg-ctl fd-seg', role: 'radiogroup', 'aria-label': label, onkeydown: radioKeys }, list.map(([k, text, tip]) =>
      h('button', {
        role: 'radio', class: cur === k ? 'on' : '', 'aria-checked': cur === k ? 'true' : 'false', tabindex: cur === k ? '0' : '-1', 'data-fk': fk + ':' + k,
        'data-tip': tip || null, 'data-tip-pos': 'bottom', onclick: () => { if (cur !== k) set(k); },
      }, text)));
    const chip = (on, text, tip, fk, flip) => h('button', { class: 'fchip' + (on ? ' on' : ''), 'aria-pressed': on ? 'true' : 'false', 'data-fk': fk, 'data-tip': tip, 'data-tip-pos': 'bottom', onclick: flip },
      on ? I('check', 's') : null, text);
    // 기본은 GeulPU 에서 실행되는 것만 — 켜면 실행 안 되는 모델(다른 구조 · 아직 미지원 크기)도 흐리게 함께 보인다
    const all = h('input', { type: 'checkbox', role: 'switch', 'data-fk': 'fd-all', 'aria-label': '실행 안 되는 모델도 보기',
      onchange: () => { FD.only = !all.checked; fdBar(); fdReload(); } });
    all.checked = !FD.only;
    const allSw = h('label', { class: 'fd-toggle', 'data-tip': '끄면 GeulPU에서 실행되는 구조(qwen2 · qwen3)와 크기만 보입니다', 'data-tip-pos': 'bottom' },
      h('span', { class: 'switch' }, all, h('i')), h('span', null, '실행 안 되는 모델도 보기'));
    put(FD.bar,
      h('div', { class: 'fd-line' },
        h('div', { class: 'fd-search' }, I('search', 's'), inp, clear),
        radio(FD_SORTS, FD.sort, '정렬', 'fd-sort', k => { FD.sort = k; store('geulpu.fd.sort', k); fdBar(); fdReload(); })),
      h('div', { class: 'fd-line' },
        allSw,
        h('span', { class: 'fd-div', 'aria-hidden': 'true' }),
        chip(FD.checked, 'GeulPU 확인됨', 'GeulPU에서 실제로 돌려 본 파일이 있는 저장소만', 'fd-checked', () => { FD.checked = !FD.checked; fdBar(); fdReload(); }),
        chip(FD.fit, '이 PC에 맞는 크기', '매개변수 수로 어림한 Q4_K_M 파일이 이 PC의 그래픽 메모리에 들어가는 것만', 'fd-fit', () => { FD.fit = !FD.fit; store('geulpu.fd.fit', FD.fit); fdBar(); fdReload(); }),
        h('span', { class: 'grow' }),
        radio(FD_SIZES, FD.size, '크기', 'fd-size', k => { FD.size = k; store('geulpu.fd.size', k); fdBar(); fdReload(); })));
  });
}
function fdClearBtn() { const b = FD.bar.querySelector('[data-fk="fd-qx"]'); if (b) b.hidden = !FD.draft; }
function fdSearch(q) { if (q === FD.q) return; FD.q = q; fdReload(); }
// 정렬 · 거르기 · 검색어가 바뀌면 처음부터 — '실행되는 것만'은 꼬리표 qwen2 · qwen3 의 두 목록을 정렬 열쇠로 맞물려 하나로
function fdReload() {
  FD.seq++;
  FD.items = []; FD.seen = new Set(); FD.done = false; FD.err = ''; FD.busy = false; FD.dry = 0;
  const base = `${HFHOST}/api/models?filter=gguf&sort=${FD.sort}&direction=-1&limit=100&${FD_EXPAND}${FD.q ? '&search=' + encodeURIComponent(FD.q) : ''}`;
  FD.srcs = FD.checked ? [] : (FD.only ? [base + '&filter=qwen2', base + '&filter=qwen3'] : [base]).map(u => ({ next: u, buf: [] }));
  fdDrawList();
  FD.scroll.scrollTop = FD.y[0] = 0;
  fdMore();
}
const fdKey = m => (FD.sort === 'lastModified' ? Date.parse(m.lastModified || '') || 0 : Number(m[FD.sort]) || 0);
function fdPass(m) {
  const sup = fdSupport(m);
  if (FD.only && sup.k !== 'ok') return false;
  const p = (m.gguf && m.gguf.total) || 0;
  if (FD.size !== 'all') {
    if (!p) return false;
    const b = p / 1e9;
    if (FD.size === 's' && b > 4.5) return false;
    if (FD.size === 'm' && (b <= 4.5 || b > 10.5)) return false;
    if (FD.size === 'l' && (b <= 10.5 || b > 20.5)) return false;
    if (FD.size === 'xl' && b <= 20.5) return false;
  }
  if (FD.fit && !(p && fdFits(p))) return false;
  if (FD.q && FD.checked && !m.id.toLowerCase().includes(FD.q.toLowerCase())) return false;
  return true;
}
async function fdFetch(s) {
  const r = await fetch(s.next);
  if (!r.ok) throw new Error('HTTP ' + r.status);
  const j = await r.json();
  if (Array.isArray(j)) s.buf.push(...j);
  const m = /<([^>]+)>;\s*rel="next"/.exec(r.headers.get('Link') || '');
  s.next = m ? m[1] : null;
}
// 다음 n 개(거른 뒤) — 목록마다 정렬된 차례라 머리끼리 견주어 큰 것부터(같은 저장소는 한 번만). 한 번에 받는 쪽수는 여덟까지
async function fdMore(n = 30) {
  if (FD.busy || FD.done) return;
  const my = FD.seq;
  const before = FD.items.length;
  FD.busy = true; FD.err = '';
  fdDrawMore();
  try {
    if (FD.checked) await fdLoadChecked(my);
    else {
      let added = 0, pages = 0;
      while (added < n && pages < 8) {
        for (const s of FD.srcs) if (!s.buf.length && s.next) { pages++; await fdFetch(s); if (my !== FD.seq) return; }
        const live = FD.srcs.filter(s => s.buf.length);
        if (!live.length) { FD.done = true; break; }
        let best = live[0];
        for (const s of live) if (fdKey(s.buf[0]) > fdKey(best.buf[0])) best = s;
        const m = best.buf.shift();
        if (!m || FD.seen.has(m.id)) continue;
        FD.seen.add(m.id);
        if (fdPass(m)) { FD.items.push(m); added++; }
      }
      if (!FD.srcs.some(s => s.buf.length || s.next)) FD.done = true;
    }
  } catch (_) { if (my === FD.seq) FD.err = 'Hugging Face에 연결하지 못했습니다. 인터넷 연결을 확인한 뒤 다시 시도하세요.'; }
  if (my !== FD.seq) return;
  FD.busy = false;
  FD.dry = FD.items.length === before ? FD.dry + 1 : 0;
  fdDrawList();
  // 넓은 창에서는 첫 모델을 옆에 — 처음 열 때, 그리고 새로 불러온 목록에 고른 것이 없을 때
  if (FD.items.length && !fdNarrow() && (!FD.sel || (before === 0 && !FD.items.some(i => i.id === FD.sel)))) fdSelect(FD.items[0].id, true);
  // 목록 끝이 아직 화면 가까이에 있으면 더 — 거르기가 빡빡해 세 번 잇달아 하나도 못 얻으면 멈춘다('더 보기'로 잇는다)
  requestAnimationFrame(() => { if (!FD.done && !FD.err && !FD.busy && FD.dry < 3 && fdNearEnd()) fdMore(); });
}
function fdNearEnd() {
  if (!FD.more || !FD.more.isConnected || !FD.more.getClientRects().length) return false;
  // 넓은 창은 목록 칸이, 좁은 창은 화면 전체가 스크롤된다
  const sc = fdNarrow() ? $('#view-models') : FD.scroll;
  return FD.more.getBoundingClientRect().top < sc.getBoundingClientRect().bottom + 600;
}
// 'GeulPU 확인됨' — 앱의 목록에서 실제로 돌려 본 파일이 있는 저장소(몇 개라 한 번에), 정보는 Hugging Face 에서
async function fdLoadChecked(my) {
  const repos = [...new Set(((S.st && S.st.catalog) || []).filter(c => c.check === 'tested' || c.check === 'crosscheck').map(fdRepoOf).filter(Boolean))];
  const got = await Promise.all(repos.map(r => fetch(`${HFHOST}/api/models/${r}?${FD_EXPAND}`).then(x => (x.ok ? x.json() : null)).catch(() => null)));
  if (my !== FD.seq) return;
  const list = got.map((m, i) => m || { id: repos[i] }).filter(fdPass);
  list.sort((a, b) => fdKey(b) - fdKey(a));
  FD.items = list;
  FD.done = true;
}
const fdNarrow = () => window.matchMedia('(max-width: 960px)').matches;
function fdDrawList() {
  if (!FD.list) return;
  put(FD.list, FD.items.map(fdRow));
  const sortName = (FD_SORTS.find(s => s[0] === FD.sort) || FD_SORTS[0])[1];
  const conds = [FD.only ? 'GeulPU에서 실행되는 것' : '실행 안 되는 것 포함', FD.checked ? 'GeulPU 확인됨' : null, FD.fit ? '이 PC에 맞는 크기' : null,
    FD.size !== 'all' ? (FD_SIZES.find(s => s[0] === FD.size) || [])[1] : null, FD.q ? `“${FD.q}”` : null].filter(Boolean);
  put(FD.sum, h('span', { class: 'ink' }, FD.items.length ? `${fmtNum(FD.items.length)}개${FD.done ? '' : ' 이상'}` : FD.busy ? '불러오는 중' : '0개'),
    h('span', null, `${NB}${sortName}순${NB}${conds.join(' · ')}`),
    h('span', { class: 'grow' }),
    h('span', { class: 'faint' }, 'Hugging Face의 GGUF 저장소'));
  fdDrawMore();
}
function fdDrawMore() {
  if (!FD.more) return;
  let body = null;
  if (FD.busy) body = h('div', { class: 'row center small muted' }, h('i', { class: 'dot busy' }), '불러오는 중…');
  else if (FD.err) body = h('div', { class: 'col center g12' }, h('div', { class: 'note-line err' }, I('alert', 's'), h('span', null, FD.err)),
    h('button', { class: 'btn sm needs-conn', onclick: () => { FD.err = ''; fdMore(); } }, I('refresh', 's'), '다시 시도'));
  else if (!FD.items.length && FD.done) body = h('div', { class: 'empty-box' }, h('div', { class: 'big' }, '조건에 맞는 모델이 없습니다'),
    h('div', null, FD.only ? "거르기를 줄이거나, '실행 안 되는 모델도 보기'를 켜면 Hugging Face의 모든 GGUF 모델이 보입니다(실행되지 않는 것은 흐리게)." : '검색어나 거르기를 바꿔 보세요.'));
  else if (!FD.done) body = h('button', { class: 'btn ghost w100 needs-conn', onclick: () => fdMore() }, I('chevD', 's'), '더 보기');
  put(FD.more, body);
}
function fdStat(icon, text, label) { return h('span', { class: 'st', 'aria-label': label ? `${label} ${text}` : null }, I(icon, 's'), h('span', { 'aria-hidden': label ? 'true' : null }, text)); }
function fdRow(m) {
  const g = m.gguf || {};
  const sup = fdSupport(m);
  const cat = fdCat(m.id);
  const st = S.st;
  const rec = st && cat.some(c => c.id === recommendId(st));
  const base = asList(m.cardData && m.cardData.base_model);
  const by = [m.author || m.id.split('/')[0], base.length ? `${base[0].split('/').pop()} 기반` : null].filter(Boolean).join(NB);
  const badge = fdChecked(m.id) ? h('span', { class: 'tag', 'data-tip': 'GeulPU에서 실제로 돌려 본 파일이 있습니다', 'data-tip-pos': 'top' }, I('shield'), 'GeulPU 확인됨')
    : sup.k === 'ok' ? (FD.only ? null : h('span', { class: 'tag' }, I('check'), '실행됨'))
      : h('span', { class: 'tag dim', 'data-tip': sup.why || null, 'data-tip-pos': 'top' }, sup.k === 'unknown' ? '구조 알 수 없음' : sup.t);
  return h('button', {
    class: 'fd-row' + (FD.sel === m.id ? ' on' : '') + (sup.k === 'arch' || sup.k === 'size' || sup.k === 'task' ? ' dim' : ''), 'data-repo': m.id, 'data-fk': 'fd:' + m.id,
    'aria-current': FD.sel === m.id ? 'true' : null, onclick: () => fdSelect(m.id),
  },
    h('span', { class: 'main' },
      h('span', { class: 'top' }, h('span', { class: 'nm' }, hfName(m.id)), g.total ? h('span', { class: 'qlab' }, fmtParams(g.total)) : null),
      h('span', { class: 'by' }, by),
      h('span', { class: 'foot' },
        fdStat('download', fmtCount(m.downloads), '최근 30일 다운로드'), fdStat('heart', fmtCount(m.likes), '좋아요'), fdStat('clock', fmtAgo(m.lastModified), '업데이트'),
        h('span', { class: 'grow' }), rec ? h('span', { class: 'tag' }, I('star'), '이 PC 추천') : null, badge)));
}
function fdSelect(repo, auto) {
  FD.sel = repo;
  for (const b of FD.list.querySelectorAll('.fd-row')) {
    const on = b.dataset.repo === repo;
    b.classList.toggle('on', on);
    if (on) b.setAttribute('aria-current', 'true'); else b.removeAttribute('aria-current');
  }
  fdLoadInfo(repo);
  if (fdNarrow() && !auto) {
    FD.modal = repo;
    modal(h('div', { class: 'fd-d-wrap' }, fdDetail(repo)), [h('button', { class: 'btn', onclick: () => closeModal() }, '닫기')], true, '.foot .btn', () => { FD.modal = null; });
  }
  fdRedraw();
  if (!fdNarrow()) FD.det.scrollTop = FD.y[1] = 0;
}
// 저장소 하나의 정보(자세한 정보 · 파일 목록 · 모델 설명) — 셋을 함께 묻고 오는 대로 그린다
function fdLoadInfo(repo) {
  if (FD.info[repo] && !FD.info[repo].err) return;
  const x = FD.info[repo] = { busy: true };
  const done = () => { if (FD.sel === repo || FD.modal === repo) fdRedraw(); };
  const enc = repo.split('/').map(encodeURIComponent).join('/');
  fetch(`${HFHOST}/api/models/${enc}?${FD_EXPAND}&expand[]=downloadsAllTime`).then(r => (r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status))))
    .then(m => { x.m = m; }).catch(() => { x.err = true; }).finally(() => { x.busy = !(x.files || x.ferr); done(); });
  fetch(`${HFHOST}/api/models/${enc}/tree/main?recursive=true`).then(r => (r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status))))
    .then(j => { x.files = (Array.isArray(j) ? j : []).filter(f => f.type === 'file' && /\.gguf$/i.test(f.path)); })
    .catch(() => { x.ferr = true; x.err = true; }).finally(() => { x.busy = !x.m && !x.err; done(); });
  fetch(`${HFHOST}/${enc}/resolve/main/README.md`).then(r => (r.ok ? r.text() : '')).then(t => { x.readme = t || ''; }).catch(() => { x.readme = ''; }).finally(done);
}
function fdRedraw() {
  if (FD.det && FD.el && FD.el.isConnected) {
    const top = FD.det.scrollTop;
    put(FD.det, FD.sel ? fdDetail(FD.sel) : fdDetailEmpty());
    FD.det.scrollTop = top;
  }
  if (FD.modal && !$('#modal').hidden) { const mb = $('#modalbox .mb .fd-d-wrap'); if (mb) put(mb, fdDetail(FD.modal)); }
  updateDlBars();
}
function fdDetailEmpty() {
  return h('div', { class: 'fd-empty' }, I('box', 'l'), h('div', { class: 'big' }, '모델을 고르면 자세한 정보가 여기에 보입니다'),
    h('div', { class: 'small muted' }, `크기${NB}구조${NB}다운로드 수${NB}라이선스${NB}파일마다 이 PC에 맞는지${NB}모델 설명`));
}
// README — 앞머리(YAML) · 그림 · HTML 꼬리표를 떼고 마크다운만(md 는 글을 늘 탈출해서 넣고 http(s) 링크만 만든다)
function fdReadme(text) {
  let s = String(text || '').replace(/\r\n/g, '\n');
  s = s.replace(/^---\n[\s\S]*?\n---\n/, '');
  s = s.replace(/<!--[\s\S]*?-->/g, '');
  s = s.replace(/!\[[^\]]*\]\([^)]*\)/g, '');
  s = s.replace(/<\/?[a-zA-Z][a-zA-Z0-9-]*(?:\s[^<>]*)?\/?>/g, '');
  s = s.replace(/\n{3,}/g, '\n\n').trim();
  return s.length > 16000 ? s.slice(0, 16000) + '\n\n…' : s;
}
function fdDetail(repo) {
  const st = S.st;
  const x = FD.info[repo] || {};
  const m = Object.assign({ id: repo }, FD.items.find(i => i.id === repo) || {}, x.m || {});
  const g = m.gguf || {};
  const sup = fdSupport(m);
  const cat = fdCat(repo);
  const rec = st && cat.some(c => c.id === recommendId(st));
  const lic = fdLicense(m);
  const base = asList(m.cardData && m.cardData.base_model);
  const langs = asList(m.cardData && m.cardData.language);
  const kind = kindOf({ id: repo });
  const sub = [kind, g.architecture ? `${g.architecture} 구조` : null, g.total ? `매개변수 ${fmtParams(g.total)}` : null, g.context_length ? `문맥 최대 ${fmtCtx(g.context_length)}` : null].filter(Boolean).join(NB);
  const cell = (k, v, s) => h('div', { class: 'cell' }, h('div', { class: 'k' }, k), h('div', { class: 'v' }, v), s ? h('div', { class: 's' }, s) : null);
  const head = h('div', { class: 'fd-dhead' },
    h('div', { class: 'row g8' }, h('span', { class: 'eyebrow caps' }, m.author || repo.split('/')[0]), h('span', { class: 'grow' }),
      h('a', { class: 'btn sm ghost', href: `${HFHOST}/${repo}`, target: '_blank', rel: 'noopener' }, 'Hugging Face', I('ext', 's'))),
    h('h2', { class: 'fd-title' }, hfName(repo)),
    sub ? h('div', { class: 'fd-sub' }, sub) : null,
    h('div', { class: 'fd-badges' },
      fdChecked(repo) ? h('span', { class: 'tag' }, I('shield'), 'GeulPU 확인됨') : null,
      rec ? h('span', { class: 'tag' }, I('star'), '이 PC 추천') : null,
      sup.k === 'ok' ? h('span', { class: 'tag' }, I('check'), 'GeulPU에서 실행되는 구조') : h('span', { class: 'tag dim' }, I('alert'), sup.k === 'unknown' ? '구조 정보 없음' : sup.t),
      lic ? h('span', { class: 'tag dim caps' }, lic) : null));
  const stats = h('div', { class: 'fd-stats' },
    cell('다운로드', fmtCount(m.downloads), '최근 30일'),
    cell('누적 다운로드', m.downloadsAllTime != null ? fmtCount(m.downloadsAllTime) : '-'),
    cell('좋아요', fmtCount(m.likes)),
    cell('업데이트', fmtAgo(m.lastModified), m.lastModified ? fmtDate(m.lastModified) : null));
  const hard = sup.k === 'arch' || sup.k === 'size' || sup.k === 'task';
  const note = sup.k === 'ok' ? null
    : h('div', { class: 'note-line' + (hard ? ' err' : '') }, I(hard ? 'alert' : 'info', 's'), h('span', null,
      sup.k === 'arch' ? `이 저장소의 구조(${g.architecture})는 아직 GeulPU 엔진에 없습니다. 정보는 볼 수 있지만 받을 수 없습니다.`
        : sup.why || 'Hugging Face가 이 저장소의 GGUF 구조를 알려 주지 않았습니다. 파일을 받기 전에 앞부분을 받아 확인합니다.'));
  // 파일
  let files;
  if (x.files) files = fdFiles(repo, x.files, sup, m);
  else if (x.ferr) files = h('div', { class: 'note-line err' }, I('alert', 's'), h('span', null, '파일 목록을 받지 못했습니다. 인터넷 연결을 확인한 뒤 모델을 다시 고르세요.'));
  else files = h('div', { class: 'row small muted' }, h('i', { class: 'dot busy' }), '파일 목록을 불러오는 중…');
  const info = h('div', { class: 'kv' },
    h('div', { class: 'k' }, '저장소'), h('div', { class: 'v small break' }, repo),
    h('div', { class: 'k' }, '라이선스'), h('div', { class: 'v' }, lic || '저장소에 적혀 있지 않음'),
    base.length ? [h('div', { class: 'k' }, '바탕 모델'), h('div', { class: 'v small' }, base.slice(0, 3).map((b, i) => [i ? ', ' : null, /^[\w.-]+\/[\w.-]+$/.test(b) ? h('a', { href: `${HFHOST}/${b}`, target: '_blank', rel: 'noopener' }, b) : b]), base.length > 3 ? ` 외 ${base.length - 3}개` : null)] : null,
    langs.length ? [h('div', { class: 'k' }, '언어'), h('div', { class: 'v small' }, langs.slice(0, 12).join(', ') + (langs.length > 12 ? ` 외 ${langs.length - 12}개` : ''))] : null,
    m.cardData && m.cardData.pipeline_tag ? [h('div', { class: 'k' }, '용도'), h('div', { class: 'v small' }, m.cardData.pipeline_tag)] : null,
    m.createdAt ? [h('div', { class: 'k' }, '만든 날'), h('div', { class: 'v small' }, fmtDate(m.createdAt))] : null);
  // 모델 설명(README)
  let readme = null;
  const rtext = x.readme ? fdReadme(x.readme) : '';
  if (rtext) {
    const open = !!FD.readmeOpen[repo];
    readme = h('div', { class: 'fd-sec' }, h('div', { class: 'fd-sec-t' }, '모델 설명', h('span', { class: 'grow' }), h('span', { class: 'faint small' }, 'Hugging Face의 README')),
      h('div', { class: 'md fd-readme' + (open ? ' open' : ''), html: md(rtext) }),
      h('button', { class: 'btn sm ghost', onclick: () => { FD.readmeOpen[repo] = !open; fdRedraw(); } }, I(open ? 'chevU' : 'chevD', 's'), open ? '접기' : '모두 보기'));
  } else if (x.readme === undefined && !x.err) readme = h('div', { class: 'row small muted' }, h('i', { class: 'dot busy' }), '모델 설명을 불러오는 중…');
  return h('div', { class: 'fd-d' }, head, stats, note,
    h('div', { class: 'fd-sec' }, h('div', { class: 'fd-sec-t' }, '파일', h('span', { class: 'grow' }), h('span', { class: 'faint small' }, '양자화마다 하나 — 고르면 받기 전에 실행되는지 확인')), files),
    h('div', { class: 'fd-sec' }, h('div', { class: 'fd-sec-t' }, '정보'), info),
    readme);
}
// 이 PC 에 가장 맞는 파일 — 받는 형식 가운데 메모리에 넉넉히 맞는 것 중 Q4_K_M → 가장 큰 것, 없으면 빠듯한 것 중 가장 작은 것
function fdBest(rows, sup) {
  if (sup.k === 'arch' || sup.k === 'size' || sup.k === 'task') return null;
  const ok = rows.filter(f => { const q = quantFromName(f.path); return quantOk(q) && !/-\d{5}-of-\d{5}\.gguf$/i.test(f.path); });
  const fit = f => fitOf({ size: f.size, params: '', id: '', devices: /K/.test(quantFromName(f.path)) ? 'k' : 'all' });
  const good = ok.filter(f => { const t = fit(f); return t && t.k === 'ok'; });
  if (good.length) return good.find(f => quantFromName(f.path) === 'Q4_K_M') || good.sort((a, b) => b.size - a.size)[0];
  const tight = ok.filter(f => { const t = fit(f); return t && t.k === 'tight'; }).sort((a, b) => a.size - b.size);
  return tight[0] || null;
}
function fdFiles(repo, files, sup, m) {
  if (!files.length) return h('div', { class: 'small muted' }, '이 저장소에는 GGUF 파일이 없습니다.');
  // 받을 수 있는 형식(한 파일)이 먼저 — 양자화 차례 → 큰 것부터, 받지 못하는 것은 뒤에
  const can = f => quantOk(quantFromName(f.path)) && !/-\d{5}-of-\d{5}\.gguf$/i.test(f.path);
  const rows = files.slice().sort((a, b) => (can(b) - can(a)) || qRank(quantFromName(a.path)) - qRank(quantFromName(b.path)) || b.size - a.size);
  const best = fdBest(rows, sup);
  return h('div', { class: 'fd-files' }, rows.map(f => fdFileRow(repo, f, sup, f === best, m)));
}
function fdFileRow(repo, f, sup, best, m) {
  const st = S.st;
  const q = quantFromName(f.path);
  const name = f.path.split('/').pop();
  const split = /-\d{5}-of-\d{5}\.gguf$/i.test(f.path);
  const c = fdCat(repo).find(x => (x.url || '') === `${HFHOST}/${repo}/resolve/main/${f.path}` || (x.file || '').toLowerCase() === name.toLowerCase());
  const mdl = c && c.installed ? modelOf(c.installed) : st.models.find(x => x.path && x.path.toLowerCase().endsWith('\\' + name.toLowerCase()));
  const ds = c ? dlStateOf(c) : null;
  const fit = fitOf({ size: f.size, params: '', id: repo, devices: c && c.devices ? c.devices : (/K/.test(q) ? 'k' : 'all') });
  let why = '';
  if (sup.k === 'arch') why = '지원하지 않는 구조';
  else if (sup.k === 'size') why = '아직 미지원 크기';
  else if (sup.k === 'task') why = '대화용 모델이 아님';
  else if (split) why = '여러 조각으로 나뉜 파일 — 합친 파일만 받습니다';
  else if (q && !quantOk(q)) why = `${q} 형식은 아직 미지원`;
  else if (!q) why = '양자화 형식을 알 수 없는 파일';
  else if (!c && !(f.lfs && f.lfs.oid)) why = 'SHA-256 정보가 없는 파일';
  const k = repo + '/' + f.path;
  const chk = FD.chk.get(k);
  let act = null, extra = null;
  if (mdl) act = [h('span', { class: 'tag ok' }, I('check'), '설치됨'), h('button', { class: 'btn sm needs-conn', onclick: () => chatWith(mdl.id) }, I('chat', 's'), '채팅')];
  else if (ds === 'run') extra = dlBox(c);
  else if (ds === 'pause') { act = h('button', { class: 'btn sm needs-conn', onclick: () => resumeDownload(c) }, I('download', 's'), '이어서 다운로드'); extra = dlBox(c, true); }
  else if (ds === 'fail') { act = h('button', { class: 'btn sm needs-conn', onclick: () => startDownload(c) }, I('refresh', 's'), '다시 다운로드'); extra = dlWhyLine(c.download.reason, c); }
  else if (why) act = h('span', { class: 'why' }, why);
  else if (chk && chk.state === 'checking') act = h('span', { class: 'why row g8 nowrap' }, h('i', { class: 'dot busy' }), '실행되는지 확인하는 중');
  else act = h('button', { class: 'btn sm needs-conn' + (best ? ' primary' : ''), 'data-fk': 'get:' + k, onclick: () => (c ? startDownload(c) : fdGet(repo, f, q, m)) }, I('download', 's'), '다운로드');
  if (!extra && chk && chk.state === 'bad') extra = h('div', { class: 'note-line err' }, I('alert', 's'), h('span', null, chk.why));
  const verified = c && (c.check === 'tested' || c.check === 'crosscheck');
  return h('div', { class: 'fd-file' + (why ? ' dim' : '') + (best && !mdl ? ' best' : '') },
    h('span', { class: 'qlab' }, q || '?'),
    h('span', { class: 'sz' }, fmtBytes(f.size)),
    h('span', { class: 'tags' },
      best && !mdl && !why ? h('span', { class: 'tag' }, I('star'), '이 PC에 추천') : null,
      verified ? h('span', { class: 'tag', 'data-tip': 'GeulPU에서 이 파일로 실제로 돌려 보았습니다', 'data-tip-pos': 'top' }, I('shield'), '실행 확인됨') : null,
      !why && !mdl && fit && fit.k !== 'ok' ? fitTag(fit) : null),
    h('span', { class: 'grow' }),
    act ? h('span', { class: 'act' }, act) : null,
    extra ? h('div', { class: 'ext' }, extra) : null,
    h('span', { class: 'fname small faint break' }, name));
}
// 받기 — 먼저 파일 앞부분(GGUF 머리)을 받아 이 엔진 · 이 PC 에서 실행되는지 확인하고, 되면 받을지 묻는다
async function fdGet(repo, f, q, m) {
  const k = repo + '/' + f.path;
  let s = FD.chk.get(k);
  if (!s || s.state !== 'ok') {
    FD.chk.set(k, { state: 'checking' });
    fdRedraw();
    s = await hfCheckFile(repo, f);
    FD.chk.set(k, s);
    fdRedraw();
    if (s.state !== 'ok') return;
  }
  hfDownload(m || { id: repo }, f, q, s.shape);
}
async function hfCheckFile(repo, f) {
  try {
    await api('/api/hf/check', { repo, file: f.path, size: f.size });
    for (let i = 0; i < 240; i++) {
      await new Promise(r => setTimeout(r, 400));
      const r = await api('/api/hf/check');
      if (r.state === 'done' || r.state === 'failed') {
        if (r.state === 'failed') return { state: 'bad', why: checkWhy(r.reason) };
        if (!r.shape || !r.shape.ok) return { state: 'bad', why: (r.shape && r.shape.reason) || '이 엔진이 받지 않는 파일입니다' };
        if (r.device_reason) return { state: 'bad', why: r.device_reason };
        return { state: 'ok', shape: r.shape };
      }
    }
    return { state: 'bad', why: '확인이 너무 오래 걸립니다. 잠시 뒤 다시 누르세요.' };
  } catch (e) { return { state: 'bad', why: e.message }; }
}
async function hfDownload(x, f, q, shape) {
  const st = S.st;
  const name = f.path.split('/').pop();
  const c = { size: f.size, params: (shape.params / 1e9).toFixed(1) + 'B', id: x.id };
  const fit = fitOf(c);
  const bad = fit && (fit.k === 'no' || fit.k === 'nogpu');
  const lic = fdLicense(x);
  const body = h('div', { class: 'col g16' },
    h('p', { class: 'muted m0' }, `${hfName(x.id)} ${q}${NB}${(shape.params / 1e9).toFixed(1)}B${NB}문맥 최대 ${fmtCtx(shape.context)}`),
    bad ? h('div', { class: 'note-line err' }, I('alert', 's'), h('span', null, `이 PC의 그래픽 메모리(${fmtBytes(st.device.memory)})로는 실행되지 않을 수 있습니다. 그래픽 메모리 ${vramNeed(c)} GB 이상을 권장합니다.`)) : null,
    h('div', { class: 'kv' },
      h('div', { class: 'k' }, '파일'), h('div', { class: 'v mono small break' }, name),
      h('div', { class: 'k' }, '크기'), h('div', { class: 'v' }, `${fmtBytes(f.size)} (${fmtNum(f.size)} 바이트)`),
      h('div', { class: 'k' }, '저장 위치'), h('div', { class: 'v small break' }, `${st.app.models_dir}${NB}여유 ${st.app.disk_free >= 0 ? fmtBytes(st.app.disk_free) : '알 수 없음'}`),
      h('div', { class: 'k' }, '출처'), h('div', { class: 'v small break' }, h('a', { href: `${HFHOST}/${x.id}`, target: '_blank', rel: 'noopener' }, `huggingface.co/${x.id}`)),
      h('div', { class: 'k' }, '라이선스'), h('div', { class: 'v' }, lic || '저장소에 적혀 있지 않음 — 저장소에서 확인하세요')),
    h('details', { class: 'fold' }, h('summary', null, I('chevR', 's'), '기술 정보'),
      h('div', { class: 'small mono muted break' }, `SHA-256 ${f.lfs.oid}`)),
    h('div', { class: 'note-line' }, I('info', 's'), h('span', null, '이 파일의 답 품질은 GeulPU에서 확인하지 않았습니다. 구조와 형식은 받기 전에 확인했고, 다 받으면 SHA-256으로 파일이 맞는지 확인합니다.')));
  if (!(await confirmBox('모델 다운로드', body, '다운로드', bad ? 'quiet' : null))) return;
  try {
    const r = await api('/api/hf/add', { repo: x.id, file: f.path, size: f.size, sha256: f.lfs.oid, name: hfName(x.id), quant: q, license: lic });
    await api('/api/models/download', { id: r.id });
    toast("다운로드를 시작했습니다 — 진행은 상태 막대와 '내 모델'에서 볼 수 있습니다", 'ok');
    resetSig(); refresh();
  } catch (e) { toast(e.message, 'err'); }
}
async function discardDownload(c) {
  if (!(await confirmBox('받다 만 파일 지우기', h('p', { class: 'muted m0' }, `${c.name} ${c.quant} — 지금까지 받은 ${fmtBytes((c.download && c.download.received) || 0)}를 지웁니다.${c.check === 'hf' ? ' Hugging Face에서 더한 항목이라 목록에서도 뺍니다.' : ''}`), '지우기', 'danger'))) return;
  try { await api('/api/models/discard', { id: c.id }); resetSig(); refresh(); }
  catch (e) { toast(e.message, 'err'); }
}

// ---------- 벤치마크 ----------
const BENCH = [
  { kind: 'diag', title: '하드웨어 진단', needModel: true, time: '1~6분',
    desc: '이 PC의 메모리 대역폭과 정수 연산 성능을 측정하고, 엔진의 각 연산이 하드웨어 한계에 얼마나 가까운지 보여 줍니다.' },
  { kind: 'speed', title: '속도 측정', needModel: true, time: '1~3분',
    desc: '프롬프트 처리(512 · 2048토큰)와 답 생성 속도를 토큰/초로 세 번씩 측정합니다.' },
  { kind: 'crosscheck', title: '재현성 검증', needModel: false, time: '경로마다 5~20분',
    desc: 'DeepSeek-R1-Distill-Qwen-7B Q8_0으로 수학 문제 32개를 풀어 기준 PC의 출력과 비트 단위로 비교합니다. 빌드와 커널의 해시도 함께 확인합니다.' },
];
const KIND = { '진단': ['pulse', '하드웨어 진단'], '속도': ['bolt', '속도 측정'], '교차검증': ['shield', '재현성 검증'] };
const R1_REF = 'deepseek-r1-distill-qwen-7b-q8_0';
function benchModel(runnables) {
  if (!runnables.some(m => m.id === S.benchModel)) S.benchModel = runnables.length ? runnables[0].id : '';
  return S.benchModel;
}
const isQuick = x => /빠름/.test(x.name || '') || /빠른 확인|줄인 판/.test(x.headline || '');
// 결과 요약 글에서 큰 숫자(KPI)를 — 관리자의 요약 꼴(벤치.gl)을 읽는다
function kpiFromText(kind, t) {
  const n = re => { const m = re.exec(t || ''); return m ? parseFloat(m[1]) : NaN; };
  if (kind === 'speed' || kind === '속도') {
    // 지금 꼴 "생성 60.3 토큰/초 · 프롬프트 6066 토큰/초(512토큰)", 지난 꼴 "프롬프트 512: 84.3 ms · 6070 토큰/초"
    const g = n(/생성 ([\d.]+) 토큰\/초/);
    let p = n(/프롬프트 ([\d.]+) 토큰\/초/);
    if (isNaN(p)) p = n(/프롬프트 \d+: [\d.]+ ms · ([\d.]+) 토큰\/초/);
    if (isNaN(g) && isNaN(p)) return null;
    return [isNaN(g) ? null : [fmtNum(g, 1), '생성 토큰/초'], isNaN(p) ? null : [fmtNum(p), '프롬프트 토큰/초']];
  }
  if (kind === 'diag' || kind === '진단') {
    // 한계 대비 — 새 꼴 "한계의 91%", 지난 결과의 꼴 "한계의 1.10배"(잰 시간 ÷ 한계 시간)도 읽는다
    const eff = name => { const p = n(new RegExp(name + ' 한계의 (\\d+)%')); return isNaN(p) ? effOf(n(new RegExp(name + ' 한계의 ([\\d.]+)배'))) : p; };
    const bw = n(/메모리 대역폭 ([\d.]+) GB\/s/), tops = n(/정수 텐서 ([\d.]+) TOPS/), gen = eff('생성\\(문맥 1024\\)'), pr = eff('프롬프트 2048토큰');
    if (isNaN(bw)) return null;
    return [[fmtNum(bw, 1) + ' GB/s', '메모리 대역폭'], isNaN(tops) ? null : [fmtNum(tops) + ' TOPS', '정수 텐서'],
      isNaN(gen) ? null : [fmtEff(gen), '생성 · 하드웨어 한계 대비', '한계 대비 생성'], isNaN(pr) ? null : [fmtEff(pr), '프롬프트 · 하드웨어 한계 대비', '한계 대비 프롬프트']];
  }
  return null;
}
const kpis = (items, small) => h('div', { class: 'kpis' + (small ? ' sm' : '') }, items.filter(Boolean).map(([v, l]) => h('div', { class: 'kpi' }, h('div', { class: 'v' }, v), h('div', { class: 'l' }, l))));
function renderBench() {
  const st = S.st;
  const page = $('#page-bench');
  const j0 = st.job;
  const j = j0 && (j0.state === 'running' || (['diag', 'speed', 'crosscheck'].includes(j0.kind) && jobKey(j0) !== S.jobHide)) ? j0 : null;
  const runnables = sortedModels().filter(runnable);
  const hasR1 = st.models.some(m => m.catalog === R1_REF && runnable(m));
  const sel = benchModel(runnables);
  const struct = [j && [j.id, j.state, j.kind, j.result, !!j.summary, j.reason], runnables.map(m => m.id), hasR1, sel, S.results && S.results.length];
  if (changed('bench', struct)) {
    const busy = !!(j && j.state === 'running');
    const r1c = st.catalog.find(c => c.id === R1_REF);
    rebuild(page,
      pageHead(S.results ? `결과 ${S.results.length}개` : null, '벤치마크', '한 번에 하나씩 실행됩니다. 실행하는 동안 불러온 채팅 모델은 GPU에서 내립니다. 결과는 zip으로 내보낼 수 있습니다.'),
      j ? jobCard(j) : null,
      h('div', { class: 'section bench-grid' },
        h('div', { class: 'card pick-card' },
          h('div', { class: 'pc-t' }, h('span', { class: 'lab' }, '측정할 모델'), h('span', { class: 'small muted' }, '하드웨어 진단 · 속도 측정에 씁니다')),
          h('div', { class: 'pc-c' },
            h('select', {
              class: 'input', 'data-fk': 'bench-model', 'aria-label': '하드웨어 진단 · 속도 측정에 쓸 모델', disabled: runnables.length ? null : true,
              onchange: ev => { S.benchModel = ev.target.value; store('geulpu.benchModel', S.benchModel); },
            }, runnables.length ? runnables.map(m => h('option', { value: m.id, selected: m.id === sel ? true : null }, `${displayName(m)} · ${quantOf(m)}`)) : h('option', { value: '' }, '실행할 수 있는 모델이 없습니다')),
            !runnables.length ? h('button', { class: 'btn sm', onclick: () => show('models') }, I('box', 's'), '모델 화면') : null)),
        BENCH.map(b => benchCard(b, runnables, hasR1, busy, r1c))),
      h('div', { class: 'section' }, h('div', { class: 'section-head' }, h('span', { class: 'sec' }, '최근 결과'), h('span', { class: 'grow' }),
        h('button', { class: 'icon-btn needs-conn', 'data-tip': '결과 폴더 열기', 'data-tip-pos': 'left', 'aria-label': '결과 폴더 열기', onclick: () => api('/api/open', { what: 'results' }).catch(e => toast(e.message, 'err')) }, I('folder'))),
        h('div', { id: 'results' }, S.results ? resultsTable(S.results) : h('div', { class: 'muted' }, '불러오는 중…'))));
    S.log = { job: j ? j.id : 0, from: 0 };
  }
  if (j) {
    const set = (id, v) => { const e = document.getElementById(id); if (e && e.textContent !== v) e.textContent = v; };
    set('job-step', j.state === 'running' ? (j.step || '') : { done: '끝났습니다', failed: '실패했습니다', cancelled: '중지했습니다' }[j.state] || '');
    set('job-time', `${{ running: '실행 중', done: '완료', failed: '실패', cancelled: '중지됨' }[j.state] || j.state} · ${fmtClock(j.seconds)}`);
    const bar = document.getElementById('job-bar');
    if (bar) bar.style.width = (j.state === 'done' ? 100 : j.progress / 10) + '%';
    const tail = document.getElementById('job-tail');
    if (tail) { tail.textContent = st.job_tail || ''; tail.closest('details').hidden = !st.job_tail; }
  }
  if (Date.now() - S.resultsAt > 5000) loadResults(false);
}
// 끝난 작업 카드를 닫은 기억 — 관리자를 다시 켜면 번호가 처음부터라 종류 · 결과 이름까지 묶는다
const jobKey = j => `${j.id}:${j.kind}:${j.result || ''}:${j.state}`;
const JOBSEEN = new Set();   // 실패를 이미 알린 작업
function rerun(j) {
  const id = jobModel(j);
  if ((j.kind === 'diag' || j.kind === 'speed') && id && runnable(modelOf(id))) { S.benchModel = id; store('geulpu.benchModel', id); resetSig(); renderBench(); }
  const run = document.querySelector(`.bench-card[data-kind=${j.kind}] .run`);
  if (run) run.click();
}
function jobCard(j) {
  const tone = { running: 'acc', done: 'ok', failed: 'err', cancelled: 'dim' }[j.state] || '';
  const benchDef = BENCH.find(b => b.kind === j.kind);
  const k = j.summary && j.state === 'done' ? kpiFromText(j.kind, j.summary) : null;
  const quick = j.kind === 'crosscheck' && /줄인|빠른/.test(j.title || '');
  let fail = null;
  if (j.reason && j.state !== 'done') {
    const [rt, rd] = humanJob(j.reason);
    const live = !JOBSEEN.has(jobKey(j));
    JOBSEEN.add(jobKey(j));
    fail = errorCard(rt, rd, (j.state === 'failed' || j.state === 'cancelled') && benchDef ? [h('button', { class: 'btn sm needs-conn', 'data-fk': 'rerun', onclick: () => rerun(j) }, I('refresh', 's'), '같은 설정으로 다시 실행')] : null, j.reason, live);
  }
  return h('div', { class: 'card job' },
    h('div', { class: 'head' },
      h('div', { class: 't' }, h('div', { class: 'ink h3' }, jobTitle(j)), h('div', { class: 'small muted', id: 'job-step' }, j.state === 'running' ? (j.step || '') : '')),
      h('span', { class: 'tag ' + tone, id: 'job-time' }, ''),
      j.state === 'running' ? h('button', { class: 'btn sm needs-conn', 'data-fk': 'job-stop', onclick: () => api('/api/job/cancel', {}).then(refresh).catch(e => toast(e.message, 'err')) }, I('stop', 's'), '중지')
        : h('button', { class: 'icon-btn', 'data-tip': '카드 닫기', 'data-tip-pos': 'left', 'aria-label': '끝난 작업 카드 닫기', onclick: () => { S.jobHide = jobKey(j); store('geulpu.jobHide', S.jobHide); resetSig(); renderBench(); } }, I('x', 's'))),
    h('div', { class: 'bar' + (j.state === 'done' ? ' done' : j.state === 'failed' ? ' fail' : '') }, h('i', { id: 'job-bar', style: `width:${j.state === 'done' ? 100 : j.progress / 10}%` })),
    k ? kpis(k, true) : j.summary && j.state === 'done' ? h('div', { class: 'verdict' }, (quick ? '빠른 확인 — ' : '') + pathLabel(headText(j.summary))) : null,
    fail,
    j.state === 'done' && j.result ? h('div', { class: 'row' },
      h('button', { class: 'btn sm primary', onclick: () => openResult(j.result) }, '결과 보기'),
      h('a', { class: 'btn sm', href: '/api/results/zip?name=' + encodeURIComponent(j.result) }, I('download', 's'), 'zip 내보내기')) : null,
    h('details', { class: 'fold' }, h('summary', null, I('chevR', 's'), '실행 기록'), h('pre', { class: 'log', id: 'joblog' })),
    h('details', { class: 'fold', hidden: true }, h('summary', null, I('chevR', 's'), '도구 출력'), h('pre', { class: 'log', id: 'job-tail' })));
}
function benchCard(b, runnables, hasR1, busy, r1c) {
  const extra = b.kind === 'crosscheck' ? h('div', { class: 'col g12' },
    h('label', { class: 'check' }, h('input', { type: 'checkbox', class: 'cc-quick' }), '빠른 확인 — 문제 2개 · 64토큰(전체 검증 아님)'),
    h('select', { class: 'input cc-mod', 'aria-label': '검증할 경로' }, h('option', { value: 'both' }, '모든 경로(권장)'), h('option', { value: 'coop' }, '텐서 코어 경로만'), h('option', { value: 'base' }, '기본 경로만'))) : null;
  const can = b.needModel ? runnables.length > 0 : hasR1;
  let need = null;
  if (!can && b.kind === 'crosscheck') need = h('div', { class: 'note-line' }, I('info', 's'), h('div', { class: 'col g8' }, h('span', null, 'DeepSeek-R1-Distill-Qwen-7B Q8_0 모델이 필요합니다.'),
    r1c && !r1c.installed ? h('div', null, h('button', { class: 'btn sm needs-conn', onclick: () => startDownload(r1c) }, I('download', 's'), `다운로드(${fmtBytes(r1c.size)})`)) : null));
  else if (!can) need = h('div', { class: 'note-line' }, I('info', 's'), h('span', null, '먼저 모델을 설치하세요.'));
  return h('div', { class: 'card bench-card', 'data-kind': b.kind },
    h('div', null, h('h2', null, b.title), h('div', { class: 'eyebrow' }, b.time)),
    h('p', null, b.desc), extra, need,
    h('div', null, h('button', {
      class: 'btn run needs-conn', disabled: (busy || !can) ? true : null, onclick: async ev => {
        const card = ev.target.closest('.card');
        const body = {};
        if (b.needModel) { body.model = S.benchModel; if (!body.model) return; }
        if (b.kind === 'crosscheck') { body.quick = card.querySelector('.cc-quick').checked; body.modules = card.querySelector('.cc-mod').value; }
        if (S.streaming) { toast('채팅의 답이 끝난 뒤 실행할 수 있습니다'); return; }
        if (S.st.server.state === 'ready' && !(await confirmBox('채팅 모델을 내립니다', h('p', { class: 'muted m0' }, '측정하는 동안 GPU를 혼자 쓰도록 불러온 채팅 모델을 내립니다. 계속할까요?'), '계속'))) return;
        try { await api('/api/bench/' + b.kind, body); resetSig(); refresh(); }
        catch (e) { toast(e.message, 'err'); }
      },
    }, I('play', 's'), busy ? '다른 작업 실행 중' : '실행')));
}
async function pollLog() {
  const j = S.st && S.st.job;
  if (!j || S.view !== 'bench') return;
  const pre = document.getElementById('joblog');
  if (!pre) return;
  if (S.log.job !== j.id) S.log = { job: j.id, from: 0 };
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
async function loadResults(force) {
  S.resultsAt = Date.now();
  let r;
  try { r = await api('/api/results'); } catch (_) { return; }
  if (!changed('results', r) && !force) return;
  S.results = r.results;
  put(document.getElementById('results'), resultsTable(r.results));
  if (S.view === 'bench') renderBench();
}
function stampText(s) { return String(s || '').replace(/^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})$/, '$1-$2-$3 $4:$5'); }
function headText(t) { return String(t || '').split('\n')[0].replace(/^결과(\([^)]*\))?: /, ''); }
function resultVerdict(x) {
  const t = x.headline || '';
  if (/다른 출력이 있거나|끝나지 못한/.test(t)) return ['err', '불일치'];
  if (isQuick(x) && /앞부분이 같습니다/.test(t)) return ['', '앞부분 일치'];
  if (/똑같은 출력|앞부분이 같습니다/.test(t)) return ['ok', '일치'];
  return null;
}
const resultModel = x => (x.kind === '교차검증' ? labelById(R1_REF) : x.model ? labelById(x.model) : '-');
function resultSummary(x) {
  const k = kpiFromText(x.kind, x.headline);
  if (k) return k.filter(Boolean).slice(0, 3).map(([v, l, s]) => `${s || l} ${v}`).join(NB);
  if (x.kind === '교차검증') {
    const t = headText(x.headline);
    const tail = t.includes(' — ') ? t.split(' — ').pop() : t;
    return (isQuick(x) ? '빠른 확인' + NB : '') + pathLabel(tail);
  }
  return headText(x.headline);
}
function resultsTable(rs) {
  if (!rs.length) return h('div', { class: 'empty-box' }, h('div', { class: 'big' }, '아직 결과가 없습니다'), h('div', null, '위에서 측정을 하나 실행하면 여기에 쌓입니다.'));
  // 좁아지면(≤1200) 일시를 종류 밑으로, 휴대폰(≤640)에서는 모델 · 결과까지 종류 밑으로
  return h('div', { class: 'list' }, h('table', { class: 'data results' },
    h('thead', null, h('tr', null, h('th', null, '종류'), h('th', { class: 'c-model' }, '모델'), h('th', { class: 'c-date' }, '일시'), h('th', { class: 'c-res' }, '결과'), h('th', { class: 'r' }, h('span', { class: 'sr' }, '동작')))),
    h('tbody', null, rs.map(x => {
      const k = KIND[x.kind] || ['terminal', x.kind];
      const v = x.kind === '교차검증' ? resultVerdict(x) : null;
      const sum = resultSummary(x);
      const vt = v ? h('span', { class: 'tag ' + v[0] }, v[0] === 'err' ? I('alert') : null, v[1]) : null;
      return h('tr', { class: 'clk', onclick: e => { if (!e.target.closest('a, button')) openResult(x.name); } },
        h('td', { class: 'c-kind' }, h('span', { class: 'row nowrap g12' }, I(k[0], 's'), h('span', { class: 'ink' }, k[1])),
          h('div', { class: 'mob' }, h('span', { class: 'mob-m' }, resultModel(x) + NB), h('span', { class: 'num' }, stampText(x.stamp))),
          h('div', { class: 'mob-res' }, vt ? vt.cloneNode(true) : null, h('span', null, sum))),
        h('td', { class: 'small c-model' }, resultModel(x)),
        h('td', { class: 'num small muted c-date nw' }, stampText(x.stamp)),
        h('td', { class: 'small c-res' }, h('span', { class: 'row nowrap g8' }, vt, h('span', { class: 'ell', 'data-tip': sum, 'data-tip-pos': 'top' }, sum))),
        h('td', { class: 'r nw' },
          h('button', { class: 'icon-btn', 'data-tip': '결과 보기', 'data-tip-pos': 'left', 'aria-label': '결과 보기', onclick: () => openResult(x.name) }, I('chevR')),
          h('a', { class: 'icon-btn', 'data-tip': 'zip 내보내기', 'data-tip-pos': 'left', 'aria-label': 'zip 내보내기', href: '/api/results/zip?name=' + encodeURIComponent(x.name) }, I('download'))));
    }))));
}
async function getFile(name, file) {
  const r = await fetch('/api/results/file?name=' + encodeURIComponent(name) + '&file=' + encodeURIComponent(file));
  if (!r.ok) return null;
  return file.endsWith('.json') ? r.json() : r.text();
}
// 진단 도구의 칸 이름(연구 기록의 말)을 화면의 말로
function diagLabel(k) {
  let s = String(k).replace(/여덟/g, '8').replace(/넷/g, '4');
  const alt = /\(31단계 후보\)/.test(s);
  s = s.replace(/\s*\(31단계 후보\)/, '');
  let m;
  if ((m = /^슬롯 (\d+) 걸음 문맥 (\d+)$/.exec(s))) s = `동시 ${m[1]}개 생성 · 문맥 ${m[2]}`;
  else if ((m = /^(\d+) 줄 문맥 (\d+)$/.exec(s))) s = `${m[1]}행 일괄 처리 · 문맥 ${m[2]}`;
  else if ((m = /^생성 문맥 (\d+)$/.exec(s))) s = `생성 · 문맥 ${m[1]}`;
  else if ((m = /^프롬프트 (\d+)$/.exec(s))) s = `프롬프트 ${m[1]}토큰`;
  return alt ? s + ' · 대체 커널' : s;
}
async function openResult(name) {
  modal(h('div', { class: 'muted' }, '불러오는 중…'), null, true);
  const [txt, summary, speed, diag, env] = await Promise.all([getFile(name, '결과.txt'), getFile(name, 'summary.json'), getFile(name, 'speed.json'), getFile(name, 'diag.json'), getFile(name, 'environment.json')]);
  const kind = name.split('-')[0];
  const k = KIND[kind] || ['terminal', kind];
  const stamp = (name.match(/(\d{8}-\d{6})$/) || [])[1];
  const quick = kind === '교차검증' && (/빠름/.test(name) || /빠른 확인|줄인 판/.test(txt || ''));
  const modelTxt = kind === '교차검증' ? labelById(R1_REF) : (speed && speed.model) ? labelById(speed.model) : (env && env.model) ? labelById(env.model) : '';
  const extra = speed ? ` · 동시 ${speed.slots}개 · 문맥 ${fmtCtx(speed.context)}` : '';
  const eyebrow = [k[1] + (quick ? ' · 빠른 확인(문제 2개 · 64토큰)' : ''), modelTxt + extra, stamp ? stampText(stamp) : ''].filter(Boolean).join(' · ');
  let title = headText(txt) || name;
  if (kind === '진단') title = '하드웨어 진단 결과';
  if (kind === '속도') title = '속도 측정 결과';
  const parts = [h('div', { class: 'row g8 muted' }, I(k[0], 's'), h('span', { class: 'eyebrow' }, eyebrow))];
  if (summary && summary.runs) {
    const runs = summary.runs;
    const allSame = runs.every(r => r.same === r.total && r.total > 0);
    const T = runs[0] ? runs[0].total : 0;
    const same = runs.reduce((a, r) => a + r.same, 0), tot = runs.reduce((a, r) => a + r.total, 0);
    title = quick ? (allSame ? '앞 64토큰이 기준 PC와 같습니다 — 전체 검증은 아닙니다' : '앞부분부터 기준 PC와 다릅니다')
      : (allSame ? `문제 ${T}개 모두 기준 PC와 출력이 같습니다` : '기준 PC와 출력이 다른 문제가 있습니다');
    parts.push(h('h2', { class: 'mt8' }, title),
      h('div', { class: 'res-head' },
        h('span', { class: 'big' }, allSame ? `${T}/${T}` : `${same}/${tot}`),
        h('span', { class: 'muted' }, quick ? '문제의 앞 64토큰이 같음' : allSame ? (runs.length > 1 ? `문제 · 경로 ${runs.length}개 모두 같음` : '문제가 같은 출력') : `${tot}회 중 ${same}회 일치(문제 ${T} × 경로 ${runs.length})`),
        h('span', { class: 'grow' }), h('span', { class: 'tag ' + (quick && allSame ? '' : allSame ? 'ok' : 'err') }, allSame ? null : I('alert'), quick && allSame ? '앞부분 일치' : allSame ? '일치' : '불일치')));
    for (const run of runs) {
      const items = [...(run.items || [])].sort((a, b) => (a.result === 'same') - (b.result === 'same'));
      const bad = items.filter(it => it.result !== 'same');
      const okRun = run.same === run.total;
      parts.push(h('div', { class: 'section-head mt24' }, h('span', { class: 'sec' }, pathLabel(run.label)), h('span', { class: 'grow' }),
        h('span', { class: 'tag ' + (okRun ? (quick ? '' : 'ok') : 'err') }, okRun ? null : I('alert'), `${run.same}/${run.total}`), h('span', { class: 'tag dim' }, `동시 ${run.slots}개 · ${run.generate_minutes < 1 ? '1분 미만' : run.generate_minutes + '분'}`)));
      if (run.error) parts.push(h('div', { class: 'note-line err' }, I('alert', 's'), h('span', null, run.error)));
      const table = rows => h('div', { class: 'list' }, h('table', { class: 'data' },
        h('thead', null, h('tr', null, h('th', null, '문제'), h('th', null, '판정'), h('th', { class: 'r' }, '토큰'), h('th', { class: 'r' }, '기준'), h('th', { 'data-tip': '토큰마다 로짓(점수)의 SHA-256', 'data-tip-pos': 'top' }, '단계별 해시'))),
        h('tbody', null, rows.map(it => h('tr', null, h('td', { class: 'num', 'data-tip': `파일 ${String(it.id).padStart(2, '0')}.json`, 'data-tip-pos': 'right' }, Number(it.id) + 1),
          h('td', null, h('span', { class: 'tag ' + (it.result === 'same' ? (quick ? '' : 'ok') : 'err') }, it.result === 'same' ? null : I('alert'), it.result === 'same' ? '같음' : it.result === 'different' ? `다름 · ${it.first_diff_char}번째 글자부터` : '오류')),
          h('td', { class: 'r num' }, fmtNum(it.n)), h('td', { class: 'r num muted' }, fmtNum(it.expected_n)), h('td', { class: 'mono small muted' }, (it.logit_hashes_sha256 || '').slice(0, 16)))))));
      if (bad.length) parts.push(table(bad));
      parts.push(h('details', { class: 'fold mt12' }, h('summary', null, I('chevR', 's'), bad.length ? `모든 문제 ${items.length}개 보기` : `문제 ${items.length}개 보기`), table(items)));
    }
    if (summary.build) parts.push(h('details', { class: 'fold mt16' }, h('summary', null, I('chevR', 's'), '빌드 · 커널 해시'),
      h('div', { class: 'kv' }, Object.entries(summary.build).flatMap(([kk, v]) => [h('div', { class: 'k' }, kk), h('div', { class: 'v mono small break' }, v)]))));
  } else parts.push(h('h2', { class: 'mt8' }, title));
  if (speed && speed.cells) {
    const cells = speed.cells;
    const gen = cells.find(c => c.generate > 1 && c.prompt <= 64) || cells.find(c => c.generate > 1);
    const p512 = cells.find(c => c.generate === 1 && c.prompt === 512), p2048 = cells.find(c => c.generate === 1 && c.prompt === 2048);
    parts.push(kpis([gen ? [fmtNum(gen.tokens_per_s, 1), '생성 토큰/초'] : null, p512 ? [fmtNum(p512.tokens_per_s), '프롬프트 토큰/초(512토큰)'] : null, p2048 ? [fmtNum(p2048.tokens_per_s), '프롬프트 토큰/초(2048토큰)'] : null]),
      h('div', { class: 'section-head mt24' }, h('span', { class: 'sec' }, '측정값'), h('span', { class: 'grow' }), h('span', { class: 'small muted' }, '세 번 측정한 가운데 값')),
      h('div', { class: 'list' }, h('table', { class: 'data' }, h('thead', null, h('tr', null, h('th', null, '항목'), h('th', { class: 'r' }, '프롬프트 처리'), h('th', { class: 'r' }, '토큰당 생성'), h('th', { class: 'r' }, '토큰/초'))),
        h('tbody', null, cells.map(c => h('tr', null, h('td', null, c.name),
          h('td', { class: 'r num' }, c.prompt_ms !== undefined ? fmtNum(c.prompt_ms, 1) + ' ms' : '–'),
          h('td', { class: 'r num' }, c.ms_per_token !== undefined ? fmtNum(c.ms_per_token, 2) + ' ms' : '–'),
          h('td', { class: 'r num ink' }, fmtNum(c.tokens_per_s, c.tokens_per_s < 1000 ? 1 : 0))))))));
  }
  if (diag && diag['커널']) {
    const floor = diag['바닥'] || {};
    const tops = floor['협력_TOPS'] > 0 ? floor['협력_TOPS'] : floor['정수텐서_TOPS'];
    const kk = diag['커널'];
    const gen = kk['생성 문맥 1024'], pr = kk['프롬프트 2048'];
    parts.push(kpis([floor['읽기대역_GBs'] ? [fmtNum(floor['읽기대역_GBs'], 1) + ' GB/s', '메모리 대역폭'] : null, tops ? [fmtNum(tops) + ' TOPS', '정수 텐서'] : null,
      gen ? [fmtEff(effOf(gen['배'])), '생성 · 하드웨어 한계 대비'] : null, pr ? [fmtEff(effOf(pr['배'])), '프롬프트 · 하드웨어 한계 대비'] : null]),
      h('div', { class: 'section-head mt24' }, h('span', { class: 'sec' }, '연산별 시간'), h('span', { class: 'grow' }),
        h('span', { class: 'small muted' }, '100% = 하드웨어 한계 · 높을수록 좋습니다')),
      h('div', { class: 'list' }, h('table', { class: 'data' }, h('thead', null, h('tr', null, h('th', null, '연산'), h('th', { class: 'r' }, '합계'), h('th', { class: 'r' }, '한계 대비'))),
        h('tbody', null, Object.entries(kk).map(([name, v]) => h('tr', null, h('td', { 'data-tip': /대체 커널/.test(diagLabel(name)) ? '같은 계산을 다른 방식으로 하는 후보 커널 — 비교하려고 함께 잽니다' : name !== diagLabel(name) ? '진단 도구의 이름: ' + name : null, 'data-tip-pos': 'top' }, diagLabel(name)), h('td', { class: 'r num' }, fmtNum(v['합_ms'] || 0, 2) + ' ms'),
          h('td', { class: 'r num ink nw' }, v['배'] > 0 ? [h('span', { class: 'ratio' }, h('i', { style: `width:${Math.min(100, effOf(v['배']))}%` })), fmtEff(effOf(v['배']))] : '-')))))));
  }
  if (txt && txt.split('\n').filter(Boolean).length > 1) parts.push(h('details', { class: 'fold mt16' }, h('summary', null, I('chevR', 's'), '결과.txt 원문'), h('pre', { class: 'log' }, txt)));
  modal(h('div', null, parts), [
    h('button', { class: 'btn ghost needs-conn', onclick: () => api('/api/open', { what: 'result', name }).catch(e => toast(e.message, 'err')) }, I('folder', 's'), '폴더 열기'),
    h('a', { class: 'btn', href: '/api/results/zip?name=' + encodeURIComponent(name) }, I('download', 's'), 'zip 내보내기'),
    h('button', { class: 'btn', onclick: () => closeModal() }, '닫기')], true, '.foot .btn:last-child');
}

// ---------- 하드웨어 ----------
async function renderDevice() {
  const d = S.st.device;
  if (!changed('device', d)) return;
  const page = $('#page-device');
  const cell = (k, v, s) => h('div', { class: 'cell' }, h('div', { class: 'eyebrow' }, k), h('div', { class: 'v' }, v), s ? h('div', { class: 's' }, s) : null);
  const vk = d.layer === 'vulkan';
  put(page,
    pageHead(d.layer ? `${LAYER[d.layer]} · ${fmtBytes(d.memory)}` : null, '하드웨어', null,
      [h('button', { class: 'btn needs-conn', onclick: () => api('/api/device/check', {}).then(() => { resetSig(); refresh(); }).catch(e => toast(e.message, 'err')) }, I('refresh', 's'), '다시 확인')]),
    !d.checked ? h('div', { class: 'empty-box' }, h('div', { class: 'big' }, '확인하는 중…'))
      : !d.layer ? h('div', { class: 'empty-box' }, h('div', { class: 'big' }, '쓸 수 있는 GPU를 찾지 못했습니다'), h('div', null, 'NVIDIA RTX 30 시리즈 이상(CUDA) 또는 Vulkan 1.3을 지원하는 GPU가 필요합니다.'),
        d.reason ? h('details', { class: 'fold mt16 tl' }, h('summary', null, I('chevR', 's'), '확인한 내용'), h('pre', { class: 'log sans' }, d.reason)) : null)
        : h('div', { class: 'spec' },
          cell('GPU', d.name || '-', d.vendor || ''),
          cell('백엔드', LAYER[d.layer], d.layer === 'cuda' ? 'NVIDIA 드라이버(nvcuda.dll)' : 'Vulkan 드라이버(vulkan-1.dll)'),
          cell('그래픽 메모리', fmtBytes(d.memory), 'VRAM'),
          cell('드라이버', d.driver || '-', ''),
          cell('커널', vk ? (d.variant === '공유32' ? '공유 메모리 32 KB용' : '표준') : 'CUDA용', '처음 한 번 이 GPU에 맞춰 만듭니다'),
          cell('행렬 가속', vk ? (d.coop ? `텐서 코어(${d.coop})` : '없음 — 일반 연산') : '텐서 코어(정수)', vk && !d.coop ? '텐서 코어를 쓸 수 없어 일반 연산으로 대신합니다' : '')),
    h('div', { class: 'section' }, h('div', { class: 'section-head' }, h('span', { class: 'sec' }, 'Vulkan 장치')), h('div', { id: 'dev-vk', class: 'col' })),
    h('div', { class: 'section' }, h('div', { class: 'section-head' }, h('span', { class: 'sec' }, 'CUDA 장치')), h('div', { id: 'dev-cu', class: 'col' })));
  try {
    const raw = await api('/api/device');
    const vl = raw.vulkan && raw.vulkan['장치들'] ? raw.vulkan['장치들'] : [];
    S.vk = vl.map(v => v['이름']);
    put($('#dev-vk'), vl.length ? h('div', { class: 'list' }, vl.map(v => {
      const integrated = v['종류'] === 1;
      return h('div', { class: 'item' },
        h('div', { class: 'main' }, h('div', { class: 'title' }, h('span', { class: 'nm' }, v['이름']), integrated ? h('span', { class: 'tag dim' }, '내장') : null),
          h('div', { class: 'sub' }, `Vulkan ${v['API']}${NB}드라이버 ${v['드라이버'] ? v['드라이버']['정보'] : '-'}${NB}공유 메모리 ${(v['공유메모리'] / 1024) | 0}\u00a0KB${NB}텐서 코어 ${v['권하는_협력'] || '없음'}`),
          ...(v['막는것'] || []).map(x => h('div', { class: 'sub bad' }, x))),
        h('div', { class: 'meta' }, v['고름'] && vk ? h('span', { class: 'tag' }, h('i', { class: 'dot ok' }), '사용 중') : null,
          v['돌릴수있음'] ? h('span', { class: 'tag' }, I('check'), '지원') : h('span', { class: 'tag err' }, I('alert'), '지원 안 함'),
          h('span', { class: 'num muted memv', 'data-tip': integrated ? '내장 GPU는 시스템 메모리를 나눠 씁니다' : 'Vulkan이 알려 준 장치 메모리 — 드라이버가 예약한 만큼 작게 보일 수 있습니다', 'data-tip-pos': 'left' }, (integrated ? '공유 ' : '') + fmtBytes(v['장치메모리']))));
    })) : h('div', { class: 'muted' }, '없음'));
    const cl = raw.cuda && raw.cuda.devices ? raw.cuda.devices : [];
    put($('#dev-cu'), cl.length ? h('div', { class: 'list' }, cl.map(c => h('div', { class: 'item' },
      h('div', { class: 'main' }, h('div', { class: 'title' }, h('span', { class: 'nm' }, c.name)), h('div', { class: 'sub' }, `Compute Capability ${c.cc_major}.${c.cc_minor}${NB}SM ${c.sm}개${NB}CUDA ${(raw.cuda.driver_version / 1000) | 0}.${(raw.cuda.driver_version % 1000) / 10}`)),
      h('div', { class: 'meta' }, d.layer === 'cuda' && c.ok ? h('span', { class: 'tag' }, h('i', { class: 'dot ok' }), '사용 중') : null, c.ok ? h('span', { class: 'tag' }, I('check'), '지원') : h('span', { class: 'tag err' }, I('alert'), '8.0 미만 · 지원 안 함'),
        h('span', { class: 'num muted memv' }, fmtBytes(c.memory)))))) :
      h('div', { class: 'muted' }, raw.cuda && raw.cuda.error ? raw.cuda.error : 'CUDA 없음 — NVIDIA 드라이버(nvcuda.dll)가 필요합니다'));
  } catch (_) { }
}

// ---------- 설정(바꾸면 바로 저장) ----------
async function loadVk() {
  if (S.vk) return;
  try { const raw = await api('/api/device'); S.vk = (raw.vulkan && raw.vulkan['장치들'] ? raw.vulkan['장치들'] : []).map(v => v['이름']); resetSig(); renderSettings(); } catch (_) { }
}
let setTimer = null;
// 저장되면 그 줄에 잠깐 '저장됨'(알림 창을 쌓지 않는다). 화면 읽기 프로그램에는 무엇이 언제 적용되는지까지 알린다
const SAVED = { row: '', t: 0 };
function markSaved(row, note) {
  SAVED.row = row; SAVED.t = Date.now();
  for (const e of document.querySelectorAll('#page-settings [data-saved]')) e.hidden = e.dataset.saved !== row;
  announce(note);
  setTimeout(() => { if (Date.now() - SAVED.t >= 2400) for (const e of document.querySelectorAll('#page-settings [data-saved]')) e.hidden = true; }, 2500);
}
// withDir: 모델 폴더 칸이 바뀐 때만 그 값을 보낸다(다른 칸을 바꿀 때 덜 쓴 경로가 따라가지 않게) · row: 저장됨을 보일 줄
function saveSettings(note, recheck, delay, withDir, row) {
  S.setDirty = true;
  clearTimeout(setTimer);
  setTimer = setTimeout(async () => {
    const page = $('#page-settings');
    const on = page.querySelector('.seg-ctl button.on');
    const num = (id, lo, hi, dflt) => { const v = parseInt(page.querySelector(id).value, 10); return isNaN(v) ? dflt : Math.min(hi, Math.max(lo, v)); };
    const vkSel = page.querySelector('#set-vk');
    const body = {
      gpu_layer: on ? on.dataset.v : 'auto', vulkan_device: vkSel ? vkSel.value : S.st.settings.vulkan_device || '', slots: num('#set-slots', 1, 8, 2), context: num('#set-ctx', 1024, 131072, 8192),
      update_check: page.querySelector('#set-upd').checked,
    };
    if (withDir) body.models_dir = page.querySelector('#set-mdir').value.trim();
    // 범위에 맞춘 값을 칸에도 다시 적는다(1~8 · 1024~131072)
    page.querySelector('#set-slots').value = body.slots;
    page.querySelector('#set-ctx').value = body.context;
    const errEl = page.querySelector('#set-mdir-err');
    try {
      await api('/api/settings', body);
      if (withDir && errEl) errEl.hidden = true;
      markSaved(row || '', note);
      if (recheck) await api('/api/device/check', {}).catch(e => toast(e.message, 'err'));
    } catch (e) {
      if (withDir && errEl) { put(errEl, I('alert', 's'), h('span', null, e.message)); errEl.hidden = false; }
      else toast(e.message, 'err');
    }
    S.setDirty = false;
    await refresh();   // 새 설정을 받아 온 뒤에 다시 그린다
    if (recheck) { resetSig(); renderSettings(true); }
    else if (!page.contains(document.activeElement)) { resetSig(); renderSettings(); }
  }, delay || 0);
}
function renderSettings(force) {
  const st = S.st;
  const page = $('#page-settings');
  if (!force && (S.setDirty || (page.contains(document.activeElement) && S.view === 'settings'))) return;   // 고치는 중에는 다시 그리지 않는다
  if (!changed('settings', [st.settings, st.app.version, st.app.commit, st.app.built, st.app.data_dir, st.app.models_dir, st.app.port, S.update && S.update.tag, S.vk, st.device.layer]) && !force) return;
  const focusV = force && document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.v : null;
  const s = st.settings, a = st.app;
  const NEXT = '저장했습니다 · 다음에 모델을 불러올 때 적용됩니다';
  const seg = h('div', {
    class: 'seg-ctl', role: 'radiogroup', 'aria-label': 'GPU 백엔드', onkeydown: ev => {
      if (ev.key !== 'ArrowLeft' && ev.key !== 'ArrowRight') return;
      const bs = [...ev.currentTarget.querySelectorAll('button')];
      const i = bs.findIndex(b => b.classList.contains('on'));
      const nx = bs[(i + (ev.key === 'ArrowRight' ? 1 : bs.length - 1)) % bs.length];
      ev.preventDefault();
      nx.focus();
      nx.click();
    },
  }, [['auto', '자동'], ['cuda', 'CUDA'], ['vulkan', 'Vulkan']].map(([v, t]) =>
    h('button', {
      class: v === s.gpu_layer ? 'on' : '', 'data-v': v, role: 'radio', 'aria-checked': v === s.gpu_layer ? 'true' : 'false', tabindex: v === s.gpu_layer ? '0' : '-1', onclick: ev => {
        const me = ev.currentTarget;
        if (me.classList.contains('on')) return;
        me.parentElement.querySelectorAll('button').forEach(b => { const on = b === me; b.classList.toggle('on', on); b.setAttribute('aria-checked', on ? 'true' : 'false'); b.tabIndex = on ? 0 : -1; });
        saveSettings('저장했습니다 · 하드웨어를 다시 확인합니다', true, 0, false, 'layer');
      },
    }, t)));
  const names = (S.vk || []).slice();
  if (s.vulkan_device && !names.includes(s.vulkan_device)) names.push(s.vulkan_device);
  const showVk = s.gpu_layer === 'vulkan' || (s.gpu_layer === 'auto' && st.device.layer === 'vulkan');
  const vkSel = h('select', { class: 'input', id: 'set-vk', 'aria-label': 'Vulkan 장치', onchange: () => saveSettings('저장했습니다 · 하드웨어를 다시 확인합니다', true, 0, false, 'vk') },
    h('option', { value: '' }, '자동 — 첫 번째 외장 GPU'), names.map(n => h('option', { value: n, selected: n === s.vulkan_device ? true : null }, n)));
  // 숫자 칸은 다 쓴 뒤(칸을 떠날 때 · Enter)에만 저장한다 — 쓰는 도중의 값(1 → 16 → 163 …)을 저장하지 않게
  const numIn = (id, lo, hi, step, v, label) => {
    const e = h('input', { type: 'number', id, min: String(lo), max: String(hi), step: step ? String(step) : null, value: v, 'aria-label': label });
    e.addEventListener('change', () => saveSettings(NEXT, false, 0, false, id));
    e.addEventListener('keydown', ev => { if (ev.key === 'Enter') { ev.preventDefault(); e.blur(); } });
    return e;
  };
  const slots = numIn('set-slots', 1, 8, 0, s.slots, '동시 처리 수');
  const ctx = numIn('set-ctx', 1024, 131072, 1024, s.context, '채팅마다 문맥 길이');
  const defDir = (a.data_dir || '') + '모델\\';
  const mdir = h('input', { type: 'text', id: 'set-mdir', value: s.models_dir || '', placeholder: '기본 폴더 사용', 'aria-label': '모델 폴더' });
  const commitDir = () => { if (mdir.value.trim() !== (s.models_dir || '')) saveSettings('저장했습니다 · 다음 실행부터 적용됩니다', false, 0, true, 'set-mdir'); };
  mdir.addEventListener('change', commitDir);
  mdir.addEventListener('keydown', ev => { if (ev.key === 'Enter') { ev.preventDefault(); mdir.blur(); } });
  const pickDir = h('button', { class: 'btn needs-conn', 'aria-label': '모델 폴더 찾아보기', onclick: () => browse(mdir.value.trim() || defDir, p => { mdir.value = p; commitDir(); }) }, I('folder', 's'), '찾아보기');
  const upd = h('input', { type: 'checkbox', id: 'set-upd', 'aria-label': '새 버전 알림', onchange: () => saveSettings('저장했습니다', false, 0, false, 'set-upd') });
  upd.checked = !!s.update_check;
  const savedMark = id => h('span', { class: 'saved', 'data-saved': id, hidden: !(SAVED.row === id && Date.now() - SAVED.t < 2400) }, I('check', 's'), '저장됨');
  const row = (t, d, c, extra, id) => h('div', { class: 'set-row-wrap' }, h('div', { class: 'set-row' }, h('div', { class: 'l' }, h('div', { class: 't' }, t, id ? savedMark(id) : null), d ? h('div', { class: 'd' }, d) : null),
    h('div', { class: 'c' }, c)), extra || null);
  const upTxt = S.update && S.update.tag ? (newer(S.update.tag, a.version) ? ` · 새 버전 ${S.update.tag} 있음` : ' · 최신 버전') : '';
  put(page,
    pageHead(null, '설정', '바꾼 값은 바로 저장됩니다(숫자 · 글 칸은 다 쓰고 칸을 떠날 때).'),
    h('div', { class: 'settings' },
      h('div', { class: 'sec' }, '실행'),
      h('div', { class: 'set-group' },
        row('GPU 백엔드', '자동은 NVIDIA GPU면 CUDA, 그 밖에는 Vulkan을 씁니다.', seg, null, 'layer'),
        showVk ? row('Vulkan 장치', 'GPU가 여러 개일 때 Vulkan으로 쓸 장치', vkSel, null, 'vk') : null,
        row('동시 처리 수', '동시에 답할 수 있는 채팅 수(1~8) · 다음에 모델을 불러올 때 적용', slots, null, 'set-slots'),
        row('채팅마다 문맥 길이', '토큰 · 그래픽 메모리에 맞지 않으면 엔진이 자동으로 줄입니다. 다음에 모델을 불러올 때 적용', ctx, null, 'set-ctx')),
      h('div', { class: 'sec mt16' }, '저장 위치'),
      h('div', { class: 'set-group' },
        row('모델 폴더', `다음 실행부터 적용됩니다. 기본: ${defDir}`, h('div', { class: 'row nowrap w100' }, mdir, pickDir), h('div', { class: 'set-err', id: 'set-mdir-err', hidden: true }), 'set-mdir'),
        row('데이터 폴더', h('span', { class: 'break' }, a.data_dir), h('button', { class: 'btn sm needs-conn', onclick: () => api('/api/open', { what: 'data' }).catch(e => toast(e.message, 'err')) }, I('folder', 's'), '열기'))),
      h('div', { class: 'sec mt16' }, '정보'),
      h('div', { class: 'set-group' },
        row('새 버전 알림', '앱을 열 때 GitHub에서 최신 버전 번호만 확인합니다.', h('label', { class: 'switch' }, upd, h('i')), null, 'set-upd'),
        row(`GeulPU v${a.version}`, `${a.commit ? '커밋 ' + a.commit.slice(0, 7) : '개발 빌드'}${a.built ? ' · ' + a.built.replace('T', ' ').replace('Z', ' UTC') : ''}${upTxt}`,
          h('div', { class: 'row' }, h('a', { class: 'btn sm', href: 'https://github.com/wwoosshh/GeulPU/releases', target: '_blank', rel: 'noopener' }, '릴리스', I('ext', 's')),
            h('a', { class: 'btn sm', href: 'https://github.com/wwoosshh/GeulPU', target: '_blank', rel: 'noopener' }, '소스', I('ext', 's')))),
        row('API 주소', '다른 프로그램은 OpenAI 호환 API로 쓸 수 있습니다(이 PC 안에서만).', h('div', { class: 'row nowrap' }, h('span', { class: 'mono small muted' }, `127.0.0.1:${a.port}/v1`),
          h('button', { class: 'icon-btn', 'data-tip': '주소 복사', 'data-tip-pos': 'left', 'aria-label': 'API 주소 복사', onclick: () => copyText(`http://127.0.0.1:${a.port}/v1`).then(ok => ok && toast('복사했습니다', 'ok')) }, I('copy')))))));
  if (focusV) { const b = page.querySelector(`.seg-ctl button[data-v="${focusV}"]`); if (b) b.focus(); }
}

// ---------- 시작 ----------
(async function start() {
  S.rooms = load('geulpu.rooms', []).map(r => Object.assign({ updated: r.created }, r));
  for (const r of S.rooms) for (const m of r.messages) if (m.partial) { delete m.partial; m.stopped = true; m.stats = m.stats || '중지됨'; }   // 지난번에 흐르다 끊긴 답
  S.roomId = load('geulpu.room', null);
  S.rooms = S.rooms.filter(r => r.messages.length || r.id === S.roomId);
  setConvos(overlayConvos() ? false : load('geulpu.convos', true), false);
  updateSend();
  await refresh();
  if (!curRoom()) { S.roomId = null; newRoom(); }
  renderRooms(); renderMsgs();
  renderChatTop(true);
  let v = null;
  try { v = sessionStorage.getItem('geulpu.view'); } catch (_) { }
  show(v || 'chat');
  checkUpdate();
})();
