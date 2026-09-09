"use strict";

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];
const API = "";

const CLASE_PILL = { alta: "alta", media: "media", baja: "baja" };

function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detalle || `HTTP ${res.status}`);
  }
  return res.json();
}

/* ------------------------------------------------ nav / vistas */
function activarVista(nombre) {
  $$(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.view === nombre));
  $$(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${nombre}`));
  if (nombre === "simulador") cargarSimulador();
  if (nombre === "brechas") cargarBrechas();
  if (nombre === "costos") cargarCostos();
  if (nombre === "tecnica") cargarTecnica();
}
$$(".nav-item").forEach((b) => b.addEventListener("click", () => activarVista(b.dataset.view)));

/* ------------------------------------------------ chat */
let sesionId = localStorage.getItem("rrhh_sesion") || "";
const logEl = $("#chat-log");
let demoLimite = null;

function actualizarBadgeDemo(restantes) {
  const el = $("#brand-demo");
  if (restantes == null || demoLimite == null) {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  el.classList.toggle("exhausted", restantes <= 0);
  el.textContent = restantes > 0
    ? `Demo · ${restantes} ${restantes === 1 ? "consulta" : "consultas"} con IA restante(s)`
    : "Demo · IA agotada · motor offline ($0)";
  el.hidden = false;
}

function nuevoChat() {
  api("/api/sesiones/nueva", { method: "POST" })
    .then((r) => {
      sesionId = r.sesion_id;
      localStorage.setItem("rrhh_sesion", sesionId);
      actualizarBadgeDemo(demoLimite);
    })
    .catch(() => {});
  logEl.innerHTML = "";
  pushMsg("ai",
    "Hola. Soy el asistente del área de talento. Pregúntame por el ranking, un postulante, la fase técnica, brechas comunes, el origen de las postulaciones o los costos.",
    ["¿Quienes pasan a fase tecnica?", "Ayuda"]);
}

function pushMsg(rol, texto, sugerencias = [], uso = null, aviso = null, faq = null, bloques = []) {
  const el = document.createElement("div");
  el.className = `msg ${rol}`;
  let html = `<div class="bubble">${esc(texto)}`;
  if (aviso) html += `<div class="aviso">${esc(aviso)}</div>`;
  if (faq) {
    html += `<div class="bloque"><h4>Respuesta general</h4>
      <div class="chip" data-cmd="${esc(faq.pregunta)}">${esc(faq.pregunta)}</div>
      <div style="margin-top:6px">${esc(faq.respuesta)}</div></div>`;
  }
  for (const b of bloques) html += renderBloque(b);
  if (sugerencias && sugerencias.length) {
    html += `<div class="chips">${sugerencias
      .map((s) => `<button class="chip" data-cmd="${esc(s)}">${esc(s)}</button>`)
      .join("")}</div>`;
  }
  if (uso) {
    const t = uso.tokens || {};
    html += `<div class="meta-uso">IA ${esc(uso.proveedor)} · ${esc(uso.modelo)} · ${t.total ?? 0} tokens · ~$${(uso.costo_usd ?? 0).toFixed(6)}</div>`;
  } else if (modoOffline()) {
    html += `<div class="meta-uso">modo offline · 0 tokens · $0</div>`;
  }
  html += "</div>";
  el.innerHTML = html;
  el.querySelectorAll("[data-cmd]").forEach((c) =>
    c.addEventListener("click", () => enviar(c.dataset.cmd))
  );
  logEl.appendChild(el);
  logEl.scrollTop = logEl.scrollHeight;
}

function renderBloque(b) {
  if (!b) return "";
  let out = `<div class="bloque"><h4>${esc(b.titulo || "")}</h4>`;
  if (b.tipo === "tabla") {
    out += `<div class="table-wrap"><table><thead><tr>${(b.columnas || [])
      .map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>`;
    for (const fila of b.filas || []) {
      out += "<tr>" + fila.map(celda).join("") + "</tr>";
    }
    out += "</tbody></table></div>";
  } else if (b.tipo === "tarjetas") {
    out += `<div class="tarjetas">`;
    for (const item of b.items || []) {
      out += `<div class="tcard"><h4>${esc(item.titulo)}</h4>`;
      if (item.subtitulo) out += `<div class="sub">${esc(item.subtitulo)}</div>`;
      if (item.etiqueta) out += `<span class="pill ${esc(item.clase || "")}">${esc(item.etiqueta)}</span>`;
      if (item.meta && item.meta.length) {
        out += `<div class="meta">${item.meta.map((m) => `<div>${esc(m)}</div>`).join("")}</div>`;
      }
      out += "</div>";
    }
    out += "</div>";
  } else if (b.tipo === "lista") {
    out += `<ul class="rows">`;
    for (const item of b.items || []) {
      if (item && typeof item === "object") {
        out += `<li><span class="pill ${esc(item.clase || "")}">${esc(item.texto)}</span></li>`;
      } else {
        out += `<li>${esc(item)}</li>`;
      }
    }
    out += "</ul>";
  }
  return out + "</div>";
}

function celda(v) {
  if (v && typeof v === "object" && "texto" in v) {
    if (v.clase) {
      if (CLASE_PILL[v.clase]) return `<td><span class="pill ${esc(v.clase)}">${esc(v.texto)}</span></td>`;
      if (v.clase.startsWith("score")) return `<td><span class="score-s ${esc(v.clase.split(" ")[1] || "")}">${esc(v.texto)}</span></td>`;
    }
    return `<td>${esc(v.texto)}</td>`;
  }
  return `<td>${esc(v)}</td>`;
}

function enviar(texto) {
  const msg = (texto || $("#chat-input").value).trim();
  if (!msg) return;
  $("#chat-input").value = "";
  pushMsg("user", msg);
  const btn = $("#btn-enviar");
  btn.disabled = true;
  api("/api/chat", {
    method: "POST",
    body: JSON.stringify({ mensaje: msg, sesion_id: sesionId }),
  })
    .then((r) => {
      sesionId = r.sesion_id || sesionId;
      localStorage.setItem("rrhh_sesion", sesionId);
      actualizarBadgeDemo(r.ia_restantes);
      pushMsg("ai", r.mensaje || "", r.sugerencias || [], r.uso || null,
        r.aviso || (r.aviso_ia ? r.aviso_ia.mensaje : null), r.faq || null, r.bloques || []);
    })
    .catch(() => pushMsg("ai", "Ocurrió un error interno. Inténtalo de nuevo.", []))
    .finally(() => { btn.disabled = false; $("#chat-input").focus(); });
}

$("#btn-enviar").addEventListener("click", () => enviar());
$("#chat-input").addEventListener("keydown", (e) => { if (e.key === "Enter") enviar(); });
$("#btn-nuevo-chat").addEventListener("click", nuevoChat);

let offlineFlag = null;
function modoOffline() { return offlineFlag !== false; }

/* ------------------------------------------------ simulador */
async function cargarSimulador() {
  const sel = $("#sim-vacante");
  if (!sel.options.length) {
    try {
      const r = await api("/api/vacantes");
      sel.innerHTML = `<option value="">Todas</option>` +
        (r.vacantes || []).map((v) => `<option value="${esc(v.carpeta)}">${esc(v.vacante_id)}</option>`).join("");
    } catch { /* sin datos */ }
  }
  simularAhora();
}

function pesosActuales() {
  return {
    habilidades: +$("#peso-hab").value,
    experiencia: +$("#peso-exp").value,
    formacion: +$("#peso-for").value,
  };
}
[["peso-hab", "out-hab"], ["peso-exp", "out-exp"], ["peso-for", "out-for"]].forEach(([inp, out]) => {
  $(`#${inp}`).addEventListener("input", () => { $(`#${out}`).textContent = $(`#${inp}`).value; });
});
$("#btn-simular").addEventListener("click", simularAhora);

