// POST /api/regs  { dim_value, registrations, note }
// P0 安全修正：加入 Bearer token 驗證，需在 CF Pages 設定 ADMIN_TOKEN Secret。
// 設定方式：CF Dashboard > ys89-seo-dashboard > Settings > Environment Variables > Secrets
const json = (d, s = 200) => new Response(JSON.stringify(d), {
  status: s,
  headers: { 'content-type': 'application/json; charset=utf-8', 'access-control-allow-origin': 'https://ys89-seo-dashboard.pages.dev' },
});

export async function onRequestOptions() {
  return new Response(null, {
    status: 204,
    headers: {
      'access-control-allow-origin': 'https://ys89-seo-dashboard.pages.dev',
      'access-control-allow-methods': 'POST, OPTIONS',
      'access-control-allow-headers': 'Authorization, Content-Type',
    },
  });
}

export async function onRequestPost({ request, env }) {
  const auth = request.headers.get('authorization') || '';
  const token = auth.replace(/^Bearer\s+/i, '').trim();
  if (!env.ADMIN_TOKEN || token !== env.ADMIN_TOKEN) {
    return json({ error: 'unauthorized' }, 401);
  }

  if (!env.DB) return json({ error: 'DB not bound' }, 500);
  const b = await request.json().catch(() => ({}));
  const dim = (b.dim_value || '').trim();
  if (!dim) return json({ error: 'dim_value required' }, 400);
  const regs = Math.max(0, parseInt(b.registrations, 10) || 0);
  await env.DB.prepare(
    `INSERT INTO manual_regs (dim_value, registrations, note, updated_at)
     VALUES (?,?,?,datetime('now'))
     ON CONFLICT(dim_value) DO UPDATE SET registrations=excluded.registrations,
       note=excluded.note, updated_at=datetime('now')`)
    .bind(dim, regs, (b.note || '').trim()).run();
  return json({ ok: true });
}
