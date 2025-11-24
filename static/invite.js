// // static/invite.js

// export async function openInviteModal(toTgId) {
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

//         <label for="inviteTypeSelect" style="display:block;margin-bottom:6px;font-weight:600">Тип встречи</label>
//         <div id="inviteType" style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px;">
//           <label><input type="radio" name="meal" value="Завтрак" /> Завтрак</label>
//           <label><input type="radio" name="meal" value="Обед" /> Обед</label>
//           <label><input type="radio" name="meal" value="Ужин" /> Ужин</label>
//           <label><input type="radio" name="meal" value="Попить кофе" /> Попить кофе</label>
//         </div>

//         <label for="inviteTime" style="display:block;margin-bottom:6px;font-weight:600">Время</label>
//         <input id="inviteTime" type="datetime-local" style="width:100%;padding:8px;border-radius:8px;border:1px solid rgba(0,0,0,0.08);margin-bottom:12px;" />

//         <label for="invitePlace" style="display:block;margin-bottom:6px;font-weight:600">Место</label>
//         <select id="invitePlace" style="width:100%;padding:8px;border-radius:8px;border:1px solid rgba(0,0,0,0.08);margin-bottom:12px;">
//           <option value="">— Не указано —</option>
//         </select>

//         <label for="inviteMessage" style="display:block;margin-bottom:6px;font-weight:600">Сообщение (необязательно)</label>
//         <textarea id="inviteMessage" rows="4" style="width:100%;padding:8px;border-radius:8px;border:1px solid rgba(0,0,0,0.08);margin-bottom:12px;" placeholder="Например: Давай выпьем кофе в 16:00 у входа"></textarea>

//         <div class="modal-actions" style="display:flex;gap:8px;justify-content:flex-end;">
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
//     const placeSelect = modal.querySelector("#invitePlace");
//     const msgInput = modal.querySelector("#inviteMessage");

//     // init defaults
//     const defaultDate = getTomorrowAt(13,0);
//     timeInput.value = formatDatetimeLocal(defaultDate);
//     for (const r of mealRadios) { if (r.value === "Обед") r.checked = true; }

//     // load places into select (uses fetchPlacesApi from static/client.js)
//     (async () => {
//         try {
//             const places = await fetchPlacesApi(50);
//             // ensure unique and stable order
//             places.forEach(p => {
//                 const opt = document.createElement("option");
//                 opt.value = p.id !== undefined ? String(p.id) : "";
//                 opt.dataset.name = p.name || "";
//                 opt.textContent = `${p.name || 'Без названия'}${p.category ? ' — ' + p.category : ''}`;
//                 placeSelect.appendChild(opt);
//             });
//         } catch (e) {
//             console.warn("places load failed", e);
//         }
//     })();

//     function close() { try { modal.remove(); } catch(e){} }

//     if (overlay) overlay.onclick = close;
//     if (cancel) cancel.onclick = close;

//     sendBtn.onclick = async () => {
//         const timeVal = timeInput ? timeInput.value : null;
//         const meal = modal.querySelector("input[name='meal']:checked");
//         const mealVal = meal ? meal.value : null;
//         const placeId = placeSelect ? placeSelect.value : "";
//         const placeName = placeSelect ? (placeSelect.selectedOptions[0]?.dataset?.name || "") : "";
//         const message = msgInput ? msgInput.value.trim() : "";

//         if (!timeVal) { alert("Выберите время"); return; }
//         // prepare payload
//         const payload = {
//             from_tg_id: Number(fromTg),
//             to_tg_id: Number(toTgId),
//             time_iso: timeVal,
//             meal_type: mealVal || null,
//             place_id: placeId ? (isNaN(Number(placeId)) ? placeId : Number(placeId)) : null,
//             place_name: placeName || null,
//             message: message || null
//         };
//         sendBtn.disabled = true;
//         try {
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
//         } finally {
//             sendBtn.disabled = false;
//         }
//     };

//     setTimeout(() => { if (timeInput && typeof timeInput.focus === 'function') timeInput.focus(); }, 20);
// }


// // Получить входящие приглашения от сервера
// export async function fetchIncomingInvites() {
//     const tg = getTgId();
//     if (!tg) return [];
//     try {
//         const res = await fetch(`/api/invites?tg_id=${encodeURIComponent(tg)}`, { cache: "no-store" });
//         if (!res.ok) throw new Error("fetch failed " + res.status);
//         const data = await res.json();
//         return Array.isArray(data.invites) ? data.invites : [];
//     } catch (e) {
//         console.warn("fetchIncomingInvites failed", e);
//         return [];
//     }
// }

// // Показывает модалку с приглашением (для получателя)
// export function openIncomingInviteModal(inv) {
//     if (!inv) return;
//     const container = $qs("#screenModals") || (function(){
//         const c = document.createElement("div"); c.id = "screenModals"; document.body.appendChild(c); return c;
//     })();
//     const id = `incomingInvite_${inv.id || String(Math.random()).slice(2)}`;
//     // удаляем старую с тем же id
//     const prev = container.querySelector(`#${id}`);
//     if (prev) prev.remove();
//     const modal = document.createElement("div");
//     modal.id = id;
//     modal.className = "modal";
//     const placeText = inv.place_name ? `"${escapeHtml(inv.place_name)}"` : "не указан";
//     const fromName = inv.from_name || inv.from_tg_id || "пользователь";
//     const time = inv.time_iso ? escapeHtml(inv.time_iso) : "";
//     modal.innerHTML = `
//       <div class="modal-overlay"></div>
//       <div class="modal-window" role="dialog" aria-modal="true">
//         <h3>Новое приглашение</h3>
//         <div class="muted">У вас новое приглашение в ${placeText} от ${escapeHtml(fromName)} на ${escapeHtml(inv.meal_type || '')} в ${time}</div>
//         <div style="margin-top:12px;"><strong>Сообщение:</strong><div style="margin-top:6px;">${escapeHtml(inv.message || '')}</div></div>
//         <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px;">
//           <button id="invCancel_${id}" class="btn">Закрыть</button>
//           <button id="invDecline_${id}" class="btn" style="background:#eee">Отказать</button>
//           <button id="invAccept_${id}" class="btn primary">Принять</button>
//         </div>
//       </div>
//     `;
//     container.appendChild(modal);
//     const overlay = modal.querySelector(".modal-overlay");
//     const btnClose = modal.querySelector(`#invCancel_${id}`);
//     const btnDecline = modal.querySelector(`#invDecline_${id}`);
//     const btnAccept = modal.querySelector(`#invAccept_${id}`);

//     function close() { try { modal.remove(); } catch(e){} }

//     if (overlay) overlay.onclick = close;
//     if (btnClose) btnClose.onclick = close;

//     async function respond(action) {
//         try {
//             const payload = { invite_id: inv.id, responder_tg_id: Number(getTgId()), action: action }; // action: "accept"|"decline"
//             const resp = await postJson("/api/invite/respond", payload);
//             if (!resp || !resp.ok) throw new Error(resp && resp.error ? resp.error : "server error");
//             alert(action === "accept" ? "Вы приняли приглашение" : "Вы отказали");
//             close();
//         } catch (e) {
//             console.error("invite respond failed", e);
//             alert("Ошибка: " + (e.message || e));
//         }
//     }

//     btnDecline.onclick = () => respond("decline");
//     btnAccept.onclick = () => respond("accept");
// }
