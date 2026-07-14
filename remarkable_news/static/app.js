const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];

const messages = {
  en: {
    language: 'Language',
    runNow: 'Build edition',
    running: 'Building…',
    tabOverview: 'Overview',
    tabFeeds: 'Feeds',
    tabSettings: 'Layout & collection',
    tabIssues: 'Log',
    tabEditions: 'Editions',
    latestRuns: 'Latest runs',
    refresh: 'Refresh',
    newFeed: 'New feed',
    feedName: 'Name',
    feedUrl: 'RSS URL',
    add: 'Add',
    feeds: 'Feeds',
    scheduleVolume: 'Schedule & volume',
    automaticCollection: 'Automatic collection',
    intervalMinutes: 'Interval, minutes',
    itemsPerFeed: 'Items per feed',
    lookbackHours: 'Look back, hours',
    articlesPerEdition: 'Articles per edition',
    retentionDays: 'Keep editions, days',
    textReliability: 'Text reliability',
    preferFullArticle: 'Try to extract full articles',
    minimumContent: 'Minimum useful characters',
    requestTimeout: 'Site timeout, seconds',
    retryAttempts: 'Retry attempts',
    retryBase: 'First retry delay, minutes',
    createEmptyEditions: 'Create editions without new articles',
    printLayout: 'Print layout',
    editionTitle: 'Edition title',
    paperSize: 'Paper size',
    fontSize: 'Font size, pt',
    lineHeight: 'Line height',
    pageMargins: 'Page margins, mm',
    articlePageBreak: 'Start each article on a new page',
    imagesCaptions: 'Images & captions',
    includeImages: 'Include images',
    maxImageBytes: 'Max bytes per image',
    showSource: 'Show source',
    showDate: 'Show date',
    showLinks: 'Print links',
    saveSettings: 'Save settings',
    connection: 'Connection',
    remarkableConnectHelp: 'Open the reMarkable page, get a one-time code, and paste it below.',
    getOneTimeCode: 'Get one-time code ↗',
    oneTimeCode: 'One-time code',
    connect: 'Connect',
    checkingCloud: 'Checking cloud…',
    testConnection: 'Test connection',
    resetTokens: 'Reset tokens',
    delivery: 'Delivery',
    autoSend: 'Automatically send editions',
    tabletFolder: 'Folder on tablet',
    overwriteSameName: 'Overwrite file with the same name',
    save: 'Save',
    issuesWarnings: 'Issues & warnings',
    retryFailedUrls: 'Retry failed URLs',
    savedPdfs: 'Saved PDFs',
    empty: 'Nothing here yet',
    requestFailed: 'Request failed',
    activeFeeds: 'Active feeds',
    pending: 'Queued',
    dead: 'Failed permanently',
    openIssues: 'Open issues',
    pdfEditions: 'PDF editions',
    start: 'Start',
    trigger: 'Trigger',
    status: 'Status',
    feedColumn: 'Feeds',
    articles: 'Articles',
    pdf: 'PDF',
    enabled: 'On',
    nameAndUrl: 'Name and URL',
    lastCheck: 'Last check',
    state: 'State',
    delete: 'Delete',
    feedUpdated: 'Feed updated',
    deleteFeedConfirm: 'Delete this feed and related articles?',
    dateWhen: 'When',
    kind: 'Type',
    source: 'Source',
    message: 'Message',
    resolve: 'Close',
    created: 'Created',
    file: 'File',
    action: 'Actions',
    download: 'Download',
    uploadToTablet: 'To tablet',
    sent: 'Sent',
    rmapiError: 'rmapi returned an error',
    configured: 'Configuration found',
    notConnected: 'Not connected yet',
    feedAdded: 'Feed added',
    settingsSaved: 'Settings saved',
    deliverySaved: 'Delivery configured',
    runStarted: 'Build started',
    queuedBack: 'Returned to queue:',
    connectedVerified: 'reMarkable connected and verified',
    authFailed: 'Authorization was not completed',
    connectionWorks: 'Connection works',
    connectionFailed: 'Connection check failed',
    resetConfirm: 'Delete local rmapi tokens? You will need a new one-time code.',
    tokensDeleted: 'Tokens deleted. Get a new one-time code.',
    connectionReset: 'Connection reset',
  },
  ru: {
    language: 'Язык',
    runNow: 'Собрать выпуск',
    running: 'Идёт сбор…',
    tabOverview: 'Обзор',
    tabFeeds: 'Подписки',
    tabSettings: 'Оформление и сбор',
    tabIssues: 'Журнал',
    tabEditions: 'Выпуски',
    latestRuns: 'Последние запуски',
    refresh: 'Обновить',
    newFeed: 'Новая подписка',
    feedName: 'Название',
    feedUrl: 'Адрес RSS',
    add: 'Добавить',
    feeds: 'Подписки',
    scheduleVolume: 'Расписание и объём',
    automaticCollection: 'Автоматический сбор',
    intervalMinutes: 'Интервал, минут',
    itemsPerFeed: 'Записей из одной ленты',
    lookbackHours: 'Искать материалы за последние часы',
    articlesPerEdition: 'Материалов в одном выпуске',
    retentionDays: 'Хранить выпуски, дней',
    textReliability: 'Надёжность текста',
    preferFullArticle: 'Пытаться извлечь полный текст',
    minimumContent: 'Минимум полезных символов',
    requestTimeout: 'Таймаут сайта, секунд',
    retryAttempts: 'Количество попыток',
    retryBase: 'Первая повторная попытка, минут',
    createEmptyEditions: 'Создавать выпуск без новых статей',
    printLayout: 'Печатный вид',
    editionTitle: 'Название выпуска',
    paperSize: 'Формат бумаги',
    fontSize: 'Размер текста, pt',
    lineHeight: 'Межстрочный интервал',
    pageMargins: 'Поля, мм',
    articlePageBreak: 'Каждая статья с новой страницы',
    imagesCaptions: 'Изображения и подписи',
    includeImages: 'Включать изображения',
    maxImageBytes: 'Максимум на изображение, байт',
    showSource: 'Показывать источник',
    showDate: 'Показывать дату',
    showLinks: 'Печатать ссылки',
    saveSettings: 'Сохранить настройки',
    connection: 'Подключение',
    remarkableConnectHelp: 'Откройте страницу reMarkable, получите одноразовый код и вставьте его ниже.',
    getOneTimeCode: 'Получить одноразовый код ↗',
    oneTimeCode: 'Одноразовый код',
    connect: 'Подключить',
    checkingCloud: 'Проверяю облако…',
    testConnection: 'Проверить подключение',
    resetTokens: 'Сбросить токены',
    delivery: 'Доставка',
    autoSend: 'Автоматически отправлять выпуски',
    tabletFolder: 'Папка на планшете',
    overwriteSameName: 'Заменять файл с тем же именем',
    save: 'Сохранить',
    issuesWarnings: 'Ошибки и предупреждения',
    retryFailedUrls: 'Повторить неудачные URL',
    savedPdfs: 'Сохранённые PDF',
    empty: 'Пока пусто',
    requestFailed: 'Ошибка запроса',
    activeFeeds: 'Активных лент',
    pending: 'В очереди',
    dead: 'Не удалось',
    openIssues: 'Открытых ошибок',
    pdfEditions: 'PDF выпусков',
    start: 'Начало',
    trigger: 'Причина',
    status: 'Статус',
    feedColumn: 'Ленты',
    articles: 'Статьи',
    pdf: 'PDF',
    enabled: 'Вкл.',
    nameAndUrl: 'Название и URL',
    lastCheck: 'Последняя проверка',
    state: 'Состояние',
    delete: 'Удалить',
    feedUpdated: 'Подписка обновлена',
    deleteFeedConfirm: 'Удалить подписку и связанные с ней статьи?',
    dateWhen: 'Когда',
    kind: 'Тип',
    source: 'Источник',
    message: 'Сообщение',
    resolve: 'Закрыть',
    created: 'Создан',
    file: 'Файл',
    action: 'Действия',
    download: 'Скачать',
    uploadToTablet: 'На планшет',
    sent: 'Отправлено',
    rmapiError: 'rmapi вернул ошибку',
    configured: 'Конфигурация найдена',
    notConnected: 'Ещё не подключено',
    feedAdded: 'Подписка добавлена',
    settingsSaved: 'Настройки сохранены',
    deliverySaved: 'Доставка настроена',
    runStarted: 'Сбор запущен',
    queuedBack: 'В очередь возвращено:',
    connectedVerified: 'reMarkable подключён и проверен',
    authFailed: 'Авторизация не завершена',
    connectionWorks: 'Подключение работает',
    connectionFailed: 'Проверка не пройдена',
    resetConfirm: 'Удалить локальные токены rmapi? После этого потребуется новый одноразовый код.',
    tokensDeleted: 'Токены удалены. Получите новый одноразовый код.',
    connectionReset: 'Подключение сброшено',
  },
};

