// // static\client.js

import * as utils from './utils.js';
import * as geo from './geo-and-session.js';
import * as ui from './ui-and-screens.js';





// const API_ROOT = "";
// const DEFAULT_TAGS = [
//     "бизнес", "IT", "стартапы", "AI", "программирование","веб","frontend",
//     "backend","data-science","машинное обучение","дизайн","фотография",
//     "спорт","фитнес","йога","путешествия","еда","кофе","кино",
//     "музыка","книги","игры","технологии","стартап-менеджмент","маркетинг"
// ];

// const reactions = [
//     { emoji: "🙂", label: "Приятный собеседник" },
//     { emoji: "🧠", label: "Мыслит нестандартно" },
//     { emoji: "🤝", label: "Крутой нетворкер" },
//     { emoji: "🔥", label: "Любит свое дело" },
//     { emoji: "⚡", label: "Позитивный и энергичный" },
// ];

// async function fetchReviewsFor(tg_id, viewer_tg_id = null) {
//     const q = new URLSearchParams({ tg_id: String(tg_id) });
//     if (viewer_tg_id) q.set("viewer_tg_id", String(viewer_tg_id));
//     const res = await fetch(`/api/reviews?${q.toString()}`, { cache: "no-store" });
//     if (!res.ok) throw new Error("fetch reviews failed");
//     return res.json();
// }

// function renderRecentReviews(container, recent) {
//     container.innerHTML = "";
//     for (const r of recent) {
//         const el = document.createElement("div");
//         el.className = "recent-full";
//         el.innerHTML = `
//             <img class="mini-avatar" src="${r.reviewer_avatar || '/static/images/default_avatar.svg'}" onerror="this.src='/static/images/default_avatar.svg'"/>
//             <div class="rf-body"><div class="rf-name">${escapeHtml(r.reviewer_name || r.reviewer_tg)}</div>
//             <div class="rf-meta">${escapeHtml(r.reaction)} · ${escapeHtml(r.created_at)}</div>
//             <div class="rf-comment">${escapeHtml(r.comment || '')}</div></div>
//         `;
//         container.appendChild(el);
//     }
// }


// // --- Tag modal helpers ---
// async function openTagModal(existingTags = [], user = null) {
//     const modal = $qs("#tagModal");
//     if (!modal) return;
//     if (!document.body.contains(modal)) document.body.appendChild(modal);

//     const list = $qs("#tagModalList");
//     list.innerHTML = "";

//     // нормализуем выбранные теги (из caller / сервер)
//     const selected = new Set((existingTags || []).map(t => String(t || "").toLowerCase().trim()).filter(Boolean));
//     const existingNorm = Array.from(selected); // массив уникальных выбранных

//     // Берём популярные теги из DEFAULT_TAGS (без запроса к бэку)
//     const availNorm = DEFAULT_TAGS.map(t => String(t).toLowerCase().trim()).filter(Boolean);

//     // helper для создания кнопки тега
//     const createTagButton = (t) => {
//         const btn = document.createElement("button");
//         btn.type = "button";
//         btn.className = "tag" + (selected.has(t) ? " selected" : "");
//         btn.dataset.value = t;
//         btn.textContent = t[0] ? (t[0].toUpperCase() + t.slice(1)) : t;
//         btn.addEventListener("click", (e) => {
//             e.preventDefault();
//             if (btn.classList.contains("selected")) {
//                 btn.classList.remove("selected");
//                 selected.delete(t);
//             } else {
//                 btn.classList.add("selected");
//                 selected.add(t);
//             }
//         });
//         return btn;
//     };

//     // 1) отрисуем популярные теги в первой секции
//     const popularWrap = document.createElement("div");
//     popularWrap.className = "tag-section popular";
//     const popTitle = document.createElement("div");
//     popTitle.className = "tag-section-title";
//     popTitle.textContent = "Популярные";
//     popularWrap.appendChild(popTitle);

//     for (const t of availNorm) {
//         popularWrap.appendChild(createTagButton(t));
//     }
//     list.appendChild(popularWrap);

//     // 2) отрисуем дополнительные пользовательские теги, которых нет в популярных
//     const extras = existingNorm.filter(t => !availNorm.includes(t));
//     if (extras.length) {
//         const yourWrap = document.createElement("div");
//         yourWrap.className = "tag-section yours";
//         const yourTitle = document.createElement("div");
//         yourTitle.className = "tag-section-title";
//         yourTitle.textContent = "Ваши теги";
//         yourWrap.appendChild(yourTitle);
//         for (const t of extras) {
//             yourWrap.appendChild(createTagButton(t));
//         }
//         list.appendChild(yourWrap);
//     }

//     // 3) если нет ни одного тега (крайний случай) - покажем подсказку
//     if (availNorm.length === 0 && extras.length === 0) {
//         const hint = document.createElement("div");
//         hint.className = "muted";
//         hint.textContent = "Нет доступных тегов - добавьте свой.";
//         list.appendChild(hint);
//     }

//     // show modal
//     modal.classList.remove("hidden");
//     modal.setAttribute("aria-hidden", "false");

//     // focus - делаем после рендера
//     setTimeout(() => {
//         const first = list.querySelector(".tag") || $qs("#tagModalSave");
//         if (first && typeof first.focus === "function") first.focus();
//     }, 20);

//     // keyboard handlers
//     function onKey(e) {
//         if (e.key === "Escape") { e.preventDefault(); closeTagModal(); }
//         if (e.key === "Enter" && (document.activeElement && document.activeElement.classList.contains("tag"))) {
//             document.activeElement.click();
//         }
//     }
//     document.addEventListener("keydown", onKey);

//     // click handlers
//     const cancel = $qs("#tagModalCancel");
//     const save = $qs("#tagModalSave");
//     const overlay = modal.querySelector(".modal-overlay");

//     const cleanupHandlers = () => {
//         document.removeEventListener("keydown", onKey);
//         if (cancel) cancel.onclick = null;
//         if (save) save.onclick = null;
//         if (overlay) overlay.onclick = null;
//     };
//     const closeAndCleanup = () => { closeTagModal(); cleanupHandlers(); };
//     if (cancel) cancel.onclick = closeAndCleanup;
//     if (overlay) overlay.onclick = closeAndCleanup;

//     save.onclick = async () => {
//         const picked = Array.from(list.querySelectorAll(".tag.selected"))
//             .map(n => (n.dataset.value || n.textContent || "").toString().trim().toLowerCase().replace(/\s+/g, ' '))
//             .filter(Boolean);
//         const tg_id = getTgId();
//         if (!tg_id) { alert("Авторизуйтесь через Telegram для сохранения"); return; }
//         try {
//             const resp = await postJson("/api/profile/tags", { tg_id, tags: picked });
//             if (!resp || !resp.ok) throw new Error("save failed");
//             closeAndCleanup();
//             runScreenInit("profile"); // обновим профиль
//         } catch (err) {
//             console.error("save tags failed", err);
//             alert("Ошибка сохранения: " + (err.message || err));
//         }
//     };
// }

// // close function
// function closeTagModal() {
//     const modal = $qs("#tagModal");
//     if (!modal) return;
//     modal.classList.add("hidden");
//     modal.setAttribute("aria-hidden","true");
//     const list = $qs("#tagModalList");
//     if (list) list.innerHTML = "";
// }

// // Получить список популярных тегов: {ok:true, tags:[{tag, count},...]}
// async function fetchAvailableTags(limit = 50) {
//     try {
//         const res = await fetch(`/api/tags?limit=${encodeURIComponent(limit)}`, { cache: "no-store" });
//         if (res.ok) {
//             const data = await res.json();
//             if (data && Array.isArray(data.tags) && data.tags.length) {
//                 return data.tags.map(it => ({ tag: String(it.tag || "").toLowerCase(), count: Number(it.count || 0) }));
//             }
//         }
//     } catch (e) {
//         console.warn("fetchAvailableTags failed, will use DEFAULT_TAGS", e);
//     }
//     return DEFAULT_TAGS.map(t => ({ tag: String(t).toLowerCase(), count: 0 }));
// }