async function simularAhora() {
  const b = $("#btn-simular");
  b.disabled = true;
  try {
    const r = await api("/api/simular", {
      method: "POST",
      body: JSON.stringify({ ...pesosActuales(), vacante: $("#sim-vacante").value }),
    });
    const p = r.pesos || {};
    $("#sim-note").textContent = `Pesos normalizados: Habilidades ${(p.habilidades * 100).toFixed(0)}% · Experiencia ${(p.experiencia * 100).toFixed(0)}% · Formación ${(p.formacion * 100).toFixed(0)}%. Cambios respecto al score original.`;
    const thead = $("#sim-tabla").querySelector("thead");
    const tbody = $("#sim-tabla").querySelector("tbody");
    thead.innerHTML = "<tr><th>#</th><th>Vacante</th><th>Postulante</th><th>Original</th><th>Nuevo</th><th>Δ</th><th>Nivel</th></tr>";
    tbody.innerHTML = (r.resultados || []).map((x, i) => `
      <tr>
        <td>${i + 1}</td>
        <td>${esc(x.vacante)}</td>
        <td>${esc(x.nombre)}</td>
        <td>${x.original}</td>
        <td class="score-s ${esc(x.clasificacion.toLowerCase())}">${x.nuevo}</td>
        <td>${x.delta > 0 ? "+" : ""}${x.delta}</td>
        <td><span class="pill ${esc(x.clasificacion.toLowerCase())}">${esc(x.clasificacion)}</span></td>
      </tr>`).join("");
  } catch {
    $("#sim-note").textContent = "No hay candidatos evaluados para simular.";
  } finally { b.disabled = false; }
}

/* ------------------------------------------------ brechas */
async function cargarBrechas() {
  try {
    const r = await api("/api/brechas");
    let resumen = `Analicé <b>${r.total_candidatos}</b> postulante(s) evaluado(s).`;
    if (r.con_requisito_esencial_ausente) {
      resumen += ` <b>${r.con_requisito_esencial_ausente}</b> no cumplen un requisito esencial.`;
    }
    $("#brechas-resumen").innerHTML = `<p>${resumen}</p>`;
    const tb = $("#brechas-tabla").querySelector("tbody");
    tb.innerHTML = "<tr><th>Brecha</th><th>Frecuencia</th></tr>" +
      r.brechas.map((b) => `<tr><td>${esc(b.descripcion)}</td><td>${b.candidatos}</td></tr>`).join("") ||
      "<tr><td>Sin brechas registradas.</td><td>0</td></tr>";
  } catch { /* sin datos */ }
}