let settings = {};
let lang = localStorage.getItem('language') || 'en';

function t(key) {
  if (!messages[lang]) lang = 'en';
  return messages[lang][key] || messages.en[key] || key;
}

function applyLanguage() {
  document.documentElement.lang = lang;
  $('#language-select').value = lang;
  $$('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
}

function toast(message, error=false) {
  const el = $('#toast'); el.textContent = message; el.className = `show${error?' error':''}`;
  clearTimeout(el.timer); el.timer = setTimeout(() => el.className='', 3500);
}

async function api(path, options={}) {
  const response = await fetch(path, {headers:{'Content-Type':'application/json', ...(options.headers||{})}, ...options});
  if (!response.ok) {
    let detail;
    try { detail=(await response.json()).detail; } catch { detail=response.statusText; }
    throw new Error(detail || t('requestFailed'));
  }
  return response.status===204 ? null : response.json();
}

const esc = value => String(value??'').replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const date = value => value ? new Date(value).toLocaleString(lang === 'ru' ? 'ru-RU' : 'en-US') : '—';
const pill = value => `<span class="pill ${esc(value)}">${esc(value)}</span>`;
function table(headers, body) {
  return body.length ? `<table><thead><tr>${headers.map(x=>`<th>${x}</th>`).join('')}</tr></thead><tbody>${body.join('')}</tbody></table>` : `<div class="empty">${t('empty')}</div>`;
}

async function loadDashboard() {
  const data = await api('/api/dashboard');
  const labels={feeds:t('activeFeeds'),pending:t('pending'),dead:t('dead'),open_issues:t('openIssues'),editions:t('pdfEditions')};
  $('#stats').innerHTML=Object.entries(data.counts).map(([k,v])=>`<div class="stat"><strong>${v}</strong><span>${labels[k]}</span></div>`).join('');
  $('#runs').innerHTML=table([t('start'),t('trigger'),t('status'),t('feedColumn'),t('articles'),t('pdf')],data.runs.map(r=>`<tr><td>${date(r.started_at)}</td><td>${esc(r.trigger)}</td><td>${pill(r.status)}</td><td>${r.feeds_ok} / <span class="bad">${r.feeds_failed}</span></td><td>${r.articles_ready} / ${r.articles_failed}</td><td>${r.edition_id??'—'}</td></tr>`));
  $('#run-now').disabled=data.running; $('#run-now').textContent=data.running?t('running'):t('runNow');
  $('#rmapi-state').textContent=data.rmapi.configured?t('configured'):t('notConnected');
}

async function loadFeeds() {
  const data=await api('/api/feeds');
  $('#feed-list').innerHTML=table([t('enabled'),t('nameAndUrl'),t('lastCheck'),t('state'),''],data.map(f=>`<tr><td><input type="checkbox" data-feed-toggle="${f.id}" ${f.enabled?'checked':''}></td><td><strong>${esc(f.name)}</strong><div class="url">${esc(f.url)}</div></td><td>${date(f.last_checked_at)}</td><td>${f.last_error?`<span title="${esc(f.last_error)}">⚠ ${esc(f.last_error.slice(0,90))}</span>`:'✓'}</td><td><button class="danger" data-feed-delete="${f.id}">${t('delete')}</button></td></tr>`));
  $$('[data-feed-toggle]').forEach(el=>el.onchange=async()=>{ const f=data.find(x=>x.id===+el.dataset.feedToggle); await api(`/api/feeds/${f.id}`,{method:'PATCH',body:JSON.stringify({name:f.name,url:f.url,enabled:el.checked})}); toast(t('feedUpdated')); });
  $$('[data-feed-delete]').forEach(el=>el.onclick=async()=>{ if(!confirm(t('deleteFeedConfirm')))return; await api(`/api/feeds/${el.dataset.feedDelete}`,{method:'DELETE'}); loadFeeds(); });
}

function fillForm(form, names) {
  names.forEach(name=>{ const el=form.elements[name]; if(!el)return; if(el.type==='checkbox')el.checked=!!settings[name]; else el.value=settings[name]??''; });
}

async function loadSettings() {
  settings=await api('/api/settings');
  fillForm($('#settings-form'), Object.keys(settings));
  fillForm($('#remarkable-form'), ['remarkable_enabled','remarkable_folder','remarkable_force_overwrite']);
}

function formSettings(form) {
  const out={};
  $$('input,select',form).forEach(el=>{ if(!el.name)return; out[el.name]=el.type==='checkbox'?el.checked:el.type==='number'?Number(el.value):el.value; });
  return out;
}

async function loadIssues() {
  const data=await api('/api/issues');
  $('#issue-list').innerHTML=table([t('dateWhen'),t('kind'),t('source'),t('message'),''],data.map(i=>`<tr><td>${date(i.created_at)}</td><td>${pill(i.kind)}</td><td>${esc(i.feed_name||'—')}<div class="url">${esc(i.url||'')}</div></td><td>${esc(i.message)}</td><td><button class="ghost" data-resolve="${i.id}">${t('resolve')}</button></td></tr>`));
  $$('[data-resolve]').forEach(el=>el.onclick=async()=>{ await api(`/api/issues/${el.dataset.resolve}/resolve`,{method:'POST'}); loadIssues(); });
}

async function loadEditions() {
  const data=await api('/api/editions');
  $('#edition-list').innerHTML=table([t('created'),t('file'),t('status'),t('articles'),t('action')],data.map(e=>`<tr><td>${date(e.created_at)}</td><td>${esc(e.filename)}</td><td>${pill(e.status)}${e.upload_error?`<div class="url">${esc(e.upload_error)}</div>`:''}</td><td>${e.article_count}</td><td><a href="/api/editions/${e.id}/download">${t('download')}</a> · <button class="ghost" data-upload="${e.id}">${t('uploadToTablet')}</button></td></tr>`));
  $$('[data-upload]').forEach(el=>el.onclick=async()=>{ el.disabled=true; try { const r=await api(`/api/editions/${el.dataset.upload}/upload`,{method:'POST'}); toast(r.success?t('sent'):t('rmapiError'),!r.success); loadEditions(); } finally {el.disabled=false;} });
}

async function refresh() {
  applyLanguage();
  try { await Promise.all([loadDashboard(),loadFeeds(),loadSettings(),loadIssues(),loadEditions()]); } catch(e) {toast(e.message,true);}
}

$$('nav button').forEach(button=>button.onclick=()=>{ $$('nav button,.tab').forEach(x=>x.classList.remove('active')); button.classList.add('active'); $(`#${button.dataset.tab}`).classList.add('active'); });
$$('.refresh').forEach(b=>b.onclick=refresh);
$('#language-select').onchange=async e=>{ lang=e.target.value; localStorage.setItem('language', lang); await refresh(); };
$('#feed-form').onsubmit=async e=>{ e.preventDefault(); const f=new FormData(e.target); try { await api('/api/feeds',{method:'POST',body:JSON.stringify({name:f.get('name'),url:f.get('url'),enabled:true})}); e.target.reset(); toast(t('feedAdded')); loadFeeds(); } catch(err){toast(err.message,true);} };
$('#settings-form').onsubmit=async e=>{ e.preventDefault(); try { settings=await api('/api/settings',{method:'PUT',body:JSON.stringify({values:formSettings(e.target)})}); toast(t('settingsSaved')); }catch(err){toast(err.message,true);} };
$('#remarkable-form').onsubmit=async e=>{ e.preventDefault(); try { settings=await api('/api/settings',{method:'PUT',body:JSON.stringify({values:formSettings(e.target)})}); toast(t('deliverySaved')); }catch(err){toast(err.message,true);} };
$('#run-now').onclick=async()=>{ try { await api('/api/runs',{method:'POST'}); toast(t('runStarted')); setTimeout(loadDashboard,800); }catch(e){toast(e.message,true);} };
$('#retry-all').onclick=async()=>{ const r=await api('/api/articles/retry',{method:'POST'}); toast(`${t('queuedBack')} ${r.queued}`); };
$('#auth-form').onsubmit=async e=>{ e.preventDefault(); const code=new FormData(e.target).get('code'); const button=e.target.querySelector('button'); button.disabled=true; button.textContent=t('checkingCloud'); try { await api('/api/rmapi/authorize',{method:'POST',body:JSON.stringify({code})}); $('#rmapi-output').textContent=t('connectedVerified'); e.target.reset(); toast(t('connectedVerified')); loadDashboard(); }catch(err){ $('#rmapi-output').textContent=err.message; toast(t('authFailed'),true); } finally { button.disabled=false; button.textContent=t('connect'); } };
$('#test-rmapi').onclick=async()=>{ try { const r=await api('/api/rmapi/test',{method:'POST'}); $('#rmapi-output').textContent=r.success?t('connectionWorks'):r.output; toast(r.success?t('connectionWorks'):t('connectionFailed'),!r.success); }catch(e){toast(e.message,true);} };
$('#reset-rmapi').onclick=async()=>{ if(!confirm(t('resetConfirm')))return; try { await api('/api/rmapi/reset',{method:'POST'}); $('#rmapi-output').textContent=t('tokensDeleted'); toast(t('connectionReset')); loadDashboard(); }catch(e){toast(e.message,true);} };

applyLanguage();
refresh();
setInterval(loadDashboard,10000);