// // --- radar rings helpers ---
// function startRadarRings(count = 3) {
//     const el = getEatCircle();
//     if (!el) return;

//     // уже запущено - ничего не делаем
//     if (el._radarActive) return;
//     el._radarActive = true;
//     el._radarRings = [];

//     const duration = 2000; // ms (соответствует CSS animation-duration)
//     const gap = duration / count; // stagger

//     for (let i = 0; i < count; i++) {
//         const r = document.createElement("div");
//         r.className = "radar-ring ring-" + i;
//         r.style.setProperty("--radar-delay", (i * (gap / 1000)).toFixed(3) + "s");
//         r.style.animationDuration = duration + "ms";
//         el.appendChild(r);
//         el._radarRings.push(r);
//     }
// }

// function stopRadarRings() {
//     const el = getEatCircle();
//     if (!el || !el._radarActive) return;
    
//     // Удаляем элементы через requestAnimationFrame для плавного ухода (и чтобы не дергать layout)
//     const rings = el._radarRings || [];
//     for (const r of rings) {
//         try { r.style.transition = "opacity 250ms linear"; r.style.opacity = "0"; } catch(e){}
//         setTimeout(() => { try { r.remove(); } catch(e){} }, 300);
//     }
//     el._radarRings = null;
//     el._radarActive = false;
// }


// // --- UI helpers для share/status ---
// function hideShareButton() {
//     const b = $qs("#shareGeoBtn");
//     if (b) b.classList.remove("visible"), b.classList.add("hidden");
// }
// function showShareButton() {
//     const b = $qs("#shareGeoBtn");
//     if (b) b.classList.remove("hidden");
// }

// // --- helper: показ подсказки под кружком ---
// function showEatHint(text) {
//     const el = $qs("#eatHint");
//     if (!el) return;
//     el.textContent = text || "";
//     el.classList.remove("hidden");
// }
// function hideEatHint() {
//     const el = $qs("#eatHint");
//     if (!el) return;
//     el.classList.add("hidden");
// }

// // --- helper: промисифицированный getCurrentPosition ---
// function getCurrentPositionPromise(options = { enableHighAccuracy: true, maximumAge: 0, timeout: 10000 }) {
//     return new Promise((resolve, reject) => {
//         if (!navigator.geolocation) return reject(new Error("Geolocation not supported"));
//         navigator.geolocation.getCurrentPosition(pos => resolve(pos), err => reject(err), options);
//     });
// }

// // --- helper: sleep с рандомом 3-5 сек ---
// function sleep(ms) { 
//     return new Promise(r => setTimeout(r, ms)); 
// }
// function randomDelayMs(min = 3000, max = 5000) {
//     return Math.floor(min + Math.random() * (max - min + 1));
// }

// async function startEatingWithDelay() {
//     // проверяем tg_id / авторизацию как в startEating
//     const rawInit = window.Telegram?.WebApp?.initData ?? null;
//     const initData = rawInit ? rawInit : buildInitDataObject();

//     let verified;
//     if (initData) {
//         verified = await verifyInitData(initData);
//     } else {
//         const saved = localStorage.getItem("meeteat_tg_id");
//         if (saved) verified = { ok: true, tg_id: Number(saved) };
//         else {
//             alert("Откройте приложение через Telegram, либо сохраните tg_id для теста.");
//             return;
//         }
//     }
//     if (!verified.ok) { alert("Auth failed"); return; }
//     const tg_id = verified.tg_id;
//     saveTgId(tg_id);

//     // UI: показываем что ищем
//     setEatCircleSearching(true);
//     showEatHint("Ищем людей поблизости…");

//     // параллельно: геопозиция и искусственная задержка
//     const delayMs = randomDelayMs(3000, 5000);
//     const delayP = sleep(delayMs);
//     const posP = getCurrentPositionPromise({ enableHighAccuracy: true, maximumAge: 0, timeout: 10000 });

//     let pos;
//     try {
//         // ждём обе операции: геопозиция и задержку
//         const [position] = await Promise.all([ posP.catch(e => { throw e; }), delayP ]);
//         pos = position;
//     } catch (geoErr) {
//         console.warn("geo error during delayed start", geoErr);
//         setEatCircleSearching(false);
//         showEatHint("Нажми на кнопку, чтобы найти людей рядом");
//         if (geoErr && geoErr.code === 1) alert("Доступ к геопозиции запрещён пользователем.");
//         else if (geoErr && geoErr.code === 3) alert("Таймаут получения геопозиции. Попробуйте снова.");
//         else alert("Не удалось получить геопозицию: " + (geoErr.message || geoErr));
//         return;
//     }

//     // если получили позицию - отправляем /start и запускаем nearby
//     try {
//         const body = { tg_id, lat: pos.coords.latitude, lon: pos.coords.longitude };
//         const data = await postJson("/start", body);

//         // render nearby
//         await fetchNearbyAndRender(tg_id, body.lat, body.lon);

//         // запустить таймер и UI
//         showEatStatus(data.expires_at);
//         showTimerAndUi(data.expires_at);
//         startUpdateLoop(tg_id);
//         setEatCircleActive(true);

//         // подсказку скрываем (eatStatus появится)
//         hideEatHint();
//     } catch (e) {
//         console.error("startWithDelay failed", e);
//         alert("Ошибка при запуске: " + (e.message || e));
//         setEatCircleSearching(false);
//         showEatHint("Нажми на кнопку, чтобы найти людей рядом");
//     } finally {
//         // если по каким-то причинам searching ещё включен - выключим (active держит анимацию)
//         setEatCircleSearching(false);
//     }
// }


// // показать/скрыть eat-status
// let eatStatusIntervalId = null;
// function showEatStatus(expires_iso) {
//     const el = $qs("#eatStatus");
//     const timerEl = $qs("#eatStatusTimer");
//     if (!el || !timerEl) return;

//     // прячем кнопку
//     hideShareButton();
//     el.classList.remove("hidden");

//     // очищаем старый интервал
//     if (eatStatusIntervalId) {
//         clearInterval(eatStatusIntervalId);
//         eatStatusIntervalId = null;
//     }

//     function tick() {
//         const expires = new Date(expires_iso);
//         const rem = Math.max(0, expires - new Date());
//         const mins = Math.floor(rem / 60000);
//         const secs = Math.floor((rem % 60000) / 1000);
//         const mm = String(mins).padStart(2,"0");
//         const ss = String(secs).padStart(2,"0");
//         timerEl.textContent = `${mm}:${ss}`;

//         if (rem <= 0) {
//             hideEatStatus();
//             showShareButton();
//             stopUpdateLoop();
//             if (eatStatusIntervalId) { 
//                 clearInterval(eatStatusIntervalId); 
//                 eatStatusIntervalId = null; 
//             }
//         }
//     }
//     tick();
//     eatStatusIntervalId = setInterval(tick, 1000);
//     setEatCircleActive(true);
// }

// function hideEatStatus(){
//     setEatCircleActive(false);
//     const el = $qs("#eatStatus");
//     if (!el) return;
    
//     el.classList.add("hidden");
//     const timerEl = $qs("#eatStatusTimer");
//     if (timerEl) timerEl.textContent = "";
//     if (eatStatusIntervalId) { 
//         clearInterval(eatStatusIntervalId); 
//         eatStatusIntervalId = null; 
//     }
// }

// // --- helpers для eat-circle ---
// function getEatCircle() { 
//     return $qs("#eatCircle"); 
// }

// function setEatCircleSearching(on) {
//     const el = getEatCircle();
//     if (!el) return;
//     if (on) {
//         el.classList.add("searching");
//         // запускаем радар (3 кольца)
//         startRadarRings(3);
//     } else {
//         el.classList.remove("searching");
//         // останавливаем радар
//         stopRadarRings();
//     }
// }

// function setEatCircleActive(on) {
//     const el = getEatCircle();
//     if (!el) return;
//     if (on) {
//         el.classList.add("active");
//         el.setAttribute("aria-pressed", "true");
//     } else {
//         el.classList.remove("active");
//         el.classList.remove("searching");
//         el.setAttribute("aria-pressed", "false");
//     }
// }





