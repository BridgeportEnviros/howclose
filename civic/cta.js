/* Contact-your-officials panel (Bridgeport Environmentalists).
 *
 * One shared file, loaded at runtime by the standalone test page now and by How Close and
 * The Railyard Across the Street later, so a change here reaches every tool in one commit.
 *
 *   CTA.mount(element, { lat, lng, label })   look up officials for a point and draw the panel
 *
 * Data (all in civic/data/ unless CTA.config says otherwise):
 *   roster.json    who holds each office (rebuilt by civic/build/build_roster.py)
 *   ratings.csv    Bridgeport Environmentalists' ratings and candidate list (the sheet BE edits)
 *   messages.json  group labels and placeholder calls to action
 * Chicago aldermen come live from the City's Ward Offices dataset.
 *
 * Privacy: the typed address is never sent anywhere by this file. Only the map point (lat/lng) is sent,
 * to the U.S. Census (TIGERweb), the City of Chicago and Cook County, to find which districts contain it.
 */
(function () {
  "use strict";
  const here = (document.currentScript && document.currentScript.src) || location.href;
  const base = new URL(".", here).href;                       // .../civic/

  const CTA = window.CTA = {
    config: {
      rosterUrl: base + "data/roster.json",
      ratingsUrl: base + "data/ratings.csv",                  // swap for a published Google Sheet CSV later
      messagesUrl: base + "data/messages.json",
      shareImageUrl: new URL("../share.png", base).href,       // stand-in for the tool's personal share image
      showUnreviewed: true,                                    // test version: show people BE hasn't rated
      timeoutMs: 9000,
    },
  };

  /* ---------------- small helpers ---------------- */
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const norm = s => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/["'.,()]/g, " ").replace(/\s+/g, " ").trim();
  const SUFFIX = /^(jr|sr|ii|iii|iv)$/;
  const tokens = s => norm(s).split(" ").filter(t => t && !SUFFIX.test(t));
  const lastName = s => { const t = String(s || "").replace(/,?\s+(Jr\.?|Sr\.?|II|III|IV)$/i, "").trim().split(/\s+/); return t[t.length - 1] || ""; };
  /** Same person if the last name matches and, when both have one, the first initial too. */
  function samePerson(a, b) {
    const A = tokens(a), B = tokens(b);
    if (!A.length || !B.length) return false;
    if (A[A.length - 1] !== B[B.length - 1]) return false;
    return A[0][0] === B[0][0];
  }
  const fmtDate = iso => { if (!iso) return ""; const d = new Date(iso + "T12:00:00"); return isNaN(d) ? iso : d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }); };
  function withTimeout(p, ms) { return Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(new Error("timed out")), ms))]); }
  async function getJSON(url) { const r = await withTimeout(fetch(url), CTA.config.timeoutMs); if (!r.ok) throw new Error(r.status + " " + url); return r.json(); }

  function parseCSV(text) {
    const rows = []; let row = [], f = "", q = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (q) { if (c === '"') { if (text[i + 1] === '"') { f += '"'; i++; } else q = false; } else f += c; }
      else if (c === '"') q = true;
      else if (c === ",") { row.push(f); f = ""; }
      else if (c === "\n" || c === "\r") { if (c === "\r" && text[i + 1] === "\n") i++; row.push(f); rows.push(row); row = []; f = ""; }
      else f += c;
    }
    if (f || row.length) { row.push(f); rows.push(row); }
    const head = rows.shift().map(h => h.trim());
    return rows.filter(r => r.some(x => x.trim())).map(r => Object.fromEntries(head.map((h, i) => [h, (r[i] || "").trim()])));
  }

  /* ---------------- data ---------------- */
  let dataP = null;
  CTA.loadData = function () {
    if (!dataP) dataP = Promise.all([
      getJSON(CTA.config.rosterUrl),
      getJSON(CTA.config.messagesUrl),
      withTimeout(fetch(CTA.config.ratingsUrl), CTA.config.timeoutMs).then(r => { if (!r.ok) throw new Error("ratings " + r.status); return r.text(); }).then(parseCSV),
    ]).then(([roster, messages, ratings]) => ({ roster, messages, ratings }));
    return dataP;
  };

  /* ---------------- district lookup (point only) ---------------- */
  const TIGER = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/";
  const TIGER_LAYERS = { usHouse: 4, ilSenate: 5, ilHouse: 6 };   // 119th Congress; 2024 state legislative districts
  const COOK = "https://gis12.cookcountyil.gov/arcgis/rest/services/politicalBoundary/MapServer/9/query";
  const WARDS = "https://data.cityofchicago.org/resource/p293-wvbd.json";
  const WARD_OFFICES = "https://data.cityofchicago.org/resource/htai-wnw4.json";

  function arcgisPoint(lat, lng, outFields) {
    return new URLSearchParams({ geometry: `${lng},${lat}`, geometryType: "esriGeometryPoint", inSR: "4326",
      spatialRel: "esriSpatialRelIntersects", outFields, returnGeometry: "false", f: "json" });
  }
  async function tiger(layer, lat, lng) {
    const j = await getJSON(`${TIGER}${layer}/query?${arcgisPoint(lat, lng, "BASENAME,NAME")}`);
    const a = j.features && j.features[0] && j.features[0].attributes;
    return a ? parseInt(a.BASENAME, 10) : null;
  }
  async function ward(lat, lng) {
    const q = new URLSearchParams({ $select: "ward", $where: `intersects(the_geom,'POINT(${lng} ${lat})')` });
    const j = await getJSON(`${WARDS}?${q}`);
    return j[0] ? parseInt(j[0].ward, 10) : null;
  }
  async function cookBoard(lat, lng) {
    const j = await getJSON(`${COOK}?${arcgisPoint(lat, lng, "DISTRICT_INT,DISTRICT_TXT")}`);
    const a = j.features && j.features[0] && j.features[0].attributes;
    return a ? parseInt(a.DISTRICT_INT || a.DISTRICT_TXT, 10) : null;
  }
  CTA.lookupDistricts = async function (lat, lng) {
    const jobs = { usHouse: tiger(TIGER_LAYERS.usHouse, lat, lng), ilSenate: tiger(TIGER_LAYERS.ilSenate, lat, lng),
                   ilHouse: tiger(TIGER_LAYERS.ilHouse, lat, lng), ward: ward(lat, lng), cookBoard: cookBoard(lat, lng) };
    const keys = Object.keys(jobs), res = await Promise.allSettled(Object.values(jobs));
    const out = { failed: [] };
    keys.forEach((k, i) => { if (res[i].status === "fulfilled") out[k] = res[i].value; else { out[k] = null; out.failed.push(k); } });
    return out;
  };

  async function alderman(wardNo) {
    const j = await getJSON(`${WARD_OFFICES}?ward=${wardNo}`);
    const r = j[0]; if (!r) return null;
    const site = r.website && (r.website.url || r.website);
    return { office_key: `chicago-ward-${wardNo}`, office: `Alderperson, ${ordinal(wardNo)} Ward`, title: "Ald.",
             name: r.alderman, email: r.email, phone: r.ward_phone, website: typeof site === "string" ? site : null,
             source: "City of Chicago Ward Offices (live)" };
  }
  function ordinal(n) { const s = ["th", "st", "nd", "rd"], v = n % 100; return n + (s[(v - 20) % 10] || s[v] || s[0]); }

  /* ---------------- who, and how each is rated ---------------- */
  function ratingFor(person, ratings, role) {
    return ratings.find(r => r.office_key === person.office_key && (r.role || "officeholder") === role && samePerson(r.person, person.name)) || null;
  }
  function categoryOf(r) {
    const c = r && r.category;
    return ["opposes", "boilerplate", "no_statement", "supports"].includes(c) ? c : "unreviewed";
  }

  CTA.officialsFor = async function (d, data) {
    const byKey = Object.fromEntries(data.roster.officials.map(o => [o.office_key, o]));
    const want = [];
    const notes = [];
    if (d.ward) {
      try { const a = await alderman(d.ward); if (a) want.push(a); else notes.push(`No alderperson listed for the ${ordinal(d.ward)} Ward in the City's Ward Offices data.`); }
      catch (e) { notes.push(`Couldn't load the ${ordinal(d.ward)} Ward alderperson from the City's data. Find them at chicago.gov.`); }
      if (byKey["chicago-mayor"]) want.push(byKey["chicago-mayor"]);
    }
    for (const [k, prefix] of [["ilHouse", "il-house"], ["ilSenate", "il-senate"], ["usHouse", "us-house"], ["cookBoard", "cook-board"]]) {
      if (d[k] && byKey[`${prefix}-${d[k]}`]) want.push(byKey[`${prefix}-${d[k]}`]);
    }
    const names = { ward: "Chicago ward", ilHouse: "Illinois House district", ilSenate: "Illinois Senate district", usHouse: "U.S. House district", cookBoard: "Cook County Board district" };
    d.failed.forEach(k => notes.push(`Couldn't look up your ${names[k]} just now; that official is missing below.`));

    const entries = want.map(p => {
      const r = ratingFor(p, data.ratings, "officeholder");
      const cat = categoryOf(r);
      const candidates = cat === "opposes" ? [] :
        data.ratings.filter(x => x.role === "candidate" && x.office_key === p.office_key && !samePerson(x.person, p.name))
          .map(x => ({ name: x.person, office_key: x.office_key, office: p.office, title: "", election: x.election,
                       email: x.email, contact_form: x.contact_form, phone: x.phone, website: x.website, rating: x, category: categoryOf(x) }));
      return { ...p, rating: r, category: cat, candidates };
    });
    const dms = data.roster.decision_makers.map(p => ({ ...p, rating: null, category: "decision_maker", candidates: [] }));
    return { entries, decisionMakers: dms, notes };
  };

  /* ---------------- messages ---------------- */
  const prefs = { name: "", note: "", address: "", includeAddress: false };
  CTA.setPrefs = p => Object.assign(prefs, p);

  function greeting(p) {
    if (p.category === "decision_maker" && !p.title) return "Hello,";
    const t = p.title ? p.title + " " : "";
    return `Dear ${t}${lastName(p.name)},`;
  }
  function message(p, data, isCandidate) {
    const m = data.messages;
    const cat = p.category;
    const ask = (p.rating && p.rating.ask) || (isCandidate ? m.candidate.asks[cat] : m.groups[cat].ask);
    const subject = isCandidate ? m.candidate.subject : m.groups[cat].subject;
    const lines = [greeting(p), "", ask];
    if (prefs.note) lines.push("", prefs.note);
    lines.push("", "[IMAGE: attach the share image from the tool]");
    const sig = [prefs.name, prefs.includeAddress ? prefs.address : ""].filter(Boolean);
    if (sig.length) lines.push("", ...sig);
    return { subject, body: lines.join("\n") };
  }

  /* ---------------- share image (phones) ---------------- */
  let imageFile = null;
  async function loadImage() {
    try { const b = await (await fetch(CTA.config.shareImageUrl)).blob(); imageFile = new File([b], "railyard.png", { type: b.type || "image/png" }); }
    catch (e) { imageFile = null; }
  }
  const canShareImage = () => !!(imageFile && navigator.canShare && navigator.canShare({ files: [imageFile] }));

  /* ---------------- drawing ---------------- */
  const ORDER = ["opposes", "boilerplate", "no_statement", "supports", "unreviewed"];

  function ratingLine(p) {
    const r = p.rating;
    if (!r || p.category === "unreviewed") return `<p class="cta-why muted">No rating yet.</p>`;
    const src = r.source_url ? ` <a href="${esc(r.source_url)}" target="_blank" rel="noopener">Source${r.source_date ? ", " + esc(fmtDate(r.source_date)) : ""}</a>` : "";
    const status = r.reviewed ? `<span class="cta-tag ok">Reviewed ${esc(fmtDate(r.reviewed))}</span>` : `<span class="cta-tag draft">Draft rating: BE to confirm</span>`;
    return `<p class="cta-why">${esc(r.reason)}${src}</p><p class="cta-status">${status}</p>`;
  }

  function actions(p, idx) {
    const b = [];
    if (p.email) b.push(`<button type="button" class="cta-btn primary" data-act="email" data-i="${idx}">Email</button>`);
    if (p.contact_form) b.push(`<a class="cta-btn" href="${esc(p.contact_form)}" target="_blank" rel="noopener" data-act="form" data-i="${idx}">Contact form</a>`);
    if (p.phone) b.push(`<a class="cta-btn" href="tel:${esc(p.phone.replace(/[^\d+]/g, ""))}">Call ${esc(p.phone)}</a>`);
    if (!p.email && !p.contact_form && !p.phone && p.website) b.push(`<a class="cta-btn" href="${esc(p.website)}" target="_blank" rel="noopener">Website</a>`);
    if (!b.length) return `<p class="cta-why muted">Contact details not added yet.</p>`;
    b.push(`<button type="button" class="cta-btn ghost" data-act="copy" data-i="${idx}">Copy message</button>`);
    return `<div class="cta-actions">${b.join("")}</div>`;
  }

  function card(p, idx, data, isCandidate) {
    const party = p.party ? ` <span class="cta-party">${esc(p.party.replace(/^Democrat(ic)?$/, "Democrat"))}</span>` : "";
    const badge = isCandidate ? `<span class="cta-badge c-${p.category}">${esc(data.messages.groups[p.category].label)}</span>` : "";
    const verify = p.verify ? `<p class="cta-why muted">Name not yet confirmed against the county's site.</p>` : "";
    const srcNote = p.source_note ? `<p class="cta-why muted">${esc(p.source_note)}</p>` : "";
    const cands = (p.candidates || []).length ? `
      <div class="cta-cands"><h5>${esc(data.messages.candidate.heading)}${p.candidates[0].election ? " · " + esc(p.candidates[0].election) : ""}</h5>
        ${p.candidates.map(c => card(c, c._idx, data, true)).join("")}
        <p class="cta-why muted">Candidate list may be incomplete.</p></div>` : "";
    return `<article class="cta-card${isCandidate ? " cand" : ""}">
      ${isCandidate ? "" : `<p class="cta-office">${esc(p.office)}</p>`}
      <h4>${esc(p.name)}${party}</h4>${badge}
      ${p.category === "decision_maker" ? srcNote : ratingLine(p)}${verify}
      ${actions(p, idx)}${cands}
    </article>`;
  }

  CTA.render = function (el, result, data, meta) {
    const all = [];
    const reg = p => { p._idx = all.length; all.push(p); };
    result.entries.forEach(p => { reg(p); p.candidates.forEach(reg); });
    result.decisionMakers.forEach(reg);

    const groups = ORDER.filter(c => c !== "unreviewed" || CTA.config.showUnreviewed)
      .map(c => ({ c, people: result.entries.filter(p => p.category === c) })).filter(g => g.people.length);
    groups.push({ c: "decision_maker", people: result.decisionMakers });

    el.innerHTML = `
      ${result.notes.length ? `<div class="cta-notes">${result.notes.map(n => `<p>${esc(n)}</p>`).join("")}</div>` : ""}
      ${groups.map(g => {
        const G = data.messages.groups[g.c];
        return `<section class="cta-group g-${g.c}">
          <header><h3>${esc(G.label)} <span class="cta-count">${g.people.length}</span></h3><p>${esc(G.explainer)}</p></header>
          ${g.people.map(p => card(p, p._idx, data, false)).join("")}
        </section>`;
      }).join("")}
      <p class="cta-foot">Officials as of ${esc(fmtDate(data.roster.built))}. Ratings by Bridgeport Environmentalists from news coverage and officials' own posts.
        Think a rating is wrong? <a href="https://www.bridgeportenviros.org/" target="_blank" rel="noopener">Contact Bridgeport Environmentalists</a>.</p>`;

    el.onclick = async ev => {
      const t = ev.target.closest("[data-act]"); if (!t) return;
      const p = all[+t.dataset.i]; const isCand = !!(p.rating && p.rating.role === "candidate");
      const msg = message(p, data, isCand);
      const act = t.dataset.act;
      if (act === "email") { ev.preventDefault(); openEmailSheet(p, msg); }
      if (act === "copy") { ev.preventDefault(); copy(msg.body, "Message copied"); }
      if (act === "form") copy(msg.body, "Message copied. Paste it into the form.");
    };
    if (meta && meta.onRender) meta.onRender(all);
  };

  /* ---------------- email sheet ---------------- */
  function toast(text) {
    let t = document.getElementById("cta-toast");
    if (!t) { t = document.createElement("div"); t.id = "cta-toast"; t.setAttribute("role", "status"); document.body.appendChild(t); }
    t.textContent = text; t.classList.add("on"); clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("on"), 2600);
  }
  async function copy(text, msg) {
    try { await navigator.clipboard.writeText(text); toast(msg); }
    catch (e) { toast("Couldn't copy automatically. Select the text and copy it."); }
  }
  CTA.mailtoUrl = (to, m) => `mailto:${encodeURIComponent(to)}?subject=${encodeURIComponent(m.subject)}&body=${encodeURIComponent(m.body)}`;
  const gmailUrl = (to, m) => "https://mail.google.com/mail/?" + new URLSearchParams({ view: "cm", fs: "1", to, su: m.subject, body: m.body });
  const outlookUrl = (to, m) => "https://outlook.office.com/mail/deeplink/compose?" + new URLSearchParams({ to, subject: m.subject, body: m.body });

  function openEmailSheet(p, m) {
    let dlg = document.getElementById("cta-sheet");
    if (!dlg) { dlg = document.createElement("dialog"); dlg.id = "cta-sheet"; document.body.appendChild(dlg); }
    const share = canShareImage();
    dlg.innerHTML = `<form method="dialog" class="cta-sheet">
      <h3>Email ${esc(p.name)}</h3>
      <p class="cta-to"><b>To:</b> <span>${esc(p.email)}</span> <button type="button" class="cta-btn ghost sm" data-s="copyto">Copy address</button></p>
      <p class="cta-to"><b>Subject:</b> ${esc(m.subject)}</p>
      <pre class="cta-body">${esc(m.body)}</pre>
      ${share ? `<button type="button" class="cta-btn primary wide" data-s="share">Send with the image (phone)</button>
        <p class="cta-hint">Copies the address, then opens your phone's share sheet with the image and message. Pick Mail, then paste the address into To.</p>` : ""}
      <div class="cta-actions">
        <a class="cta-btn${share ? "" : " primary"}" href="${esc(CTA.mailtoUrl(p.email, m))}" data-s="mailto">Open in my email app</a>
        <a class="cta-btn" href="${esc(gmailUrl(p.email, m))}" target="_blank" rel="noopener">Gmail</a>
        <a class="cta-btn" href="${esc(outlookUrl(p.email, m))}" target="_blank" rel="noopener">Outlook</a>
        <a class="cta-btn ghost" href="${esc(CTA.config.shareImageUrl)}" download="railyard.png">Save the image</a>
      </div>
      <p class="cta-hint">Email drafts can't include the image automatically. Save it, then attach it to your email.</p>
      <button class="cta-btn ghost wide" value="close">Close</button>
    </form>`;
    dlg.onclick = ev => {
      const s = ev.target.closest("[data-s]"); if (!s) { if (ev.target === dlg) dlg.close(); return; }
      if (s.dataset.s === "copyto") copy(p.email, "Address copied");
      if (s.dataset.s === "share") {
        navigator.clipboard && navigator.clipboard.writeText(p.email).catch(() => {});
        navigator.share({ files: [imageFile], title: m.subject, text: m.body }).catch(() => {});
      }
    };
    dlg.showModal ? dlg.showModal() : dlg.setAttribute("open", "");
  }

  /* ---------------- entry point ---------------- */
  CTA.mount = async function (el, where, meta) {
    el.innerHTML = `<p class="cta-loading">Finding your officials…</p>`;
    loadImage();
    try {
      const [data, d] = await Promise.all([CTA.loadData(), CTA.lookupDistricts(where.lat, where.lng)]);
      if (d.failed.length === 5) throw new Error("all lookups failed");
      const result = await CTA.officialsFor(d, data);
      if (meta && meta.onDistricts) meta.onDistricts(d);
      CTA.render(el, result, data, meta);
      return { districts: d, result };
    } catch (e) {
      console.error(e);
      el.innerHTML = `<p class="cta-error">We couldn't look up officials just now. Check your connection and try again.</p>`;
      return null;
    }
  };
})();
