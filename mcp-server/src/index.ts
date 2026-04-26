export interface Env {
  X_API_KEY: string;
  X_API_SECRET: string;
  X_ACCESS_TOKEN: string;
  X_ACCESS_TOKEN_SECRET: string;
  MCP_AUTH_TOKEN: string;
}

const PROTOCOL_VERSION = "2024-11-05";

const SERVER_INFO = {
  name: "x-mcp",
  version: "0.1.0",
};

const TOOLS = [
  {
    name: "post_tweet",
    description:
      "Post a tweet to X (formerly Twitter). Returns the URL of the posted tweet.",
    inputSchema: {
      type: "object",
      properties: {
        text: {
          type: "string",
          description: "The tweet body. Must be 280 characters or fewer.",
        },
      },
      required: ["text"],
    },
  },
];

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const pathToken = url.pathname.replace(/^\/+/, "").replace(/\/+$/, "");

    console.log(JSON.stringify({
      method: request.method,
      pathname: url.pathname,
      hasAuthHeader: request.headers.has("Authorization"),
      ua: request.headers.get("User-Agent"),
      accept: request.headers.get("Accept"),
    }));

    if (request.method === "GET" && pathToken === "") {
      return new Response("x-mcp ok", { status: 200 });
    }
    if (request.method !== "POST") {
      return new Response("Method not allowed", { status: 405 });
    }

    const headerToken = request.headers
      .get("Authorization")
      ?.replace(/^Bearer\s+/i, "");
    const provided = headerToken || pathToken;

    if (provided !== env.MCP_AUTH_TOKEN) {
      return jsonRpc(
        null,
        { error: { code: -32001, message: "Unauthorized" } },
        401,
      );
    }

    let body: JsonRpcRequest;
    try {
      body = (await request.json()) as JsonRpcRequest;
    } catch {
      return jsonRpc(null, { error: { code: -32700, message: "Parse error" } });
    }

    const { id = null, method, params } = body;
    console.log(JSON.stringify({ rpc: method, params }));

    try {
      switch (method) {
        case "initialize":
          return jsonRpc(id, {
            result: {
              protocolVersion: PROTOCOL_VERSION,
              capabilities: { tools: {} },
              serverInfo: SERVER_INFO,
            },
          });

        case "tools/list":
          return jsonRpc(id, { result: { tools: TOOLS } });

        case "tools/call":
          return await handleToolCall(id, params, env);

        case "notifications/initialized":
          return new Response(null, { status: 204 });

        default:
          return jsonRpc(id, {
            error: { code: -32601, message: `Method not found: ${method}` },
          });
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      console.log(JSON.stringify({ caught: message }));
      return jsonRpc(id, { error: { code: -32603, message } });
    }
  },
};

interface JsonRpcRequest {
  jsonrpc?: string;
  id?: string | number | null;
  method: string;
  params?: { name?: string; arguments?: Record<string, unknown> };
}

async function handleToolCall(
  id: string | number | null,
  params: JsonRpcRequest["params"],
  env: Env,
): Promise<Response> {
  const name = params?.name;
  const args = params?.arguments ?? {};

  if (name !== "post_tweet") {
    return jsonRpc(id, {
      error: { code: -32602, message: `Unknown tool: ${name}` },
    });
  }

  const text = args.text;
  if (typeof text !== "string" || text.length === 0) {
    return jsonRpc(id, {
      error: { code: -32602, message: "text must be a non-empty string" },
    });
  }
  if (text.length > 280) {
    return jsonRpc(id, {
      error: { code: -32602, message: "text exceeds 280 characters" },
    });
  }

  const url = await postTweet(text, env);
  return jsonRpc(id, {
    result: { content: [{ type: "text", text: `Posted: ${url}` }] },
  });
}

function jsonRpc(
  id: string | number | null,
  payload: { result?: unknown; error?: { code: number; message: string } },
  status = 200,
): Response {
  return new Response(
    JSON.stringify({ jsonrpc: "2.0", id, ...payload }),
    {
      status,
      headers: { "Content-Type": "application/json" },
    },
  );
}

async function postTweet(text: string, env: Env): Promise<string> {
  const url = "https://api.x.com/2/tweets";
  const authHeader = await buildOAuthHeader("POST", url, env);

  console.log(JSON.stringify({ x_api: "request", textLen: text.length }));

  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: authHeader,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ text }),
  });

  const respText = await res.text();
  console.log(JSON.stringify({ x_api: "response", status: res.status, body: respText.slice(0, 500) }));

  if (!res.ok) {
    throw new Error(`X API ${res.status}: ${respText}`);
  }

  let data: { data?: { id?: string } };
  try {
    data = JSON.parse(respText);
  } catch {
    throw new Error(`X API non-JSON response: ${respText.slice(0, 200)}`);
  }
  const tweetId = data.data?.id;
  if (!tweetId) {
    throw new Error(`Unexpected X API response: ${respText.slice(0, 200)}`);
  }
  return `https://x.com/i/web/status/${tweetId}`;
}

async function buildOAuthHeader(
  method: string,
  url: string,
  env: Env,
): Promise<string> {
  const oauthParams: Record<string, string> = {
    oauth_consumer_key: env.X_API_KEY,
    oauth_nonce: generateNonce(),
    oauth_signature_method: "HMAC-SHA1",
    oauth_timestamp: Math.floor(Date.now() / 1000).toString(),
    oauth_token: env.X_ACCESS_TOKEN,
    oauth_version: "1.0",
  };

  oauthParams.oauth_signature = await sign(
    method,
    url,
    oauthParams,
    env.X_API_SECRET,
    env.X_ACCESS_TOKEN_SECRET,
  );

  const headerParts = Object.entries(oauthParams)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${rfc3986(k)}="${rfc3986(v)}"`);

  return `OAuth ${headerParts.join(", ")}`;
}

async function sign(
  method: string,
  url: string,
  oauthParams: Record<string, string>,
  consumerSecret: string,
  tokenSecret: string,
): Promise<string> {
  const paramString = Object.entries(oauthParams)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${rfc3986(k)}=${rfc3986(v)}`)
    .join("&");

  const baseString = [
    method.toUpperCase(),
    rfc3986(url),
    rfc3986(paramString),
  ].join("&");

  const signingKey = `${rfc3986(consumerSecret)}&${rfc3986(tokenSecret)}`;

  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(signingKey),
    { name: "HMAC", hash: "SHA-1" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(baseString),
  );
  return base64(sig);
}

function generateNonce(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function rfc3986(s: string): string {
  return encodeURIComponent(s).replace(
    /[!*'()]/g,
    (c) => `%${c.charCodeAt(0).toString(16).toUpperCase()}`,
  );
}

function base64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary);
}