// function $qs(sel) { 
//     return document.querySelector(sel); 
// }

// // вставьте это в static/client.js (например сразу после функции $qs)
// function openUserProfilePage(tg_id) {
//     if (!tg_id) {
//         alert("tg_id не указан");
//         return;
//     }
//     try {
//         sessionStorage.setItem("view_tg_id", String(tg_id));
//     } catch (e) {
//         console.warn("sessionStorage set failed", e);
//     }
//     // loadScreen уже делает history.pushState и runScreenInit
//     loadScreen("user_profile_view");
// }


// async function postJson(path, body) {
//     const res = await fetch(API_ROOT + path, {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify(body)
//     });
//     if (!res.ok) {
//         const text = await res.text().catch(()=>null);
//         throw new Error("HTTP " + res.status + (text ? " - " + text : ""));
//     }
//     return res.json();
// }

// // --- safe parseInnerQuery: принимает "a=b&c=d" или "?a=b&c=d" ---
// function parseInnerQuery(str) {
//     if (!str) return {};
//     if (str.startsWith("?") || str.startsWith("#")) str = str.slice(1);
//     const params = new URLSearchParams(str);
//     const obj = {};
//     for (const [k,v] of params.entries()) obj[k] = v;
//     // keep "user" as decoded JSON string (do not parse to object)
//     if (obj.user) {
//         try {
//             obj.user = decodeURIComponent(obj.user);
//         } catch (e) {}
//     }
//     return obj;
// }

// // find tgWebAppData in different places
// function extractTgWebAppDataFromUrl() {
//     const tryParams = (s) => {
//         if (!s) return null;
//         const idx = s.indexOf("tgWebAppData=");
//         if (idx === -1) return null;
//         let tail = s.slice(idx + "tgWebAppData=".length);
//         const htmlPos = tail.indexOf(".html");
//         if (htmlPos !== -1) tail = tail.slice(0, htmlPos);
//         try { return decodeURIComponent(tail); } catch(e) { return tail; }
//     };

//     let raw = tryParams(location.search);
//     if (raw) return parseInnerQuery(raw);

//     raw = tryParams(location.hash);
//     if (raw) return parseInnerQuery(raw);

//     raw = tryParams(location.pathname);
//     if (raw) return parseInnerQuery(raw);

//     return null;
// }

// // build initData object - поддерживает:
// // 1) WebApp.initDataUnsafe (object)
// // 2) WebApp.initData (string) -> распарсится
// // 3) tgWebAppData в url -> распарсится
// function buildInitDataObject() {
//     // prefer initData string if present
//     const initStr = window.Telegram?.WebApp?.initData ?? null;
//     if (initStr && typeof initStr === "string" && initStr.includes("=")) {
//         return parseInnerQuery(initStr);
//     }

//     // if we only have tgWebAppData in URL
//     const parsedFromUrl = extractTgWebAppDataFromUrl();
//     if (parsedFromUrl) return parsedFromUrl;

//     // if we only have unsafe object (last resort)
//     const initUnsafe = window.Telegram?.WebApp?.initDataUnsafe ?? null;
//     if (initUnsafe && typeof initUnsafe === "object") {
//         // best-effort: convert fields to strings; keep user as JSON string
//         const out = {};
//         for (const k of Object.keys(initUnsafe)) {
//             if (k === "user" && initUnsafe.user) {
//                 try { out.user = JSON.stringify(initUnsafe.user); }
//                 catch(e) { out.user = String(initUnsafe.user); }
//             } else {
//                 out[k] = String(initUnsafe[k]);
//             }
//         }
//         return out;
//     }

//     return null;
// }



// async function verifyInitData(initData) {
//     return postJson("/verify_init", { initData })
//         .catch(err => ({ ok: false, error: err.message }));
// }

// function saveTgId(tg_id) { 
//     localStorage.setItem("meeteat_tg_id", String(tg_id)); 
// }
// function getTgId() { 
//     return localStorage.getItem("meeteat_tg_id") ? Number(localStorage.getItem("meeteat_tg_id")) : null; 
// }

// async function ensureTgId() {
//     const saved = getTgId();
//     if (saved) return saved;

//     // prefer raw initData string if available
//     const rawInit = window.Telegram?.WebApp?.initData ?? null;
//     let initData = rawInit ? rawInit : buildInitDataObject();
//     if (initData) {
//         const resp = await verifyInitData(initData).catch(() => ({ ok:false }));
//         if (resp && resp.ok && resp.tg_id) {
//             saveTgId(resp.tg_id);
//             if (resp.name) localStorage.setItem("meeteat_name", resp.name);
//             if (resp.username) localStorage.setItem("meeteat_username", resp.username);
//             if (resp.avatar) localStorage.setItem("meeteat_avatar", resp.avatar);

//             // Синхронизируем профиль (await чтобы гарантировать запись до дальнейших действий, можно убрать await если не надо блокировать)
//             (async () => {
//                 try {
//                     // отправляем только существующие поля
//                     const payload = { tg_id: resp.tg_id };
//                     if (resp.name) payload.name = resp.name;
//                     if (resp.username) payload.username = resp.username;
//                     if (resp.avatar) payload.avatar = resp.avatar;
//                     await postJson("/api/profile/update", payload);
//                 } catch (err) {
//                     console.warn("profile sync failed", err);
//                 }
//             })();

//             showShareButton();
//         } else {
//             console.warn("verifyInitData failed", resp);
//         }
//     }

//     alert("tg_id не найден. Откройте в Telegram или сохраните tg_id для теста.");
//     return null;
// }




// // --- рендер interest (похожие по тегам) ---
// function renderInterestCard(u) {
//     const art = document.createElement("div");
//     art.className = "interest-card";

//     const avatarSrc = u.avatar || "/static/images/default_avatar.svg";
//     const tagsHtml = (u.tags || []).slice(0,3).map(t => `<span>${escapeHtml(t)}</span>`).join("");

//     art.innerHTML = `
//         <img class="avatar" src="${avatarSrc}" alt="${u.name || u.username || 'user'}"/>
//         <div class="info">
//             <div class="name">${escapeHtml(u.name || (u.username ? '@' + u.username : 'Пользователь'))}</div>
//             <div class="age">${u.age ? (u.age + " лет") : ""}${u.common ? " · " + u.common + " совпад." : ""}</div>
//         </div>
//         <div class="tags">${tagsHtml}</div>
//     `;
    
//     const img = art.querySelector("img");
//     if (img) img.onerror = () => { img.src = "/static/images/default_avatar.svg"; };

//     art.setAttribute("tabindex", "0");
//     art.setAttribute("role", "button");
//     art.setAttribute("aria-label", u.name || u.username || "Пользователь");

//     // клавиатурная активация (Enter / Space)
//     art.addEventListener("keydown", (ev) => {
//         if (ev.key === "Enter" || ev.key === " ") {
//             ev.preventDefault();
//             art.click();
//         }
//     });

//     // по клику открываем профиль/telegram
//     art.addEventListener("click", () => {
//         openUserProfilePage(u.tg_id || u.username);
//     });

//     return art;
// }

// async function fetchSimilarAndRender() {
//     const list = $qs("#interestList");
//     if (!list) return;
//     const placeholder = $qs("#interestListPlaceholder");
//     if (placeholder) placeholder.textContent = "Загрузка похожих пользователей…";

//     const tg_id = getTgId();
//     if (!tg_id) {
//         // если не авторизован - показать подсказку
//         if (placeholder) placeholder.textContent = "Войдите через Telegram, чтобы видеть людей с похожими интересами.";
//         return;
//     }

//     try {
//         const res = await fetch(`/api/users/similar?tg_id=${encodeURIComponent(tg_id)}&limit=12`, { cache: "no-store" });
//         if (!res.ok) throw new Error("fetch failed " + res.status);
//         const data = await res.json();
//         if (!data || !data.users || !data.users.length) {
//             list.innerHTML = '<div class="muted">Похожих пользователей не найдено</div>';
//             return;
//         }
//         list.innerHTML = "";
//         for (const u of data.users) {
//             const node = renderInterestCard(u);
//             list.appendChild(node);
//         }
//     } catch (e) {
//         console.error("fetchSimilarAndRender error", e);
//         list.innerHTML = '<div class="muted">Ошибка при загрузке похожих пользователей</div>';
//     }
// }





