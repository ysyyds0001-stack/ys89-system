/**
 * YS89 GA4 自訂日期查詢 Cloudflare Worker
 * 端點：GET /api/ga4-custom?start=YYYY-MM-DD&end=YYYY-MM-DD
 *
 * 需設定的 Worker Secrets（不可放進程式碼）：
 *   GA4_SA_EMAIL  — Service Account client_email
 *   GA4_SA_KEY    — Service Account private_key（整段 PEM，含 -----BEGIN...-----）
 */

const YS89_PROP    = "properties/539393762";
const P168_PROP    = "properties/541257936";
const GA4_API      = "https://analyticsdata.googleapis.com/v1beta";
const TOKEN_URL    = "https://oauth2.googleapis.com/token";
const SCOPE        = "https://www.googleapis.com/auth/analytics.readonly";
const CTA_EVENTS   = ["platform_register_click","line_click","line_oa_click","cta_click","purchase"];
const CONV_EVENTS  = ["cta_click","subscribe_click"];

const CORS = {
  "Access-Control-Allow-Origin":  "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Content-Type": "application/json; charset=utf-8",
};

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { headers: CORS });

    const url = new URL(request.url);
    if (url.pathname !== "/api/ga4-custom")
      return new Response(JSON.stringify({ error: "Not found" }), { status: 404, headers: CORS });

    const start = url.searchParams.get("start");
    const end   = url.searchParams.get("end");
    if (!start || !end)
      return new Response(JSON.stringify({ error: "缺少 start 或 end" }), { status: 400, headers: CORS });

    try {
      const token = await getAccessToken(env.GA4_SA_EMAIL, env.GA4_SA_KEY);
      const data  = await fetchCustomRange(token, start, end);
      return new Response(JSON.stringify(data), { headers: CORS });
    } catch (e) {
      return new Response(JSON.stringify({ error: e.message }), { status: 500, headers: CORS });
    }
  }
};

// ── JWT / OAuth ───────────────────────────────────────────────────────────────

function b64url(data) {
  const s = typeof data === "string" ? data : JSON.stringify(data);
  return btoa(unescape(encodeURIComponent(s)))
    .replace(/=/g,"").replace(/\+/g,"-").replace(/\//g,"_");
}

function pemToBuffer(pem) {
  const b64 = pem.replace(/-----[^-]+-----/g,"").replace(/\s/g,"");
  const bin = atob(b64);
  const buf = new Uint8Array(bin.length);
  for (let i=0;i<bin.length;i++) buf[i] = bin.charCodeAt(i);
  return buf.buffer;
}

function bufToB64url(buf) {
  const bytes = new Uint8Array(buf);
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/=/g,"").replace(/\+/g,"-").replace(/\//g,"_");
}

async function getAccessToken(email, pem) {
  const now = Math.floor(Date.now()/1000);
  const header  = b64url({ alg:"RS256", typ:"JWT" });
  const payload = b64url({ iss:email, scope:SCOPE, aud:TOKEN_URL, iat:now, exp:now+3600 });
  const unsigned = `${header}.${payload}`;

  const key = await crypto.subtle.importKey(
    "pkcs8", pemToBuffer(pem),
    { name:"RSASSA-PKCS1-v1_5", hash:"SHA-256" },
    false, ["sign"]
  );
  const sig = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", key, new TextEncoder().encode(unsigned));
  const jwt = `${unsigned}.${bufToB64url(sig)}`;

  const resp = await fetch(TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type":"application/x-www-form-urlencoded" },
    body: new URLSearchParams({ grant_type:"urn:ietf:params:oauth:grant-type:jwt-bearer", assertion:jwt }),
  });
  const d = await resp.json();
  if (!d.access_token) throw new Error("Token 失敗: " + JSON.stringify(d));
  return d.access_token;
}

// ── GA4 runReport 通用呼叫 ────────────────────────────────────────────────────

