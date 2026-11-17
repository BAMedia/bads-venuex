const ALLOWED_ORIGIN = "https://bamedia.agency";
const EMAIL_RE = /^[a-z0-9._%+'*-]+@[a-z0-9.-]+\.[a-z]{2,}$/i;
const MAX_EMAIL = 254;

function corsHeaders(origin) {
  const headers = {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
  if (origin === ALLOWED_ORIGIN) {
    headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN;
  }
  return headers;
}

function json(body, status, origin) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...corsHeaders(origin),
    },
  });
}

async function readPayload(request) {
  const ctype = request.headers.get("Content-Type") || "";
  if (ctype.includes("application/x-www-form-urlencoded") || ctype.includes("multipart/form-data")) {
    const form = await request.formData();
    return Object.fromEntries(form.entries());
  }
  return await request.json();
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      if (origin !== ALLOWED_ORIGIN) {
        return new Response(null, { status: 403 });
      }
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }

    if (request.method !== "POST" || url.pathname !== "/subscribe") {
      return json({ ok: false, error: "Not found" }, 404, origin);
    }

    if (origin && origin !== ALLOWED_ORIGIN) {
      return json({ ok: false, error: "Forbidden" }, 403, origin);
    }

    const ip = request.headers.get("CF-Connecting-IP") || "unknown";
    const { success } = await env.RATE_LIMITER.limit({ key: ip });
    if (!success) {
      return json({ ok: false, error: "Please try again in a minute." }, 429, origin);
    }

    let payload;
    try {
      payload = await readPayload(request);
    } catch {
      return json({ ok: false, error: "Please enter a valid email address." }, 400, origin);
    }

    const honey = String(payload.company || payload.website || payload.hp || "").trim();
    if (honey) {
      return json({ ok: true }, 200, origin);
    }

    const email = String(payload.email || "").trim().toLowerCase();
    if (!email || email.length > MAX_EMAIL || !EMAIL_RE.test(email)) {
      return json({ ok: false, error: "Please enter a valid email address." }, 400, origin);
    }

    const source = String(payload.source || "bads").trim().slice(0, 64) || "bads";
    const createdAt = new Date().toISOString();

    try {
      await env.DB.prepare(
        "INSERT OR IGNORE INTO subscribers (email, created_at, source, consent) VALUES (?, ?, ?, 1)",
      )
        .bind(email, createdAt, source)
        .run();
    } catch (err) {
      console.error(JSON.stringify({ event: "subscribe_error" }));
      return json({ ok: false, error: "Something went wrong. Please try again." }, 500, origin);
    }

    return json({ ok: true }, 200, origin);
  },
};