// function pluralizePeople(n) {
//     if (n === 0) return "0 человек";
//     if (n === 1) return "1 человек";
//     // простая форма: 2-4 -> "2 человека", else "n человек"
//     const rem10 = n % 10;
//     if (rem10 >= 2 && rem10 <= 4 && !(n % 100 >= 12 && n % 100 <= 14)) return `${n} человека`;
//     return `${n} человек`;
// }

// async function fetchNearbyAndRender(tg_id, lat, lon, radius_km = 3.0) {
//     const countEl = $qs("#nearbyCount");
//     const cards = $qs("#nearbyCards");
//     if (!countEl || !cards) return;
//     cards.innerHTML = '<div class="muted">Ищем людей поблизости…</div>';
//     try {
//         const res = await fetch(`/nearby?tg_id=${encodeURIComponent(tg_id)}&lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}&radius_km=${encodeURIComponent(radius_km)}`, { cache: "no-store" });
//         if (!res.ok) throw new Error("nearby fetch failed " + res.status);
//         const data = await res.json();
//         const items = data.nearby || [];
//         // update title
//         const txt = `Рядом - ${pluralizePeople(items.length)} готовы обедать`;
//         countEl.textContent = txt;

//         // render cards
//         cards.innerHTML = "";
//         if (items.length === 0) {
//             cards.innerHTML = '<div class="muted">Никого рядом не найдено</div>';
//             return;
//         }
//         for (const p of items) {
//             const node = renderPersonCard(p);
//             cards.appendChild(node);
//         }
//     } catch (e) {
//         console.error("fetchNearbyAndRender error", e);
//         cards.innerHTML = '<div class="muted">Ошибка при поиске людей</div>';
//         countEl.textContent = `Рядом - ?`;
//     }
// }

// function formatDistance(p) {
//     // p.distance_km может быть числом или строкой
//     const d = Number(p.distance_km);
//     if (!isFinite(d) || d <= 0) return "";
//     if (d < 1) {
//         return `${Math.round(d * 1000)} м`;
//     } else if (d < 10) {
//         // одна десятичная точность для ближайших километров
//         return `${(Math.round(d * 10) / 10).toFixed(1)} км`;
//     } else {
//         // цельные километры для дальних
//         return `${Math.round(d)} км`;
//     }
// }

// function renderPersonCard(p) {
//     const art = document.createElement("article");
//     art.className = "person-card";

//     const avatarSrc = p.avatar || "/static/images/default_avatar.svg";

//     const distText = formatDistance(p);
//     const ageText = p.age ? (p.age + " лет") : "";
//     const metaParts = [];
//     if (ageText) metaParts.push(ageText);
//     if (distText) metaParts.push(distText);

//     art.innerHTML = `
//         <img class="avatar" src="${avatarSrc}" alt="${p.name || p.username || 'user'}" />
//         <div class="p-info">
//             <div class="p-name">${escapeHtml(p.name || (p.username ? '@'+p.username : 'Пользователь'))}</div>
//             <div class="p-meta">${metaParts.join(" · ")}</div>
//             <div class="p-tags"></div>
//         </div>
//     `;
//     const img = art.querySelector("img");
//     if (img) img.onerror = () => { img.src = "/static/images/default_avatar.svg"; };

//     art.setAttribute("tabindex", "0");
//     art.setAttribute("role", "button");
//     art.setAttribute("aria-label", p.name || p.username || "Пользователь");

//     // клавиатурная активация (Enter / Space)
//     art.addEventListener("keydown", (ev) => {
//         if (ev.key === "Enter" || ev.key === " ") {
//             ev.preventDefault();
//             art.click();
//         }
//     });

//     art.addEventListener("click", () => {
//         openUserProfilePage(p.tg_id || p.username);
//     });

//     return art;
// }


// // small helper to escape text nodes
// function escapeHtml(s) {
//     if (!s) return "";
//     return String(s).replace(/[&<>"']/g, function(m) {
//         return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[m];
//     });
// }

// async function startEating() {
//     try {
//         const rawInit = window.Telegram?.WebApp?.initData ?? null;
//         const initData = rawInit ? rawInit : buildInitDataObject();

//         let verified;
//         if (initData) {
//             verified = await verifyInitData(initData);
//         } else {
//             const saved = localStorage.getItem("meeteat_tg_id");
//             if (saved) verified = { ok: true, tg_id: Number(saved) };
//             else return alert("Откройте приложение через Telegram, либо сохраните tg_id для теста.");
//         }

//         if (!verified.ok) {
//             console.error("verify failed", verified);
//             return alert("Auth failed");
//         }

//         const tg_id = verified.tg_id;
//         saveTgId(tg_id);

//         navigator.geolocation.getCurrentPosition(async pos => {
//             const body = { tg_id, lat: pos.coords.latitude, lon: pos.coords.longitude };
//             const data = await postJson("/start", body);
//             console.log("start:", data);
//             startUpdateLoop(tg_id);
//             showTimerAndUi(data.expires_at);
//             showEatStatus(data.expires_at);
//             fetchNearbyAndRender(tg_id, body.lat, body.lon);
//         }, err => {
//             console.error("geo error", err);
//             alert("Не удалось получить геопозицию");
//         }, { enableHighAccuracy: true, maximumAge: 5000 });
//     } catch (e) {
//         console.error(e);
//         alert("Ошибка старта: " + e.message);
//     }
// }

// async function stopEating() {
//     const tg_id = Number(localStorage.getItem("meeteat_tg_id"));
//     if (!tg_id) return alert("tg_id not found");

//     try {
//         await postJson("/stop", { tg_id });
//         stopUpdateLoop();
//         hideTimerAndUi();
//         hideEatStatus();
//         showShareButton(); 
//         alert("Сессия остановлена");
//     } catch (e) {
//         console.error(e);
//         alert("Stop failed");
//     }
// }

// let updateIntervalId = null;

// function startUpdateLoop(tg_id) {
//     stopUpdateLoop();
//     updateIntervalId = setInterval(() => {
//         navigator.geolocation.getCurrentPosition(async pos => {
//         try {
//             await postJson("/start", { tg_id, lat: pos.coords.latitude, lon: pos.coords.longitude });
//             console.log("pos updated");
//             fetchNearbyAndRender(tg_id, pos.coords.latitude, pos.coords.longitude);
//         } catch (e) {
//             console.error("update error", e);
//         }
//         }, err => {
//             console.warn("geo failed during update", err);
//         }, { enableHighAccuracy: true, maximumAge: 15000 });
//     }, 30000);
// }

// function stopUpdateLoop() {
//     if (updateIntervalId) { 
//         clearInterval(updateIntervalId); 
//         updateIntervalId = null; 
//     }
// }

// // Timer UI
// function showTimerAndUi(expires_iso) {
//     const expires = new Date(expires_iso);
//     const timerEl = $qs("#timer");
//     if (!timerEl) return;
//     timerEl.style.display = "block";

//     let tid = null;
//     function tick() {
//         const rem = Math.max(0, expires - new Date());
//         const mins = Math.floor(rem / 60000);
//         const secs = Math.floor((rem % 60000) / 1000);
//         timerEl.textContent = `Сессия: ${mins}м ${secs}s`;
//         if (rem <= 0) {
//             timerEl.textContent = "Сессия завершена";
//             stopUpdateLoop();
//             if (tid) {
//                 clearInterval(tid);
//                 tid = null;
//             }
//         }
//     }
//     tick();
//     tid = setInterval(tick, 1000);
//     timerEl.dataset.tid = String(tid);
// }

// function hideTimerAndUi() {
//     const timerEl = $qs("#timer");
//     if (!timerEl) return;

//     timerEl.style.display = "none";
//     const tid = timerEl.dataset.tid;
//     if (tid) clearInterval(Number(tid));

//     timerEl.textContent = "";
// }

// // Screens loader (SPA)
// const APP = $qs("#app");
// let currentScreen = null;