/* ------------------------------------------------ costos */
async function cargarCostos() {
  try {
    const r = await api("/api/costos");
    const f2 = r.fase2 || {}, chat = r.chat || {};
    $("#costos-metricas").innerHTML = `
      <div class="metric"><div class="m-v">${f2.candidatos || 0}</div><div class="m-l">Evaluados F2</div></div>
      <div class="metric"><div class="m-v">${(f2.total_tokens || 0).toLocaleString()}</div><div class="m-l">Tokens F2</div></div>
      <div class="metric"><div class="m-v">${chat.llamadas || 0}</div><div class="m-l">Llamadas chat</div></div>
      <div class="metric"><div class="m-v">${(chat.costo_usd || 0).toFixed(6)}</div><div class="m-l">Costo chat (USD)</div></div>
      ${r.offline ? '<div class="metric"><div class="m-v">$0</div><div class="m-l">Modo offline</div></div>' : ""}`;
    $("#costos-chat").querySelector("tbody").innerHTML =
      (r.detalle_chat || []).length
        ? r.detalle_chat.map((u) => `<tr><td>${esc((u.fecha || "").slice(0, 19).replace("T", " "))}</td><td>${esc(u.modelo)}</td><td>${u.total_tokens}</td><td>${u.costo_usd.toFixed(6)}</td></tr>`).join("")
        : "<tr><td colspan='4'>Sin llamadas de IA registradas.</td></tr>";
    $("#costos-tarifas").querySelector("tbody").innerHTML =
      Object.entries(r.tarifas || {}).map(([m, p]) =>
        `<tr><td>${esc(m)}</td><td>${p.entrada}</td><td>${p.salida}</td></tr>`).join("");
  } catch { /* sin datos */ }
}

/* ------------------------------------------------ fase técnica */
async function cargarTecnica() {
  const cont = $("#tecnica-tarjetas");
  cont.innerHTML = "<p class='subtle'>Cargando…</p>";
  let tarjetas = "";
  try {
    const r = await api("/api/vacantes");
    for (const v of r.vacantes || []) {
      const rr = await api(`/api/ranking?carpeta=${encodeURIComponent(v.carpeta)}`);
      const altos = (rr.candidatos || []).filter((c) => c.clasificacion === "Alta");
      if (altos.length) {
        tarjetas += `<div class="card"><h3>${esc(rr.vacante_id)}</h3><div class="tarjetas">` +
          altos.map((c) => `
            <div class="tcard">
              <h4>${esc(c.nombre)}</h4>
              <div class="sub">${c.match_score}/100 · <span class="pill alta">Alta</span></div>
              <div class="meta">
                <div>📞 ${esc(c.telefono || "sin datos")}</div>
                <div>✉️ ${esc(c.email_remitente || "sin datos")}</div>
              </div>
            </div>`).join("") + "</div></div>";
      }
    }
    cont.innerHTML = tarjetas || "<div class='card'><h3>Sin candidatos Alta</h3><p class='subtle'>Ningún evaluado alcanza 80+ de compatibilidad.</p></div>";
  } catch { cont.innerHTML = "<p class='subtle'>Sin datos disponibles.</p>"; }
}

/* ------------------------------------------------ arranque */
(async function init() {
  try {
    const h = await api("/api/health");
    offlineFlag = h.modo === "offline";
    demoLimite = (typeof h.limite_ia_demo === "number" && h.limite_ia_demo > 0)
      ? h.limite_ia_demo : null;
    $("#brand-mode").textContent = h.modo === "offline" ? "modo offline · $0" : `IA: ${h.modo}`;
    $("#sidebar-health").innerHTML =
      `<span class="badge ${h.modo === "offline" ? "offline" : "online"}">${h.modo}</span> · ${esc(h.modelo_chat)}`;
    actualizarBadgeDemo(demoLimite);
  } catch { /* sin servidor de salud */ }
  activarVista("chat");
  if (!logEl.children.length) {
    if (!sesionId) {
      try { const r = await api("/api/sesiones/nueva", { method: "POST" }); sesionId = r.sesion_id; localStorage.setItem("rrhh_sesion", sesionId); } catch {}
    }
    pushMsg("ai",
      "Hola. Soy el asistente del área de talento. Pregúntame por el ranking, un postulante, la fase técnica, brechas comunes, el origen de las postulaciones o los costos.",
      ["¿Quienes pasan a fase tecnica?", "Ranking de ANALISTA DE DATOS", "¿Cuales son las brechas mas comunes?", "Ayuda"]);
  }
  $("#chat-input").focus();
})();