async function runReport(token, property, body) {
  const resp = await fetch(`${GA4_API}/${property}:runReport`, {
    method: "POST",
    headers: { Authorization:`Bearer ${token}`, "Content-Type":"application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    const t = await resp.text();
    throw new Error(`GA4 ${resp.status}: ${t.slice(0,200)}`);
  }
  return resp.json();
}

function dateRange(start, end) { return [{ startDate:start, endDate:end }]; }

function ctaFilter() {
  return {
    orGroup: {
      expressions: CTA_EVENTS.map(e => ({
        filter: { fieldName:"eventName", stringFilter:{ matchType:"EXACT", value:e } }
      }))
    }
  };
}

function eventFilter(name) {
  return { filter:{ fieldName:"eventName", stringFilter:{ matchType:"EXACT", value:name } } };
}

// ── ys89.fun 數據 ─────────────────────────────────────────────────────────────

async function fetchYs89Kpis(token, start, end) {
  const [sessR, ctaR] = await Promise.all([
    runReport(token, YS89_PROP, {
      dateRanges: dateRange(start,end),
      metrics: [
        { name:"activeUsers" },
        { name:"sessions" },
        { name:"eventCount" },
      ],
    }),
    runReport(token, YS89_PROP, {
      dateRanges: dateRange(start,end),
      metrics: [{ name:"sessions" }],
      dimensionFilter: ctaFilter(),
    }),
  ]);
  const row = sessR.rows?.[0];
  const sessions    = row ? +row.metricValues[1].value : 0;
  const activeUsers = row ? +row.metricValues[0].value : 0;
  const eventCount  = row ? +row.metricValues[2].value : 0;
  const cta = ctaR.rows?.[0] ? +ctaR.rows[0].metricValues[0].value : 0;
  return {
    activeUsers,
    sessions,
    eventCount,
    cta,
    conversionRate: sessions > 0 ? Math.round(cta/sessions*10000)/100 : 0,
  };
}

async function fetchYs89Accounts(token, start, end) {
  const [sessR, ctaR] = await Promise.all([
    runReport(token, YS89_PROP, {
      dateRanges: dateRange(start,end),
      dimensions: [{ name:"sessionSource" }],
      metrics: [{ name:"sessions" }],
    }),
    runReport(token, YS89_PROP, {
      dateRanges: dateRange(start,end),
      dimensions: [{ name:"sessionSource" }],
      metrics: [{ name:"sessions" }],
      dimensionFilter: ctaFilter(),
    }),
  ]);
  const sessMap = {};
  for (const r of (sessR.rows||[])) {
    const src = r.dimensionValues[0].value;
    sessMap[src] = +r.metricValues[0].value;
  }
  const ctaMap = {};
  for (const r of (ctaR.rows||[])) {
    ctaMap[r.dimensionValues[0].value] = +r.metricValues[0].value;
  }
  return Object.entries(sessMap)
    .map(([name,s]) => ({ name, s, cta: ctaMap[name]||0 }))
    .sort((a,b)=>b.s-a.s);
}

async function fetchYs89Contents(token, start, end) {
  const [sessR, ctaR] = await Promise.all([
    runReport(token, YS89_PROP, {
      dateRanges: dateRange(start,end),
      dimensions: [{ name:"sessionManualAdContent" }],
      metrics: [{ name:"sessions" }],
    }),
    runReport(token, YS89_PROP, {
      dateRanges: dateRange(start,end),
      dimensions: [{ name:"sessionManualAdContent" }],
      metrics: [{ name:"sessions" }],
      dimensionFilter: ctaFilter(),
    }),
  ]);
  const map = {};
  for (const r of (sessR.rows||[])) {
    const c = r.dimensionValues[0].value;
    const s = +r.metricValues[0].value;
    if (!c || c==="(not set)" || s===0) continue;
    map[c] = { content:c, sessions:s, cta:0 };
  }
  for (const r of (ctaR.rows||[])) {
    const c = r.dimensionValues[0].value;
    if (map[c]) map[c].cta = +r.metricValues[0].value;
  }
  return Object.values(map).sort((a,b)=>b.sessions-a.sessions);
}

// ── picks168.com 數據 ─────────────────────────────────────────────────────────

async function fetchP168Kpis(token, start, end) {
  try {
    const r = await runReport(token, P168_PROP, {
      dateRanges: dateRange(start,end),
      metrics: [{ name:"activeUsers" },{ name:"sessions" },{ name:"eventCount" }],
    });
    const row = r.rows?.[0];
    return row ? {
      users:    +row.metricValues[0].value,
      sessions: +row.metricValues[1].value,
      events:   +row.metricValues[2].value,
    } : { users:0, sessions:0, events:0 };
  } catch { return { users:0, sessions:0, events:0 }; }
}

async function fetchP168Sources(token, start, end) {
  try {
    const r = await runReport(token, P168_PROP, {
      dateRanges: dateRange(start,end),
      dimensions: [{ name:"sessionSource" },{ name:"sessionMedium" }],
      metrics: [{ name:"sessions" },{ name:"activeUsers" }],
    });
    return (r.rows||[])
      .map(row => ({
        source:  row.dimensionValues[0].value,
        medium:  row.dimensionValues[1].value,
        sessions:+row.metricValues[0].value,
        users:   +row.metricValues[1].value,
      }))
      .filter(x=>x.sessions>0)
      .sort((a,b)=>b.sessions-a.sessions);
  } catch { return []; }
}

async function fetchP168Events(token, start, end) {
  try {
    const r = await runReport(token, P168_PROP, {
      dateRanges: dateRange(start,end),
      dimensions: [{ name:"eventName" }],
      metrics: [{ name:"eventCount" }],
    });
    return (r.rows||[])
      .map(row => ({ name:row.dimensionValues[0].value, count:+row.metricValues[0].value }))
      .filter(x=>x.count>0)
      .sort((a,b)=>b.count-a.count);
  } catch { return []; }
}

async function fetchP168ConvBySource(token, start, end) {
  const result = {};
  await Promise.all(CONV_EVENTS.map(async evt => {
    try {
      const r = await runReport(token, P168_PROP, {
        dateRanges: dateRange(start,end),
        dimensions: [{ name:"sessionSource" },{ name:"sessionMedium" }],
        metrics: [{ name:"eventCount" }],
        dimensionFilter: eventFilter(evt),
      });
      result[evt] = (r.rows||[])
        .map(row => ({
          source: row.dimensionValues[0].value,
          medium: row.dimensionValues[1].value,
          count:  +row.metricValues[0].value,
        }))
        .filter(x=>x.count>0)
        .sort((a,b)=>b.count-a.count);
    } catch { result[evt] = []; }
  }));
  return result;
}

async function fetchP168Contents(token, start, end) {
  try {
    const r = await runReport(token, P168_PROP, {
      dateRanges: dateRange(start,end),
      dimensions: [{ name:"sessionManualAdContent" }],
      metrics: [{ name:"sessions" },{ name:"activeUsers" }],
    });
    return (r.rows||[])
      .map(row => ({
        content:  row.dimensionValues[0].value,
        sessions: +row.metricValues[0].value,
        users:    +row.metricValues[1].value,
      }))
      .filter(x=>x.content && x.content!=="(not set)" && x.sessions>0)
      .sort((a,b)=>b.sessions-a.sessions);
  } catch { return []; }
}

// ── 整合入口 ──────────────────────────────────────────────────────────────────

async function fetchCustomRange(token, start, end) {
  const [kpis, accounts, contents, p168Kpis, p168Sources, p168Events, p168Conv, p168Contents] =
    await Promise.all([
      fetchYs89Kpis(token, start, end),
      fetchYs89Accounts(token, start, end),
      fetchYs89Contents(token, start, end),
      fetchP168Kpis(token, start, end),
      fetchP168Sources(token, start, end),
      fetchP168Events(token, start, end),
      fetchP168ConvBySource(token, start, end),
      fetchP168Contents(token, start, end),
    ]);

  return {
    custom:   true,
    range:    `${start}~${end}`,
    kpis,
    accounts,
    contents,
    picks168: {
      kpis:                    p168Kpis,
      sources:                 p168Sources,
      events:                  p168Events,
      conversions_by_source:   p168Conv,
      contents:                p168Contents,
    },
  };
}