// function sanitizeScreenName(name) {
//     if (!name) return "home";
//     name = name.split("?")[0].split("#")[0];
//     if (name.endsWith(".html")) name = name.slice(0, -5);
//     if (name.includes("tgWebAppData=")) return "home";
//     name = name.replace(/[^a-z0-9_\-]/gi, "");
//     return name || "home";
// }

// async function loadScreen(name) { 
//     name = sanitizeScreenName(name);
//     if (name === currentScreen) return;
//     currentScreen = name;
//     const url = `/screens/${name}.html`;
//     try {
//         const res = await fetch(url, { cache: "no-store" });
//         if (!res.ok) throw new Error("fetch failed " + res.status);
//         APP.innerHTML = await res.text();
//         runScreenInit(name);
//         history.pushState({screen: name}, "", `#${name}`);
//         document.body.setAttribute("data-screen", name);
//         if (typeof window.showFloatingBackBtn === 'function') window.showFloatingBackBtn(name === 'user_profile_view');
//     } catch(e) {
//         console.error(e);
//         APP.innerHTML = `<div class="err">Ошибка загрузки: ${e.message}</div>`;
//     }
// }


// function formatDatetimeLocal(d) {
//     const pad = n => String(n).padStart(2, '0');
//     return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
// }

// function getTomorrowAt(hour = 12, minute = 0) {
//     const now = new Date();
//     const t = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, hour, minute, 0, 0);
//     return t;
// }

// function openInviteModal(toTgId) {
//     if (!toTgId) return alert("кому позвать не указан");

//     const fromTg = getTgId();
//     if (!fromTg) { alert("Авторизуйтесь через Telegram, чтобы отправить приглашение."); return; }

//     const container = $qs("#screenModals") || (function(){
//         const c = document.createElement("div"); c.id = "screenModals"; document.body.appendChild(c); return c;
//     })();

//     const prev = container.querySelector("#inviteModal");
//     if (prev) prev.remove();

//     const modal = document.createElement("div");
//     modal.id = "inviteModal";
//     modal.className = "modal";
//     modal.innerHTML = `
//       <div class="modal-overlay"></div>
//       <div class="modal-window invite-modal" role="dialog" aria-modal="true" aria-labelledby="inviteTitle">
//         <h3 id="inviteTitle">Позвать на встречу</h3>

//           <label for="inviteTime" style="display:block;margin-bottom:6px;font-weight:600">Время</label>
//           <input id="inviteTime" type="datetime-local" style="width:100%;padding:8px;border-radius:8px;border:1px solid rgba(0,0,0,0.08);margin-bottom:12px;" />

//           <label style="display:block;margin-bottom:6px;font-weight:600">Тип встречи</label>
//           <div id="inviteType" style="display:flex;gap:10px;align-items:center;margin-bottom:12px;">
//             <label><input type="radio" name="meal" value="Завтрак" /> Завтрак</label>
//             <label><input type="radio" name="meal" value="Обед" /> Обед</label>
//             <label><input type="radio" name="meal" value="Ужин" /> Ужин</label>
//           </div>
//         </div>

//         <div class="modal-actions">
//           <button id="inviteCancel" class="btn">Отмена</button>
//           <button id="inviteSend" class="btn primary">Отправить</button>
//         </div>
//       </div>
//     `;
//     container.appendChild(modal);

//     const overlay = modal.querySelector(".modal-overlay");
//     const cancel = modal.querySelector("#inviteCancel");
//     const sendBtn = modal.querySelector("#inviteSend");
//     const timeInput = modal.querySelector("#inviteTime");
//     const mealRadios = modal.querySelectorAll('input[name="meal"]');

//     // init: set default to tomorrow lunch (Обед) - but user can change
//     const defaultDate = getTomorrowAt(13,0);
//     timeInput.value = formatDatetimeLocal(defaultDate);
//     for (const r of mealRadios) { if (r.value === "Обед") r.checked = true; }

//     function setDateFromPreset(preset) {
//         let d;
//         if (preset === 'tomorrow') d = getTomorrowAt(12,0);
//         else if (preset === 'lunch') d = getTomorrowAt(13,0);
//         else if (preset === 'dinner') d = getTomorrowAt(19,0);
//         else d = getTomorrowAt(12,0);
//         timeInput.value = formatDatetimeLocal(d);
//     }

//     function close() { 
//         try { modal.remove(); } catch(e){} 
//     }
//     if (overlay) overlay.onclick = close;
//     if (cancel) cancel.onclick = close;

//     sendBtn.onclick = async () => {
//         const timeVal = timeInput ? timeInput.value : null;
//         const meal = modal.querySelector("input[name='meal']:checked");
//         const mealVal = meal ? meal.value : null;

//         if (!timeVal) { alert("Выберите время"); return; }

//         try {
//             const payload = {
//                 from_tg_id: fromTg,
//                 to_tg_id: toTgId,
//                 time_iso: timeVal,
//                 meal_type: mealVal || null
//             };
//             const resp = await postJson("/api/invite", payload);
//             if (resp && resp.ok) {
//                 alert("Приглашение отправлено");
//                 close();
//             } else {
//                 throw new Error((resp && resp.error) ? resp.error : "server error");
//             }
//         } catch (err) {
//             console.error("invite send failed", err);
//             alert("Ошибка отправки приглашения: " + (err.message || err));
//         }
//     };

//     // accessibility: focus first control
//     setTimeout(() => { if (timeInput && typeof timeInput.focus === 'function') timeInput.focus(); }, 20);
// }

// function insertAfter(refNode, newNode) {
//     if (!refNode || !refNode.parentNode) return;
//     refNode.parentNode.insertBefore(newNode, refNode.nextSibling);
// }

// const screenInits = {
//     home() { 
//         const btn = $qs("#startBtn");
//         if (btn) btn.addEventListener("click", startEating);
//         const stopBtn = $qs("#stopBtn");
//         if (stopBtn) stopBtn.addEventListener("click", stopEating);
//         fetchSimilarAndRender();
//         loadPlacesIntoHome()
//     },
//     feed() {
//         const btn = $qs("#refreshNearby");
//         if (btn) btn.addEventListener("click", async () => {
//             const tg_id = Number(localStorage.getItem("meeteat_tg_id"));
//             const lat = 0, lon = 0;
//             try {
//                 const q = await fetch(`/nearby?tg_id=${tg_id}&lat=${lat}&lon=${lon}`).then(r => r.json());
//                 console.log("nearby:", q);
//             } catch(e) {
//                 console.error(e);
//             }
//         });
//         const eatCircle = $qs("#eatCircle");
//         if (eatCircle) {
//             eatCircle.addEventListener("click", async () => {
//                 const isActive = eatCircle.classList.contains("active");
//                 if (isActive) {
//                     if (confirm("Остановить сессию?")) {
//                         await stopEating();
//                         showEatHint("Нажми на кнопку, чтобы найти людей рядом");
//                     }
//                     return;
//                 }
//                 startEatingWithDelay();
//             });

//             eatCircle.addEventListener("keydown", (ev) => {
//                 if (ev.key === "Enter" || ev.key === " ") {
//                     ev.preventDefault();
//                     eatCircle.click();
//                 }
//             });
//         }
//     },
//     map(){},
//     chat(){},
//     profile: async function() {
//         const avatarEl = $qs("#profileAvatar");
//         const nameEl = $qs("#profileName");
//         const usernameEl = $qs("#profileUsername");
//         const ageEl = $qs("#profileAge");
//         const geoEl = $qs("#profileGeo");
//         const meetList = $qs("#meetList");
//         const tagsPanel = $qs("#tagsPanel");
//         const settingsBtn = $qs("#profileSettings");

//         function setImgWithFallback(imgEl, src) {
//             if (!imgEl) return;
//             imgEl.onerror = () => { imgEl.src = "/static/images/default_avatar.svg"; };
//             imgEl.src = src || "/static/images/default_avatar.svg";
//         }

//         // reset UI
//         if (meetList) meetList.innerHTML = '<div class="muted">Загрузка...</div>';
//         if (tagsPanel) {
//             const addBtn = tagsPanel.querySelector(".tag.outline") || null;
//             tagsPanel.innerHTML = "";
//             if (addBtn) tagsPanel.appendChild(addBtn);
//         }

//         const tg_id = getTgId();
//         if (!tg_id) {
//             const name = localStorage.getItem("meeteat_name") || "Пользователь";
//             const username = localStorage.getItem("meeteat_username") || "";
//             const avatar = localStorage.getItem("meeteat_avatar") || "/static/images/default_avatar.svg";
//             setImgWithFallback(avatarEl, avatar);
//             if (nameEl) nameEl.textContent = name;
//             if (usernameEl) usernameEl.textContent = username ? `@${username}` : "";
//             if (ageEl) ageEl.textContent = "";
//             if (meetList) meetList.innerHTML = '<div class="muted">Контактов не найдено</div>';
//             return;
//         }

//         // settings opens edit screen
//         if (settingsBtn) {
//             settingsBtn.onclick = () => {
//                 loadScreen("profile_edit");
//             };
//         }

//         try {
//             const res = await fetch(`/api/profile?tg_id=${tg_id}`, { cache: "no-store" }).then(r => r.json());
//             if (!res.ok) {
//                 console.warn("profile fetch failed", res);
//                 return;
//             }
//             const u = res.user || {};
//             setImgWithFallback(avatarEl, u.avatar);
//             if (nameEl) nameEl.textContent = u.name || u.username || "Пользователь";
//             if (usernameEl) usernameEl.textContent = u.username ? `@${u.username}` : "";
//             if (ageEl) ageEl.textContent = u.age ? `${u.age} лет` : "";

//             // tags
//             const tags = res.tags || [];
//             if (tagsPanel) {
//                 tagsPanel.innerHTML = "";
//                 for (const t of tags) {
//                     const btn = document.createElement("button");
//                     btn.className = "tag";
//                     btn.textContent = t;
//                     tagsPanel.appendChild(btn);
//                 }
//                 const add = document.createElement("button");
//                 add.className = "tag outline";
//                 add.textContent = "Добавить +";
//                 add.addEventListener("click", async () => {
//                     try {
//                         const tg = getTgId();
//                         if (!tg) return alert("tg_id не найден");
//                         const resp = await fetch(`/api/profile/tags?tg_id=${encodeURIComponent(tg)}`, { cache: "no-store" })
//                             .then(r => r.json());
//                         const current = (resp && resp.ok && Array.isArray(resp.tags)) ? resp.tags : [];
//                         openTagModal(current, null);
//                     } catch (e) {
//                         console.warn("profile fetch failed for modal", e);
//                         openTagModal([], null);
//                     }
//                 });
//                 tagsPanel.appendChild(add);
//             }

//             try {
//                 // удалим старый блок если он есть
//                 const prev = $qs("#profileReviewsSummary");
//                 if (prev) prev.remove();

//                 // заголовок раздела "Мои отзывы"
//                 const title = document.createElement("h3");
//                 title.textContent = "Мои отзывы";
//                 title.className = "section-title";

//                 // блок для отображения количества метчингов (для текущего пользователя попробуем взять из ответа сервера)
//                 const matchEl = document.createElement("h3");
//                 matchEl.className = "section-title match-count";
//                 matchEl.style.cssText = "display:flex;align-items:center;gap:12px;margin:10px 0;font-weight:700;";

//                 let matchCount = 0;
//                 try {
//                     matchCount = Number(res.match_count ?? res.matches_count ?? res.matchings_count ?? 0);
//                     if (!matchCount && Array.isArray(res.matches)) matchCount = res.matches.length;
//                     if (!matchCount && Array.isArray(res.matchings)) matchCount = res.matchings.length;
//                     if (!Number.isFinite(matchCount)) matchCount = 0;
//                 } catch (e) {
//                     matchCount = 0;
//                 }

//                 // label + number in one line
//                 const lbl = document.createElement("span");
//                 lbl.textContent = "Мое количество метчингов";
//                 lbl.style.fontWeight = "700";

//                 const num = document.createElement("span");
//                 num.className = "match-number";
//                 num.textContent = String(matchCount);
//                 num.setAttribute("aria-hidden", "true");
//                 num.style.cssText = "font-weight:700; font-size:20px;";

//                 matchEl.appendChild(lbl);
//                 matchEl.appendChild(num);

//                 // блок для аггрегации отзывов
//                 const reviewsSummary = document.createElement("div");
//                 reviewsSummary.id = "profileReviewsSummary";
//                 reviewsSummary.className = "reviews-summary";

//                 // вставляем после tagsPanel (или в нужное место)
//                 if (tagsPanel && tagsPanel.parentNode) {
//                     tagsPanel.parentNode.insertBefore(title, tagsPanel);
//                     insertAfter(tagsPanel, matchEl);
//                     insertAfter(matchEl, reviewsSummary);
//                 } else {
//                     const card = $qs(".profile-card");
//                     if (card) {
//                         card.appendChild(title);
//                         if (tagsPanel) card.appendChild(tagsPanel);
//                         card.appendChild(matchEl);
//                         card.appendChild(reviewsSummary);
//                     }
//                 }

//                 // отрисовка read-only реакций
//                 function renderReadOnlyReactions(container, data = {counts:{}}) {
//                     container.innerHTML = "";
//                     const wrap = document.createElement("div");
//                     wrap.className = "reactions-wrap readonly";

//                     for (const r of reactions) {
//                         const lbl = r.label;
//                         const cnt = Number((data.counts && data.counts[lbl]) ? data.counts[lbl] : 0);

//                         const node = document.createElement("div");
//                         node.className = "reaction-item readonly";
//                         node.dataset.reaction = lbl;
//                         node.setAttribute("aria-hidden", "false");

//                         node.innerHTML = `
//                             <div class="reaction-emoji" aria-hidden="true">${r.emoji}</div>
//                             <div class="reaction-label">${escapeHtml(lbl)}</div>
//                             <span class="reaction-badge" aria-hidden="true">${cnt}</span>
//                         `;
//                         wrap.appendChild(node);
//                     }

//                     container.appendChild(wrap);
//                 }

//                 // загрузим агрегаты (counts) для текущего профиля
//                 (async () => {
//                     try {
//                         const data = await fetchReviewsFor(tg_id); // tg_id - уже есть в profile()
//                         renderReadOnlyReactions(reviewsSummary, data);
//                     } catch (err) {
//                         console.warn("load profile reviews failed", err);
//                         reviewsSummary.innerHTML = '<div class="muted">Не удалось загрузить отзывы</div>';
//                     }
//                 })();
//             } catch(e) {
//                 console.warn("profile reviews insert failed", e);
//             }

//             // recent contacts (unchanged)
//             if (meetList) {
//                 meetList.innerHTML = "";
//                 const contacts = res.recent_contacts || [];
//                 if (!contacts.length) meetList.innerHTML = '<div class="muted">Контактов не найдено</div>';
//                 else {
//                     for (const c of contacts) {
//                         const art = document.createElement("article");
//                         art.className = "meet-card";
//                         const avatar = c.avatar || "/static/images/default_avatar.svg";
//                         const lastSeen = c.last_seen ? c.last_seen.split("T")[0] : "";
//                         art.innerHTML = `
//                         <img class="meet-avatar" src="${avatar}" alt="${c.name || c.username || 'user'}"/>
//                         <div class="meet-info">
//                             <div class="meet-name">${c.name || ('@' + (c.username || ''))}</div>
//                             <div class="meet-place">${c.username ? '@' + c.username : ''}${c.age ? ' · ' + c.age + ' лет' : ''}</div>
//                             <div class="meet-date">${lastSeen}</div>
//                         </div>
//                         `;
//                         const img = art.querySelector("img");
//                         if (img) img.onerror = () => { img.src = "/static/images/default_avatar.svg"; };
//                         meetList.appendChild(art);
//                     }
//                 }
//             }
//         } catch (e) {
//             console.error("profile load error", e);
//         }
//     },
//     profile_edit: async function() {
//         const tg_id = getTgId();
//         if (!tg_id) {
//             alert("tg_id не найден. Авторизуйтесь через Telegram.");
//             loadScreen("home");
//             return;
//         }

//         const nameInput = $qs("#editName");
//         const usernameInput = $qs("#editUsername");
//         const ageInput = $qs("#editAge");
//         const avatarInput = $qs("#editAvatar");
//         const avatarPreview = $qs("#editAvatarPreview");
//         const saveBtn = $qs("#saveProfileBtn");
//         const cancelBtn = $qs("#cancelEditBtn");

//         function setImgWithFallback(imgEl, src) {
//             if (!imgEl) return;
//             imgEl.onerror = () => { imgEl.src = "/static/images/default_avatar.svg"; };
//             imgEl.src = src || "/static/images/default_avatar.svg";
//         }

//         try {
//             const resp = await fetch(`/api/profile?tg_id=${encodeURIComponent(tg_id)}`, { cache: "no-store" });
//             if (!resp.ok) {
//                 console.warn("profile fetch http failed", resp.status, resp.statusText);
//                 alert("Не удалось загрузить профиль (сервер вернул ошибку)");
//                 loadScreen("profile");
//                 return;
//             }

//             const res = await resp.json();
//             const u = res.user || {};
//             if (nameInput) nameInput.value = u.name || "";
//             if (usernameInput) usernameInput.value = u.username || "";
//             if (ageInput) ageInput.value = u.age ? String(u.age) : "";
//             if (avatarInput) avatarInput.value = u.avatar || "";
//             setImgWithFallback(avatarPreview, u.avatar);

//             // preview avatar on input change
//             if (avatarInput) avatarInput.addEventListener("input", () => setImgWithFallback(avatarPreview, avatarInput.value));

//             // cancel
//             if (cancelBtn) cancelBtn.onclick = () => loadScreen("profile");

//             // save - только профиль (без тегов)
//             if (saveBtn) saveBtn.onclick = async () => {
//                 const newName = nameInput ? nameInput.value.trim() || null : null;
//                 const newUsername = usernameInput ? usernameInput.value.trim() || null : null;
//                 const newAgeVal = ageInput && ageInput.value ? Number(ageInput.value) : null;
//                 const newAvatar = avatarInput ? avatarInput.value.trim() || null : null;

//                 const updatePayload = { tg_id };
//                 if (newName !== null) updatePayload.name = newName;
//                 if (newAvatar) updatePayload.avatar = newAvatar;
//                 if (newAgeVal !== null && !Number.isNaN(newAgeVal)) updatePayload.age = newAgeVal;
//                 if (newUsername !== null) updatePayload.username = newUsername;

//                 try {
//                     const upd = await postJson("/api/profile/update", updatePayload);
//                     if (!upd || !upd.ok) throw new Error("update failed");

//                     alert("Профиль сохранён");

//                     // update local cache
//                     if (newName) localStorage.setItem("meeteat_name", newName);
//                     if (newUsername) localStorage.setItem("meeteat_username", newUsername);
//                     if (newAvatar) localStorage.setItem("meeteat_avatar", newAvatar);

//                     loadScreen("profile");
//                 } catch (e) {
//                     console.error(e);
//                     alert("Ошибка при сохранении: " + (e.message || e));
//                 }
//             };
//         } catch (e) {
//             console.error("profile_edit load error", e);
//             alert("Ошибка загрузки профиля");
//             loadScreen("profile");
//         }
//     },
// };

// screenInits.user_profile_view = async function() {
//     const backBtn = $qs("#backBtn");
//     if (backBtn) backBtn.onclick = () => { window.history.back(); };

//     const viewAvatar = $qs("#viewAvatar");
//     const viewName = $qs("#viewName");
//     const viewUsername = $qs("#viewUsername");
//     const viewAge = $qs("#viewAge");
//     const reviewsList = $qs("#reviewsList");
//     const callBtn = $qs("#callBtn");

//     // get tg_id from sessionStorage
//     const viewTg = sessionStorage.getItem("view_tg_id");
//     if (!viewTg) {
//         if (viewName) viewName.textContent = "Пользователь не найден";
//         if (reviewsList) reviewsList.innerHTML = '<div class="muted">Невозможно загрузить профиль</div>';
//         return;
//     }

//     // загрузим профиль целевого пользователя (если у вас API /api/profile?tg_id=... - используем его)
//     try {
//         const res = await fetch(`/api/profile?tg_id=${encodeURIComponent(viewTg)}`, { cache: "no-store" });
//         const data = await res.json();
//         if (!data || !data.ok) throw new Error("profile fetch failed");

//         const u = data.user || {};
//         if (viewAvatar) { viewAvatar.onerror = () => { viewAvatar.src = "/static/images/default_avatar.svg"; }; viewAvatar.src = u.avatar || "/static/images/default_avatar.svg"; }
//         if (viewName) viewName.textContent = u.name || (u.username ? "@" + u.username : "Пользователь");
//         // if (viewUsername) viewUsername.textContent = u.username ? `@${u.username}` : "";
//         if (viewAge) viewAge.textContent = u.age ? `${u.age} лет` : "";

//         // Добавляем заголовок "Интересы"
//         const interestsTitle = document.createElement("h3");
//         interestsTitle.textContent = "Интересы";
//         interestsTitle.className = "section-title";

//         // render tags for viewed profile
//         const viewTagsPanel = document.createElement("div");
//         viewTagsPanel.className = "tags-panel";
//         viewTagsPanel.id = "viewTagsPanel";

//         if ((data.tags || []).length === 0) {
//             viewTagsPanel.innerHTML = '<div class="muted">Интересы не указаны</div>';
//         } else {
//             for (const t of data.tags) {
//                 const btn = document.createElement("button");
//                 btn.className = "tag";
//                 btn.textContent = t;
//                 viewTagsPanel.appendChild(btn);
//             }
//         }

//         // insert tagsPanel right after profile-top (before reviews)
//         const profileCard = $qs(".profile-card");
//         const topNode = profileCard ? profileCard.querySelector(".profile-top") : null;

//         const matchElView = document.createElement("h3");
//         matchElView.className = "section-title view-match";
//         matchElView.style.cssText = "display:flex;align-items:center;gap:12px;margin:10px 0;font-weight:700;";

//         const lblView = document.createElement("span");
//         lblView.textContent = "Количество метчингов";
//         lblView.style.fontWeight = "700";

//         const numView = document.createElement("span");
//         numView.className = "match-number";
//         numView.textContent = "0"; // заглушка
//         numView.setAttribute("aria-hidden", "true");
//         numView.style.cssText = "font-weight:700; font-size:20px;";

//         matchElView.appendChild(lblView);
//         matchElView.appendChild(numView);

//         // вставляем так: interestsTitle -> viewTagsPanel -> matchElView
//         if (profileCard) {
//             if (topNode && topNode.nextSibling) {
//                 profileCard.insertBefore(interestsTitle, topNode.nextSibling);
//                 insertAfter(interestsTitle, viewTagsPanel);
//                 insertAfter(viewTagsPanel, matchElView);
//             } else {
//                 profileCard.appendChild(interestsTitle);
//                 profileCard.appendChild(viewTagsPanel);
//                 profileCard.appendChild(matchElView);
//             }
//         }
//     } catch (e) {
//         console.error("load profile view error", e);
//         if (viewName) viewName.textContent = "Ошибка загрузки профиля";
//     }

//     if (reviewsList) {
//         reviewsList.innerHTML = "";

//         const wrap = document.createElement("div");
//         wrap.className = "reactions-wrap";

//         // helper: обновляет кнопки внутри wrap по данным от сервера
//         function updateWrapFromData(wrapEl, data) {
//             const counts = (data && data.counts) ? data.counts : {};
//             const viewerArr = Array.isArray(data && data.viewer) ? data.viewer : [];
//             for (const btn of wrapEl.querySelectorAll(".reaction-item")) {
//                 const lbl = btn.dataset.reaction || "";
//                 const cnt = Number((counts[lbl] !== undefined) ? counts[lbl] : 0);
//                 const badge = btn.querySelector(".reaction-badge");
//                 if (badge) badge.textContent = String(cnt);
//                 const sel = viewerArr.includes(lbl);
//                 btn.classList.toggle("selected", sel);
//                 btn.setAttribute("aria-pressed", sel ? "true" : "false");
//             }
//         }

//         // создаём кнопки реакций (compact)
//         const viewer = getTgId();
//         const targetTg = String(viewTg || sessionStorage.getItem("view_tg_id") || "");
//         for (const rObj of reactions) {
//             const rawLabel = String(rObj.label || '').trim();
//             const words = rawLabel ? rawLabel.split(/\s+/) : [];
//             const firstWord = words.length ? words.shift() : '';
//             const restText = words.length ? words.join(' ') : '';

//             const btn = document.createElement("button");
//             btn.type = "button";
//             btn.className = "reaction-item compact";
//             btn.dataset.reaction = rawLabel;
//             btn.setAttribute("role", "button");
//             btn.setAttribute("tabindex", "0");
//             btn.setAttribute("aria-pressed", "false");
//             btn.title = rawLabel;

//             btn.innerHTML = `
//                 <div class="reaction-emoji" aria-hidden="true">${rObj.emoji}</div>
//                 <div class="reaction-label">
//                     <span class="reaction-first">${escapeHtml(firstWord)}</span>${restText ? ' ' : ''}<span class="reaction-rest">${escapeHtml(restText)}</span>
//                 </div>
//                 <span class="reaction-badge" aria-hidden="true">0</span>
//             `;

//             // click: toggle review + перезапрос агрегатов и обновление UI
//             btn.addEventListener("click", async (e) => {
//                 e.preventDefault();
//                 const viewerId = getTgId();
//                 if (!viewerId) return alert("Авторизуйтесь через Telegram, чтобы ставить реакции.");

//                 const target = targetTg || (reviewsList.dataset && reviewsList.dataset.targetTg) || sessionStorage.getItem("view_tg_id");
//                 if (!target) return console.warn("No targetTg for reviewsList");

//                 const badge = btn.querySelector(".reaction-badge");
//                 const origSelected = btn.classList.contains("selected");
//                 const origBadgeCount = badge ? Number(badge.textContent || 0) : 0;

//                 // Оптимистично переключаем состояние UI сразу
//                 btn.classList.toggle("selected", !origSelected);
//                 btn.setAttribute("aria-pressed", !origSelected ? "true" : "false");
//                 if (badge) badge.textContent = String(origSelected ? Math.max(0, origBadgeCount - 1) : (origBadgeCount + 1));

//                 // блокируем кнопку, чтобы не спамили
//                 btn.disabled = true;

//                 try {
//                     const payload = { reviewer_tg_id: Number(viewerId), target_tg_id: Number(target), reaction: rawLabel };
//                     const resp = await postJson("/api/review/toggle", payload);
//                     if (!resp || !resp.ok) throw new Error(resp && resp.error ? resp.error : "server error");

//                     // после успеха - перезапросим агрегаты и синхронизируем UI
//                     const refreshed = await fetchReviewsFor(target, viewerId);
//                     updateWrapFromData(wrap, refreshed);
//                 } catch (err) {
//                     console.error("toggle review failed", err);

//                     // откатываем оптимистичное изменение
//                     btn.classList.toggle("selected", origSelected);
//                     btn.setAttribute("aria-pressed", origSelected ? "true" : "false");
//                     if (badge) badge.textContent = String(origBadgeCount);

//                     alert("Ошибка: " + (err.message || err));
//                 } finally {
//                     btn.disabled = false;
//                 }
//             });

//             // клавиатурная доступность (Enter / Space)
//             btn.addEventListener("keydown", (ev) => {
//                 if (ev.key === "Enter" || ev.key === " ") {
//                     ev.preventDefault();
//                     btn.click();
//                 }
//             });

//             wrap.appendChild(btn);
//         }

//         reviewsList.appendChild(wrap);

//         // initial load counts/state
//         (async () => {
//             try {
//                 const tgt = sessionStorage.getItem("view_tg_id") || targetTg;
//                 if (!tgt) return;
//                 const data = await fetchReviewsFor(tgt, viewer);
//                 updateWrapFromData(wrap, data);
//             } catch (e) {
//                 console.warn("reviews initial fetch failed", e);
//             }
//         })();
//     }

//     // Позвать - открывает модалку
//     if (callBtn) {
//         callBtn.onclick = () => openInviteModal(viewTg);
//     }
// };

// function runScreenInit(name) {
//     (screenInits[name] || (() => {}))();
// }

// // AUTO START (only if user grants geolocation)
// async function tryAutoStart() {
//     const tg_id = await ensureTgId();
//     if (!tg_id) return;

//     // try get geolocation silently
//     navigator.geolocation.getCurrentPosition(async pos => {
//         try {
//             const body = { tg_id, lat: pos.coords.latitude, lon: pos.coords.longitude };
//             const data = await postJson("/start", body);
//             console.log("auto-start:", data);
//             showEatStatus(data.expires_at);
//             showTimerAndUi(data.expires_at);
//             startUpdateLoop(tg_id);
//         } catch (e) {
//             console.warn("auto start failed", e);
//         }
//     }, (err) => {
//         console.warn("geo denied or failed", err);
//     }, { enableHighAccuracy: true, maximumAge: 0, timeout: 10000 });
// }


// document.addEventListener("DOMContentLoaded", async () => {
//     // Telegram WebApp tweaks
//     const tg = window.Telegram?.WebApp;
//     if (tg) try { tg.expand(); } catch(e) {}

//     // Auto verify Telegram initData if present
//     try {
//         const rawInit = window.Telegram?.WebApp?.initData ?? null;
//         const initData = rawInit ? rawInit : buildInitDataObject();

//         if (initData) {
//             const resp = await verifyInitData(initData);
//             if (resp && resp.ok && resp.tg_id) {
//                 saveTgId(resp.tg_id);
//                 // optionally save profile locally
//                 if (resp.name) localStorage.setItem("meeteat_name", resp.name);
//                 if (resp.username) localStorage.setItem("meeteat_username", resp.username);
//                 if (resp.avatar) localStorage.setItem("meeteat_avatar", resp.avatar);

//                 showShareButton();
//             } else {
//                 console.warn("verifyInitData failed", resp);
//             }
//         }
//     } catch (e) {
//         console.error("verifyInitData error", e);
//     }

//     // --- floating back button (top-left) ---
//     // create once, hidden by default; show/hide via showFloatingBackBtn()
//     (function ensureFloatingBackBtn(){
//         if ($qs("#floatingBackBtn")) return;
//         const btn = document.createElement("button");
//         btn.id = "floatingBackBtn";
//         btn.type = "button";
//         btn.setAttribute("aria-label", "Назад");
//         btn.title = "Назад";
//         btn.style.display = "none"; // hidden by default
//         btn.innerHTML = `
//             <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg">
//                 <path d="M15 18L9 12L15 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
//             </svg>
//         `;
//         // single click handler (history.back with fallback)
//         btn.addEventListener("click", (e) => {
//             e.preventDefault();
//             if (window.history && window.history.length > 1) window.history.back();
//             else loadScreen("home");
//         });
//         // keyboard accessible
//         btn.addEventListener("keydown", (e) => {
//             if (e.key === "Enter" || e.key === " ") { e.preventDefault(); btn.click(); }
//         });
//         document.body.appendChild(btn);

//         // helper exposed locally
//         window.showFloatingBackBtn = function(show) {
//             try {
//                 btn.style.display = show ? "inline-flex" : "none";
//             } catch (e) { /* ignore */ }
//         };
//     })();

//     const menu = $qs("#menu");
//     if (menu) {
//         menu.addEventListener("click", (e) => {
//             const b = e.target.closest("button[data-screen]");
//             if(!b) return;
//             loadScreen(b.dataset.screen);
//         });
//     }

//     // initial screen from hash
//     const initial = location.hash?.slice(1) || "home";
//     loadScreen(initial);
// });


// window.addEventListener("popstate", (e) => {
//     const s = (e.state && e.state.screen) || "home";
//     loadScreen(s);
// });