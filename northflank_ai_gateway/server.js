const http = require("http");
const crypto = require("crypto");
const { createDeviceBindingsStoreFromEnv } = require("./device_bindings_store");

const PORT = parseInt(process.env.PORT || "3000", 10);
const ACCESS_TOKEN_TTL_SEC = Math.max(300, parseInt(process.env.ACCESS_TOKEN_TTL_SEC || "604800", 10));
const APP_TOKEN_SECRET = String(process.env.APP_TOKEN_SECRET || "").trim();
const GROQ_API_BASE_URL = String(process.env.GROQ_API_BASE_URL || "https://api.groq.com/openai/v1").trim().replace(/\/+$/, "");
const GROQ_KEY_COOLDOWN_SEC = Math.max(5, parseInt(process.env.GROQ_KEY_COOLDOWN_SEC || "35", 10));
const GROQ_INVALID_KEY_COOLDOWN_SEC = Math.max(60, parseInt(process.env.GROQ_INVALID_KEY_COOLDOWN_SEC || "3600", 10));
const GROQ_NETWORK_ERROR_COOLDOWN_SEC = Math.max(5, parseInt(process.env.GROQ_NETWORK_ERROR_COOLDOWN_SEC || "20", 10));

let groqCursor = 0;
const groqKeyStateMap = new Map();
let geminiCursor = 0;
const geminiKeyStateMap = new Map();
const GEMINI_API_BASE_URL = String(process.env.GEMINI_API_BASE_URL || "https://generativelanguage.googleapis.com/v1beta/openai").trim().replace(/\/+$/, "");
const GEMINI_KEY_COOLDOWN_SEC = Math.max(5, parseInt(process.env.GEMINI_KEY_COOLDOWN_SEC || "35", 10));
const GEMINI_INVALID_KEY_COOLDOWN_SEC = Math.max(60, parseInt(process.env.GEMINI_INVALID_KEY_COOLDOWN_SEC || "3600", 10));
const GEMINI_NETWORK_ERROR_COOLDOWN_SEC = Math.max(5, parseInt(process.env.GEMINI_NETWORK_ERROR_COOLDOWN_SEC || "20", 10));
const ANY_API_BASE_URL = String(process.env.ANY_API_BASE_URL || "https://api.anyapi.ai/v1").trim().replace(/\/+$/, "");
const ANY_KEY_COOLDOWN_SEC = Math.max(5, parseInt(process.env.ANY_KEY_COOLDOWN_SEC || "35", 10));
const ANY_INVALID_KEY_COOLDOWN_SEC = Math.max(60, parseInt(process.env.ANY_INVALID_KEY_COOLDOWN_SEC || "3600", 10));
const ANY_NETWORK_ERROR_COOLDOWN_SEC = Math.max(5, parseInt(process.env.ANY_NETWORK_ERROR_COOLDOWN_SEC || "20", 10));
const NVIDIA_API_BASE_URL = String(process.env.NVIDIA_API_BASE_URL || "https://integrate.api.nvidia.com/v1").trim().replace(/\/+$/, "");
const NVIDIA_KEY_COOLDOWN_SEC = Math.max(5, parseInt(process.env.NVIDIA_KEY_COOLDOWN_SEC || "35", 10));
const NVIDIA_INVALID_KEY_COOLDOWN_SEC = Math.max(60, parseInt(process.env.NVIDIA_INVALID_KEY_COOLDOWN_SEC || "3600", 10));
const NVIDIA_NETWORK_ERROR_COOLDOWN_SEC = Math.max(5, parseInt(process.env.NVIDIA_NETWORK_ERROR_COOLDOWN_SEC || "20", 10));
let anyCursor = 0;
const anyKeyStateMap = new Map();
let nvidiaCursor = 0;
const nvidiaKeyStateMap = new Map();
const bindingsStore = createDeviceBindingsStoreFromEnv(process.env);
const bindingsStoreInfo = bindingsStore.describe();

function nowSeconds() {
  return Math.floor(Date.now() / 1000);
}

function base64Url(input) {
  return Buffer.from(input)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function hmacBase64Url(secret, text) {
  return crypto.createHmac("sha256", secret).update(text).digest("base64url");
}

function sha256Hex(text) {
  return crypto.createHash("sha256").update(text).digest("hex");
}

function stableDeviceKeyHash(deviceKey) {
  return hmacBase64Url(APP_TOKEN_SECRET, String(deviceKey || "").trim());
}

function getGroqKeys() {
  const keys = [];
  const seen = new Set();
  function pushUniqueKey(rawValue, label) {
    const key = String(rawValue || "").trim();
    if (!key || seen.has(key)) {
      return;
    }
    seen.add(key);
    keys.push({
      value: key,
      label: String(label || `key_${keys.length + 1}`),
    });
  }
  const rawList = String(process.env.GROQ_API_KEYS || "").trim();
  if (rawList) {
    let offset = 0;
    for (const part of rawList.split(/[,\s;]+/)) {
      offset += 1;
      pushUniqueKey(part, `GROQ_API_KEYS_${offset}`);
    }
  }
  for (const envName of ["GROQ_API_KEY", "GROQ_KEY_1", "GROQ_KEY_2", "GROQ_KEY_3", "GROQ_KEY_4", "GROQ_KEY_5"]) {
    pushUniqueKey(process.env[envName], envName);
  }
  return keys.map((item, index) => ({ ...item, index }));
}

function getGeminiKeys() {
  const keys = [];
  const seen = new Set();
  function pushUniqueKey(rawValue, label) {
    const key = String(rawValue || "").trim();
    if (!key || seen.has(key)) {
      return;
    }
    seen.add(key);
    keys.push({
      value: key,
      label: String(label || `key_${keys.length + 1}`),
    });
  }
  const rawList = String(process.env.GEMINI_API_KEYS || "").trim();
  if (rawList) {
    let offset = 0;
    for (const part of rawList.split(/[,\s;]+/)) {
      offset += 1;
      pushUniqueKey(part, `GEMINI_API_KEYS_${offset}`);
    }
  }
  for (const envName of ["GEMINI_API_KEY", "GEMINI_KEY_1", "GEMINI_KEY_2", "GEMINI_KEY_3", "GEMINI_KEY_4", "GEMINI_KEY_5"]) {
    pushUniqueKey(process.env[envName], envName);
  }
  return keys.map((item, index) => ({ ...item, index }));
}

function getAnyKeys() {
  const keys = [];
  const seen = new Set();
  function pushUniqueKey(rawValue, label) {
    const key = String(rawValue || "").trim();
    if (!key || seen.has(key)) return;
    seen.add(key);
    keys.push({ value: key, label: String(label || `key_${keys.length + 1}`) });
  }
  const rawList = String(process.env.ANY_API_KEYS || "").trim();
  if (rawList) {
    let offset = 0;
    for (const part of rawList.split(/[,\s;]+/)) {
      offset += 1;
      pushUniqueKey(part, `ANY_API_KEYS_${offset}`);
    }
  }
  for (const envName of ["ANY_KEY", "ANY_API_KEY", "ANY_KEY_1", "ANY_KEY_2"]) {
    pushUniqueKey(process.env[envName], envName);
  }
  return keys.map((item, index) => ({ ...item, index }));
}

function getNvidiaKeys() {
  const keys = [];
  const seen = new Set();
  function pushUniqueKey(rawValue, label) {
    const key = String(rawValue || "").trim();
    if (!key || seen.has(key)) return;
    seen.add(key);
    keys.push({ value: key, label: String(label || `key_${keys.length + 1}`) });
  }
  const rawList = String(process.env.NVIDIA_API_KEYS || "").trim();
  if (rawList) {
    let offset = 0;
    for (const part of rawList.split(/[,\s;]+/)) {
      offset += 1;
      pushUniqueKey(part, `NVIDIA_API_KEYS_${offset}`);
    }
  }
  for (const envName of ["NVIDIA_KEY", "NVIDIA_API_KEY", "NVIDIA_KEY_1", "NVIDIA_KEY_2"]) {
    pushUniqueKey(process.env[envName], envName);
  }
  return keys.map((item, index) => ({ ...item, index }));
}

function keyStateId(keyConfig) {
  return sha256Hex(String((keyConfig || {}).value || ""));
}

function getGroqKeyState(keyConfig) {
  const stateId = keyStateId(keyConfig);
  if (!groqKeyStateMap.has(stateId)) {
    groqKeyStateMap.set(stateId, {
      stateId,
      label: keyConfig.label,
      status: "ready",
      cooldownUntil: 0,
      lastStatusCode: 0,
      lastError: "",
      lastUsedAt: "",
      lastSuccessAt: "",
      lastFailureAt: "",
      successCount: 0,
      failCount: 0,
    });
  }
  return groqKeyStateMap.get(stateId);
}

function markGroqKeySuccess(keyConfig) {
  const state = getGroqKeyState(keyConfig);
  const nowIso = new Date().toISOString();
  state.status = "ready";
  state.cooldownUntil = 0;
  state.lastStatusCode = 200;
  state.lastError = "";
  state.lastUsedAt = nowIso;
  state.lastSuccessAt = nowIso;
  state.successCount += 1;
}

function markGroqKeyFailure(keyConfig, statusCode, errorMessage, cooldownSec) {
  const state = getGroqKeyState(keyConfig);
  const nowIso = new Date().toISOString();
  const cooldownUntil = cooldownSec > 0 ? nowSeconds() + cooldownSec : 0;
  state.status = cooldownUntil > nowSeconds() ? "cooling_down" : "ready";
  state.cooldownUntil = cooldownUntil;
  state.lastStatusCode = Number(statusCode || 0);
  state.lastError = String(errorMessage || "").slice(0, 500);
  state.lastUsedAt = nowIso;
  state.lastFailureAt = nowIso;
  state.failCount += 1;
}

function groqKeyCooldownRemaining(state) {
  const remaining = Math.max(0, Number(state.cooldownUntil || 0) - nowSeconds());
  return remaining;
}

function listGroqKeyHealth() {
  const keys = getGroqKeys();
  return keys.map((keyConfig) => {
    const state = getGroqKeyState(keyConfig);
    const cooldownRemainingSec = groqKeyCooldownRemaining(state);
    return {
      index: keyConfig.index + 1,
      label: keyConfig.label,
      status: cooldownRemainingSec > 0 ? "cooling_down" : "ready",
      cooldown_remaining_sec: cooldownRemainingSec,
      last_status_code: state.lastStatusCode || 0,
      last_error: state.lastError || "",
      last_used_at: state.lastUsedAt || "",
      last_success_at: state.lastSuccessAt || "",
      last_failure_at: state.lastFailureAt || "",
      success_count: state.successCount || 0,
      fail_count: state.failCount || 0,
    };
  });
}

function orderedGroqKeys(keys) {
  const total = keys.length;
  if (!total) {
    return [];
  }
  const startIndex = groqCursor % total;
  const ready = [];
  const cooling = [];
  for (let offset = 0; offset < total; offset += 1) {
    const idx = (startIndex + offset) % total;
    const keyConfig = keys[idx];
    const state = getGroqKeyState(keyConfig);
    if (groqKeyCooldownRemaining(state) > 0) {
      cooling.push(keyConfig);
    } else {
      ready.push(keyConfig);
    }
  }
  return ready.concat(cooling);
}

function getGeminiKeyState(keyConfig) {
  const stateId = keyStateId(keyConfig);
  if (!geminiKeyStateMap.has(stateId)) {
    geminiKeyStateMap.set(stateId, {
      stateId,
      label: keyConfig.label,
      status: "ready",
      cooldownUntil: 0,
      lastStatusCode: 0,
      lastError: "",
      lastUsedAt: "",
      lastSuccessAt: "",
      lastFailureAt: "",
      successCount: 0,
      failCount: 0,
    });
  }
  return geminiKeyStateMap.get(stateId);
}

function markGeminiKeySuccess(keyConfig) {
  const state = getGeminiKeyState(keyConfig);
  const nowIso = new Date().toISOString();
  state.status = "ready";
  state.cooldownUntil = 0;
  state.lastStatusCode = 200;
  state.lastError = "";
  state.lastUsedAt = nowIso;
  state.lastSuccessAt = nowIso;
  state.successCount += 1;
}

function markGeminiKeyFailure(keyConfig, statusCode, errorMessage, cooldownSec) {
  const state = getGeminiKeyState(keyConfig);
  const nowIso = new Date().toISOString();
  const cooldownUntil = cooldownSec > 0 ? nowSeconds() + cooldownSec : 0;
  state.status = cooldownUntil > nowSeconds() ? "cooling_down" : "ready";
  state.cooldownUntil = cooldownUntil;
  state.lastStatusCode = Number(statusCode || 0);
  state.lastError = String(errorMessage || "").slice(0, 500);
  state.lastUsedAt = nowIso;
  state.lastFailureAt = nowIso;
  state.failCount += 1;
}

function geminiKeyCooldownRemaining(state) {
  const remaining = Math.max(0, Number(state.cooldownUntil || 0) - nowSeconds());
  return remaining;
}

function listGeminiKeyHealth() {
  const keys = getGeminiKeys();
  return keys.map((keyConfig) => {
    const state = getGeminiKeyState(keyConfig);
    const cooldownRemainingSec = geminiKeyCooldownRemaining(state);
    return {
      index: keyConfig.index + 1,
      label: keyConfig.label,
      status: cooldownRemainingSec > 0 ? "cooling_down" : "ready",
      cooldown_remaining_sec: cooldownRemainingSec,
      last_status_code: state.lastStatusCode || 0,
      last_error: state.lastError || "",
      last_used_at: state.lastUsedAt || "",
      last_success_at: state.lastSuccessAt || "",
      last_failure_at: state.lastFailureAt || "",
      success_count: state.successCount || 0,
      fail_count: state.failCount || 0,
    };
  });
}

function orderedGeminiKeys(keys) {
  const total = keys.length;
  if (!total) {
    return [];
  }
  const startIndex = geminiCursor % total;
  const ready = [];
  const cooling = [];
  for (let offset = 0; offset < total; offset += 1) {
    const idx = (startIndex + offset) % total;
    const keyConfig = keys[idx];
    const state = getGeminiKeyState(keyConfig);
    if (geminiKeyCooldownRemaining(state) > 0) {
      cooling.push(keyConfig);
    } else {
      ready.push(keyConfig);
    }
  }
  return ready.concat(cooling);
}

function getAnyKeyState(keyConfig) {
  const stateId = keyStateId(keyConfig);
  if (!anyKeyStateMap.has(stateId)) {
    anyKeyStateMap.set(stateId, { stateId, label: keyConfig.label, status: "ready", cooldownUntil: 0, lastStatusCode: 0, lastError: "", lastUsedAt: "", lastSuccessAt: "", lastFailureAt: "", successCount: 0, failCount: 0 });
  }
  return anyKeyStateMap.get(stateId);
}
function markAnyKeySuccess(keyConfig) {
  const state = getAnyKeyState(keyConfig);
  const nowIso = new Date().toISOString();
  state.status = "ready"; state.cooldownUntil = 0; state.lastStatusCode = 200; state.lastError = ""; state.lastUsedAt = nowIso; state.lastSuccessAt = nowIso; state.successCount += 1;
}
function markAnyKeyFailure(keyConfig, statusCode, errorMessage, cooldownSec) {
  const state = getAnyKeyState(keyConfig);
  const nowIso = new Date().toISOString();
  const cooldownUntil = cooldownSec > 0 ? nowSeconds() + cooldownSec : 0;
  state.status = cooldownUntil > nowSeconds() ? "cooling_down" : "ready"; state.cooldownUntil = cooldownUntil; state.lastStatusCode = Number(statusCode || 0); state.lastError = String(errorMessage || "").slice(0, 500); state.lastUsedAt = nowIso; state.lastFailureAt = nowIso; state.failCount += 1;
}
function anyKeyCooldownRemaining(state) { return Math.max(0, Number(state.cooldownUntil || 0) - nowSeconds()); }
function listAnyKeyHealth() {
  const keys = getAnyKeys();
  return keys.map((keyConfig) => {
    const state = getAnyKeyState(keyConfig);
    const cooldownRemainingSec = anyKeyCooldownRemaining(state);
    return { index: keyConfig.index + 1, label: keyConfig.label, status: cooldownRemainingSec > 0 ? "cooling_down" : "ready", cooldown_remaining_sec: cooldownRemainingSec, last_status_code: state.lastStatusCode || 0, last_error: state.lastError || "", last_used_at: state.lastUsedAt || "", last_success_at: state.lastSuccessAt || "", last_failure_at: state.lastFailureAt || "", success_count: state.successCount || 0, fail_count: state.failCount || 0 };
  });
}
function orderedAnyKeys(keys) {
  const total = keys.length; if (!total) return [];
  const startIndex = anyCursor % total; const ready = []; const cooling = [];
  for (let offset = 0; offset < total; offset += 1) {
    const idx = (startIndex + offset) % total; const keyConfig = keys[idx]; const state = getAnyKeyState(keyConfig);
    if (anyKeyCooldownRemaining(state) > 0) cooling.push(keyConfig); else ready.push(keyConfig);
  }
  return ready.concat(cooling);
}
function getNvidiaKeyState(keyConfig) {
  const stateId = keyStateId(keyConfig);
  if (!nvidiaKeyStateMap.has(stateId)) {
    nvidiaKeyStateMap.set(stateId, { stateId, label: keyConfig.label, status: "ready", cooldownUntil: 0, lastStatusCode: 0, lastError: "", lastUsedAt: "", lastSuccessAt: "", lastFailureAt: "", successCount: 0, failCount: 0 });
  }
  return nvidiaKeyStateMap.get(stateId);
}
function markNvidiaKeySuccess(keyConfig) {
  const state = getNvidiaKeyState(keyConfig);
  const nowIso = new Date().toISOString();
  state.status = "ready"; state.cooldownUntil = 0; state.lastStatusCode = 200; state.lastError = ""; state.lastUsedAt = nowIso; state.lastSuccessAt = nowIso; state.successCount += 1;
}
function markNvidiaKeyFailure(keyConfig, statusCode, errorMessage, cooldownSec) {
  const state = getNvidiaKeyState(keyConfig);
  const nowIso = new Date().toISOString();
  const cooldownUntil = cooldownSec > 0 ? nowSeconds() + cooldownSec : 0;
  state.status = cooldownUntil > nowSeconds() ? "cooling_down" : "ready"; state.cooldownUntil = cooldownUntil; state.lastStatusCode = Number(statusCode || 0); state.lastError = String(errorMessage || "").slice(0, 500); state.lastUsedAt = nowIso; state.lastFailureAt = nowIso; state.failCount += 1;
}
function nvidiaKeyCooldownRemaining(state) { return Math.max(0, Number(state.cooldownUntil || 0) - nowSeconds()); }
function listNvidiaKeyHealth() {
  const keys = getNvidiaKeys();
  return keys.map((keyConfig) => {
    const state = getNvidiaKeyState(keyConfig);
    const cooldownRemainingSec = nvidiaKeyCooldownRemaining(state);
    return { index: keyConfig.index + 1, label: keyConfig.label, status: cooldownRemainingSec > 0 ? "cooling_down" : "ready", cooldown_remaining_sec: cooldownRemainingSec, last_status_code: state.lastStatusCode || 0, last_error: state.lastError || "", last_used_at: state.lastUsedAt || "", last_success_at: state.lastSuccessAt || "", last_failure_at: state.lastFailureAt || "", success_count: state.successCount || 0, fail_count: state.failCount || 0 };
  });
}
function orderedNvidiaKeys(keys) {
  const total = keys.length; if (!total) return [];
  const startIndex = nvidiaCursor % total; const ready = []; const cooling = [];
  for (let offset = 0; offset < total; offset += 1) {
    const idx = (startIndex + offset) % total; const keyConfig = keys[idx]; const state = getNvidiaKeyState(keyConfig);
    if (nvidiaKeyCooldownRemaining(state) > 0) cooling.push(keyConfig); else ready.push(keyConfig);
  }
  return ready.concat(cooling);
}

function sanitizeString(value, maxLen) {
  return String(value || "").trim().slice(0, maxLen);
}

function withCors(headers) {
  return {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET,POST,OPTIONS",
    "access-control-allow-headers": "authorization,content-type,x-device-id,x-device-key,x-machine-fingerprint",
    ...headers,
  };
}

function sendJson(res, statusCode, data) {
  res.writeHead(statusCode, withCors({ "content-type": "application/json; charset=utf-8" }));
  res.end(JSON.stringify(data));
}

function sendText(res, statusCode, text) {
  res.writeHead(statusCode, withCors({ "content-type": "text/plain; charset=utf-8" }));
  res.end(String(text || ""));
}

async function readJsonBody(req) {
  const chunks = [];
  for await (const chunk of req) {
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString("utf8");
  if (!raw.trim()) {
    return {};
  }
  return JSON.parse(raw);
}

function issueAccessToken(binding) {
  const payload = {
    sub: binding.deviceId,
    dk: binding.deviceKeyHash,
    fp: binding.machineFingerprint,
    iat: nowSeconds(),
    exp: nowSeconds() + ACCESS_TOKEN_TTL_SEC,
  };
  const payloadEncoded = base64Url(JSON.stringify(payload));
  const sig = hmacBase64Url(APP_TOKEN_SECRET, payloadEncoded);
  return `${payloadEncoded}.${sig}`;
}

function verifyAccessToken(token) {
  const raw = String(token || "").trim();
  const parts = raw.split(".");
  if (parts.length !== 2) {
    return { ok: false, error: "invalid_token" };
  }
  const [payloadEncoded, sig] = parts;
  const expected = hmacBase64Url(APP_TOKEN_SECRET, payloadEncoded);
  if (!crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected))) {
    return { ok: false, error: "invalid_signature" };
  }
  try {
    const payload = JSON.parse(Buffer.from(payloadEncoded, "base64url").toString("utf8"));
    if (!payload || typeof payload !== "object") {
      return { ok: false, error: "invalid_payload" };
    }
    if (Number(payload.exp || 0) <= nowSeconds()) {
      return { ok: false, error: "token_expired" };
    }
    return { ok: true, payload };
  } catch (_error) {
    return { ok: false, error: "invalid_payload" };
  }
}

async function registerDevice(body) {
  const deviceId = sanitizeString(body.device_id, 128);
  const deviceKey = sanitizeString(body.device_key, 256);
  const machineFingerprint = sanitizeString(body.machine_fingerprint, 256);
  const platformName = sanitizeString(body.platform, 256);
  const appId = sanitizeString(body.app_id, 128) || "eduplay-studio";

  if (!deviceId.startsWith("dev_") || deviceId.length < 12) {
    return { status: 400, body: { error: { message: "bad_device_id" } } };
  }
  if (!deviceKey.startsWith("dkey_") || deviceKey.length < 20) {
    return { status: 400, body: { error: { message: "bad_device_key" } } };
  }
  if (!machineFingerprint.startsWith("mfp_") || machineFingerprint.length < 20) {
    return { status: 400, body: { error: { message: "bad_machine_fingerprint" } } };
  }

  const deviceKeyHash = stableDeviceKeyHash(deviceKey);
  const existing = await bindingsStore.getByDeviceId(deviceId);
  let bindingStatus = "registered";
  const currentIso = new Date().toISOString();
  const existingByDeviceKeyHash = await bindingsStore.getByDeviceKeyHash(deviceKeyHash);

  if (existingByDeviceKeyHash && existingByDeviceKeyHash.deviceId !== deviceId) {
    return { status: 403, body: { error: { message: "device_key_already_bound" } } };
  }

  if (existing) {
    const sameBinding =
      existing.deviceKeyHash === deviceKeyHash &&
      existing.machineFingerprint === machineFingerprint;
    if (!sameBinding) {
      return { status: 403, body: { error: { message: "device_binding_mismatch" } } };
    }
    bindingStatus = "known";
  }

  const savedBinding = await bindingsStore.upsertBinding({
    deviceId,
    deviceKeyHash,
    machineFingerprint,
    platform: platformName,
    appId,
    createdAt: existing && existing.createdAt ? existing.createdAt : currentIso,
    lastSeenAt: currentIso,
  });

  return {
    status: 200,
    body: {
      access_token: issueAccessToken(savedBinding),
      binding_status: bindingStatus,
      device_key_accepted: true,
    },
  };
}

async function verifyDeviceHeaders(req) {
  const auth = String(req.headers.authorization || "").trim();
  const deviceId = sanitizeString(req.headers["x-device-id"], 128);
  const deviceKey = sanitizeString(req.headers["x-device-key"], 256);
  const machineFingerprint = sanitizeString(req.headers["x-machine-fingerprint"], 256);

  if (!auth.startsWith("Bearer ")) {
    return { ok: false, status: 401, error: "missing_token" };
  }
  if (!deviceId || !deviceKey || !machineFingerprint) {
    return { ok: false, status: 401, error: "missing_device_headers" };
  }

  const tokenCheck = verifyAccessToken(auth.slice("Bearer ".length));
  if (!tokenCheck.ok) {
    return { ok: false, status: 401, error: tokenCheck.error };
  }

  const binding = await bindingsStore.getByDeviceId(deviceId);
  if (!binding) {
    return { ok: false, status: 401, error: "unknown_device" };
  }

  const deviceKeyHash = stableDeviceKeyHash(deviceKey);
  const payload = tokenCheck.payload;
  const bindingMatches =
    binding.deviceKeyHash === deviceKeyHash &&
    binding.machineFingerprint === machineFingerprint &&
    payload.sub === deviceId &&
    payload.dk === deviceKeyHash &&
    payload.fp === machineFingerprint;

  if (!bindingMatches) {
    return { ok: false, status: 403, error: "device_binding_mismatch" };
  }

  await bindingsStore.touchBinding(deviceId, new Date().toISOString());

  return { ok: true };
}

function mapGroqModelToGemini(originalModel) {
  const m = String(originalModel || "").toLowerCase();
  if (m.includes("gemini")) {
    return String(originalModel || "").trim(); // đã là Gemini, giữ nguyên
  }
  // Gemini 2.5 Flash-Lite cho chat thường (LIGHT 20B), Flash cho suy luận/tìm kiếm (HEAVY 120B, COMPOUND)
  if (m.includes("120b") || m.includes("compound") || m.includes("heavy") || m.includes("reason") || m.includes("search")) {
    return "gemini-2.5-flash";
  }
  if (m.includes("qwen") || m.includes("vision")) {
    return "gemini-2.5-flash"; // Gemini cũng hỗ trợ vision
  }
  return "gemini-2.5-flash-lite";
}

async function forwardToGemini(payload) {
  const geminiKeys = getGeminiKeys();
  if (!geminiKeys.length) {
    return null; // Không có Gemini key, để Groq trả lỗi như cũ
  }

  const originalModel = sanitizeString(payload.model, 120) || "openai/gpt-oss-20b";
  const geminiModel = mapGroqModelToGemini(originalModel);

  const requestBody = {
    model: geminiModel,
    messages: Array.isArray(payload.messages) ? payload.messages : [],
    temperature: payload.temperature ?? 0.2,
    max_tokens: payload.max_tokens ?? 1024,
    stream: false,
  };

  const orderedKeys = orderedGeminiKeys(geminiKeys);
  const readyCount = orderedKeys.filter((keyConfig) => geminiKeyCooldownRemaining(getGeminiKeyState(keyConfig)) === 0).length;
  if (!readyCount) {
    return null; // Để Groq trả 503, không chặn
  }

  for (let offset = 0; offset < orderedKeys.length; offset += 1) {
    const keyConfig = orderedKeys[offset];
    if (geminiKeyCooldownRemaining(getGeminiKeyState(keyConfig)) > 0) {
      continue;
    }
    const apiKey = keyConfig.value;
    try {
      const upstream = await fetch(`${GEMINI_API_BASE_URL}/chat/completions`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      const responseText = await upstream.text();
      if (upstream.ok) {
        let parsed;
        try {
          parsed = JSON.parse(responseText);
        } catch (_error) {
          parsed = { raw: responseText };
        }
        markGeminiKeySuccess(keyConfig);
        geminiCursor = (keyConfig.index + 1) % geminiKeys.length;
        // Đánh dấu là từ Gemini để debug
        if (parsed && typeof parsed === "object" && parsed.choices && parsed.choices[0]) {
          try {
            parsed._via = "gemini";
            parsed._gemini_model = geminiModel;
            parsed._original_model = originalModel;
          } catch (_e) {}
        }
        console.log(`[Gemini] ${keyConfig.label} success with ${geminiModel} (from ${originalModel})`);
        return { status: upstream.status, body: parsed };
      }

      let parsedError;
      try {
        parsedError = JSON.parse(responseText);
      } catch (_error) {
        parsedError = { error: { message: responseText || "upstream_error" } };
      }
      const detail = String(parsedError?.error?.message || responseText || "upstream_error");
      let cooldownSec = 0;
      if (upstream.status === 429) {
        let retrySec = GEMINI_KEY_COOLDOWN_SEC;
        try {
          const m = String(detail || "").match(/try again in ([0-9]+(?:\.[0-9]+)?)s/i);
          if (m) {
            const parsed = parseFloat(m[1]);
            if (!isNaN(parsed) && parsed > 0) {
              retrySec = Math.ceil(parsed + 3);
              retrySec = Math.max(5, Math.min(retrySec, 60));
            }
          }
        } catch (_e) {}
        cooldownSec = retrySec;
      } else if (upstream.status === 401 || upstream.status === 403) {
        cooldownSec = GEMINI_INVALID_KEY_COOLDOWN_SEC;
      }
      if (cooldownSec > 0) {
        markGeminiKeyFailure(keyConfig, upstream.status, detail, cooldownSec);
      } else {
        markGeminiKeyFailure(keyConfig, upstream.status, detail, 0);
      }
      if ([401, 403, 429].includes(upstream.status) && offset < orderedKeys.length - 1) {
        console.warn(`[Gemini] ${keyConfig.label} failed with ${upstream.status}, cooldown=${cooldownSec}s`);
        continue;
      }
      geminiCursor = (keyConfig.index + 1) % geminiKeys.length;
      // Nếu Gemini cũng lỗi 429/500, trả về để Groq có thể thử lại hoặc trả cho client
      // Nhưng vì đây là fallback, ta trả luôn lỗi Gemini
      return { status: upstream.status, body: parsedError };
    } catch (error) {
      const detail = error && error.message ? error.message : "upstream_error";
      markGeminiKeyFailure(keyConfig, 502, detail, GEMINI_NETWORK_ERROR_COOLDOWN_SEC);
      if (offset < orderedKeys.length - 1) {
        console.warn(`[Gemini] ${keyConfig.label} network error, cooldown=${GEMINI_NETWORK_ERROR_COOLDOWN_SEC}s`);
        continue;
      }
      geminiCursor = (keyConfig.index + 1) % geminiKeys.length;
      return {
        status: 502,
        body: {
          error: {
            message: detail,
            type: "network_error",
          },
        },
      };
    }
  }

  return null;
}

function mapGroqModelToAny(originalModel) {
  const m = String(originalModel || "").toLowerCase();
  if (m.includes("120b") || m.includes("heavy") || m.includes("nemotron") || m.includes("30b") || m.includes("reason")) {
    return "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free";
  }
  return "google/gemma-4-26b-a4b-it:free";
}
async function forwardToAny(payload) {
  const anyKeys = getAnyKeys();
  if (!anyKeys.length) return null;
  const originalModel = sanitizeString(payload.model, 120) || "openai/gpt-oss-20b";
  const anyModel = mapGroqModelToAny(originalModel);
  const requestBody = { model: anyModel, messages: Array.isArray(payload.messages) ? payload.messages : [], temperature: payload.temperature ?? 0.2, max_tokens: payload.max_tokens ?? 1024, stream: false };
  const orderedKeys = orderedAnyKeys(anyKeys);
  const readyCount = orderedKeys.filter((kc) => anyKeyCooldownRemaining(getAnyKeyState(kc)) === 0).length;
  if (!readyCount) return null;
  for (let offset = 0; offset < orderedKeys.length; offset += 1) {
    const keyConfig = orderedKeys[offset];
    if (anyKeyCooldownRemaining(getAnyKeyState(keyConfig)) > 0) continue;
    const apiKey = keyConfig.value;
    try {
      const upstream = await fetch(`${ANY_API_BASE_URL}/chat/completions`, {
        method: "POST",
        headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });
      const text = await upstream.text();
      if (upstream.ok) {
        let parsed; try { parsed = JSON.parse(text); } catch (_e) { parsed = { raw: text }; }
        markAnyKeySuccess(keyConfig);
        anyCursor = (keyConfig.index + 1) % anyKeys.length;
        if (parsed && typeof parsed === "object" && parsed.choices && parsed.choices[0]) {
          try { parsed._via = "anyapi"; parsed._any_model = anyModel; parsed._original_model = originalModel; } catch (_e) {}
        }
        console.log(`[Any-API] ${keyConfig.label} success with ${anyModel} (from ${originalModel})`);
        return { status: upstream.status, body: parsed };
      }
      let parsedError; try { parsedError = JSON.parse(text); } catch (_e) { parsedError = { error: { message: text || "upstream_error" } }; }
      const detail = String(parsedError?.error?.message || text || "upstream_error");
      let cooldownSec = 0;
      if (upstream.status === 429) {
        let retrySec = ANY_KEY_COOLDOWN_SEC;
        try {
          const m = String(detail || "").match(/try again in ([0-9]+(?:\.[0-9]+)?)s/i);
          if (m) { const p = parseFloat(m[1]); if (!isNaN(p) && p > 0) { retrySec = Math.ceil(p + 3); retrySec = Math.max(5, Math.min(retrySec, 60)); } }
        } catch (_e) {}
        cooldownSec = retrySec;
      } else if (upstream.status === 401 || upstream.status === 403) { cooldownSec = ANY_INVALID_KEY_COOLDOWN_SEC; }
      if (cooldownSec > 0) markAnyKeyFailure(keyConfig, upstream.status, detail, cooldownSec); else markAnyKeyFailure(keyConfig, upstream.status, detail, 0);
      if ([401, 403, 429].includes(upstream.status) && offset < orderedKeys.length - 1) { console.warn(`[Any-API] ${keyConfig.label} failed ${upstream.status}, cooldown=${cooldownSec}s`); continue; }
      anyCursor = (keyConfig.index + 1) % anyKeys.length;
      return { status: upstream.status, body: parsedError };
    } catch (error) {
      const detail = error && error.message ? error.message : "upstream_error";
      markAnyKeyFailure(keyConfig, 502, detail, ANY_NETWORK_ERROR_COOLDOWN_SEC);
      if (offset < orderedKeys.length - 1) { console.warn(`[Any-API] ${keyConfig.label} network error`); continue; }
      anyCursor = (keyConfig.index + 1) % anyKeys.length;
      return { status: 502, body: { error: { message: detail, type: "network_error" } } };
    }
  }
  return null;
}

function mapGroqModelToNvidia(originalModel) {
  const m = String(originalModel || "").toLowerCase();
  if (m.includes("120b") || m.includes("heavy") || m.includes("deepseek") || m.includes("reason") || m.includes("nemotron")) {
    return "deepseek-ai/deepseek-v4-pro-0813";
  }
  return "google/gemma-4-31b-it";
}
async function forwardToNvidia(payload) {
  const nvidiaKeys = getNvidiaKeys();
  if (!nvidiaKeys.length) return null;
  const originalModel = sanitizeString(payload.model, 120) || "openai/gpt-oss-20b";
  const nvidiaModel = mapGroqModelToNvidia(originalModel);
  const requestBody = { model: nvidiaModel, messages: Array.isArray(payload.messages) ? payload.messages : [], temperature: payload.temperature ?? 0.2, max_tokens: payload.max_tokens ?? 1024, stream: false };
  const orderedKeys = orderedNvidiaKeys(nvidiaKeys);
  const readyCount = orderedKeys.filter((kc) => nvidiaKeyCooldownRemaining(getNvidiaKeyState(kc)) === 0).length;
  if (!readyCount) return null;
  for (let offset = 0; offset < orderedKeys.length; offset += 1) {
    const keyConfig = orderedKeys[offset];
    if (nvidiaKeyCooldownRemaining(getNvidiaKeyState(keyConfig)) > 0) continue;
    const apiKey = keyConfig.value;
    try {
      const upstream = await fetch(`${NVIDIA_API_BASE_URL}/chat/completions`, {
        method: "POST",
        headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });
      const text = await upstream.text();
      if (upstream.ok) {
        let parsed; try { parsed = JSON.parse(text); } catch (_e) { parsed = { raw: text }; }
        markNvidiaKeySuccess(keyConfig);
        nvidiaCursor = (keyConfig.index + 1) % nvidiaKeys.length;
        if (parsed && typeof parsed === "object" && parsed.choices && parsed.choices[0]) {
          try { parsed._via = "nvidia"; parsed._nvidia_model = nvidiaModel; parsed._original_model = originalModel; } catch (_e) {}
        }
        console.log(`[Nvidia] ${keyConfig.label} success with ${nvidiaModel} (from ${originalModel})`);
        return { status: upstream.status, body: parsed };
      }
      let parsedError; try { parsedError = JSON.parse(text); } catch (_e) { parsedError = { error: { message: text || "upstream_error" } }; }
      const detail = String(parsedError?.error?.message || text || "upstream_error");
      let cooldownSec = 0;
      if (upstream.status === 429) {
        let retrySec = NVIDIA_KEY_COOLDOWN_SEC;
        try {
          const m = String(detail || "").match(/try again in ([0-9]+(?:\.[0-9]+)?)s/i);
          if (m) { const p = parseFloat(m[1]); if (!isNaN(p) && p > 0) { retrySec = Math.ceil(p + 3); retrySec = Math.max(5, Math.min(retrySec, 60)); } }
        } catch (_e) {}
        cooldownSec = retrySec;
      } else if (upstream.status === 401 || upstream.status === 403) { cooldownSec = NVIDIA_INVALID_KEY_COOLDOWN_SEC; }
      if (cooldownSec > 0) markNvidiaKeyFailure(keyConfig, upstream.status, detail, cooldownSec); else markNvidiaKeyFailure(keyConfig, upstream.status, detail, 0);
      if ([401, 403, 429].includes(upstream.status) && offset < orderedKeys.length - 1) { console.warn(`[Nvidia] ${keyConfig.label} failed ${upstream.status}`); continue; }
      nvidiaCursor = (keyConfig.index + 1) % nvidiaKeys.length;
      return { status: upstream.status, body: parsedError };
    } catch (error) {
      const detail = error && error.message ? error.message : "upstream_error";
      markNvidiaKeyFailure(keyConfig, 502, detail, NVIDIA_NETWORK_ERROR_COOLDOWN_SEC);
      if (offset < orderedKeys.length - 1) { console.warn(`[Nvidia] ${keyConfig.label} network error`); continue; }
      nvidiaCursor = (keyConfig.index + 1) % nvidiaKeys.length;
      return { status: 502, body: { error: { message: detail, type: "network_error" } } };
    }
  }
  return null;
}

async function forwardToGroq(payload) {
  const groqKeys = getGroqKeys();
  if (!groqKeys.length) {
    return { status: 500, body: { error: { message: "missing_groq_key" } } };
  }

  const requestBody = {
    model: sanitizeString(payload.model, 120) || "openai/gpt-oss-20b",
    messages: Array.isArray(payload.messages) ? payload.messages : [],
    temperature: payload.temperature ?? 0.2,
    max_tokens: payload.max_tokens ?? 1024,
    stream: false,
  };

  const orderedKeys = orderedGroqKeys(groqKeys);
  const readyCount = orderedKeys.filter((keyConfig) => groqKeyCooldownRemaining(getGroqKeyState(keyConfig)) === 0).length;
  if (!readyCount) {
    // Thử Any-API trước Gemini (theo yêu cầu mới)
    const anyFallback = await forwardToAny(payload);
    if (anyFallback) return anyFallback;
    const nvidiaFallback = await forwardToNvidia(payload);
    if (nvidiaFallback) return nvidiaFallback;
    // Thử fallback sang Gemini nếu Groq hết key
    const geminiFallback = await forwardToGemini(payload);
    if (geminiFallback) {
      return geminiFallback;
    }
    const retryAfterSec = Math.min(
      ...orderedKeys
        .map((keyConfig) => groqKeyCooldownRemaining(getGroqKeyState(keyConfig)))
        .filter((value) => value > 0)
    );
    return {
      status: 503,
      body: {
        error: {
          message: "all_groq_keys_cooling_down",
          retry_after_sec: retryAfterSec || GROQ_KEY_COOLDOWN_SEC,
        },
      },
    };
  }

  for (let offset = 0; offset < orderedKeys.length; offset += 1) {
    const keyConfig = orderedKeys[offset];
    if (groqKeyCooldownRemaining(getGroqKeyState(keyConfig)) > 0) {
      continue;
    }
    const apiKey = keyConfig.value;
    try {
      const upstream = await fetch(`${GROQ_API_BASE_URL}/chat/completions`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      const responseText = await upstream.text();
      if (upstream.ok) {
        let parsed;
        try {
          parsed = JSON.parse(responseText);
        } catch (_error) {
          parsed = { raw: responseText };
        }
        markGroqKeySuccess(keyConfig);
        groqCursor = (keyConfig.index + 1) % groqKeys.length;
        return { status: upstream.status, body: parsed };
      }

      let parsedError;
      try {
        parsedError = JSON.parse(responseText);
      } catch (_error) {
        parsedError = { error: { message: responseText || "upstream_error" } };
      }
      const detail = String(parsedError?.error?.message || responseText || "upstream_error");
      let cooldownSec = 0;
      if (upstream.status === 429) {
        // Groq TPM 429 thường kèm "try again in 15.79s" -> dùng thời gian đó thay vì 900s
        let retrySec = GROQ_KEY_COOLDOWN_SEC;
        try {
          const m = String(detail || "").match(/try again in ([0-9]+(?:\.[0-9]+)?)s/i);
          if (m) {
            const parsed = parseFloat(m[1]);
            if (!isNaN(parsed) && parsed > 0) {
              retrySec = Math.ceil(parsed + 3);
              retrySec = Math.max(5, Math.min(retrySec, 60));
            }
          }
          // Nếu detail có retry_after hoặc reset time header, có thể parse thêm
          const m2 = String(detail || "").match(/retry.*?(\d+)\s*s/i);
          if (m2 && !m) {
            const parsed2 = parseInt(m2[1], 10);
            if (!isNaN(parsed2) && parsed2 > 0) {
              retrySec = Math.max(5, Math.min(parsed2 + 2, 60));
            }
          }
        } catch (_e) {}
        cooldownSec = retrySec;
      } else if (upstream.status === 401 || upstream.status === 403) {
        cooldownSec = GROQ_INVALID_KEY_COOLDOWN_SEC;
      }
      if (cooldownSec > 0) {
        markGroqKeyFailure(keyConfig, upstream.status, detail, cooldownSec);
      } else {
        markGroqKeyFailure(keyConfig, upstream.status, detail, 0);
      }
      if ([401, 403, 429].includes(upstream.status) && offset < orderedKeys.length - 1) {
        console.warn(`[Groq] ${keyConfig.label} failed with ${upstream.status}, cooldown=${cooldownSec}s`);
        continue;
      }
      // Thử fallback Any-API -> Nvidia -> Gemini nếu Groq lỗi nặng (429 TPM, 5xx)
      if ([429, 503, 500, 502].includes(upstream.status)) {
        const anyRes = await forwardToAny(payload);
        if (anyRes) { groqCursor = (keyConfig.index + 1) % groqKeys.length; return anyRes; }
        const nvidiaRes = await forwardToNvidia(payload);
        if (nvidiaRes) { groqCursor = (keyConfig.index + 1) % groqKeys.length; return nvidiaRes; }
        const geminiRes = await forwardToGemini(payload);
        if (geminiRes) {
          groqCursor = (keyConfig.index + 1) % groqKeys.length;
          return geminiRes;
        }
      }
      groqCursor = (keyConfig.index + 1) % groqKeys.length;
      return { status: upstream.status, body: parsedError };
    } catch (error) {
      const detail = error && error.message ? error.message : "upstream_error";
      markGroqKeyFailure(keyConfig, 502, detail, GROQ_NETWORK_ERROR_COOLDOWN_SEC);
      if (offset < orderedKeys.length - 1) {
        console.warn(`[Groq] ${keyConfig.label} network error, cooldown=${GROQ_NETWORK_ERROR_COOLDOWN_SEC}s`);
        continue;
      }
      // Thử Any-API -> Nvidia -> Gemini khi network error
      const anyNetFallback = await forwardToAny(payload);
      if (anyNetFallback) { groqCursor = (keyConfig.index + 1) % groqKeys.length; return anyNetFallback; }
      const nvidiaNetFallback = await forwardToNvidia(payload);
      if (nvidiaNetFallback) { groqCursor = (keyConfig.index + 1) % groqKeys.length; return nvidiaNetFallback; }
      const geminiNetFallback = await forwardToGemini(payload);
      if (geminiNetFallback) {
        groqCursor = (keyConfig.index + 1) % groqKeys.length;
        return geminiNetFallback;
      }
      groqCursor = (keyConfig.index + 1) % groqKeys.length;
      return {
        status: 502,
        body: {
          error: {
            message: detail,
            type: "network_error",
          },
        },
      };
    }
  }

  // Hết Groq keys mà vẫn lỗi -> thử Any -> Nvidia -> Gemini lần cuối
  const finalAny = await forwardToAny(payload);
  if (finalAny) return finalAny;
  const finalNvidia = await forwardToNvidia(payload);
  if (finalNvidia) return finalNvidia;
  const finalGemini = await forwardToGemini(payload);
  if (finalGemini) {
    return finalGemini;
  }
  return { status: 502, body: { error: { message: "upstream_error" } } };
}

function createServer() {
  return http.createServer(async (req, res) => {
  if (req.method === "OPTIONS") {
    res.writeHead(204, withCors({}));
    res.end();
    return;
  }

  const url = new URL(req.url, `http://${req.headers.host || "localhost"}`);

  if (req.method === "GET" && url.pathname === "/health") {
    const keyStates = listGroqKeyHealth();
    const geminiStates = listGeminiKeyHealth();
    const anyStates = listAnyKeyHealth();
    const nvidiaStates = listNvidiaKeyHealth();
    sendJson(res, 200, {
      ok: true,
      bindings_store: bindingsStoreInfo.type,
      bindings_target: bindingsStoreInfo.target,
      groq_api_base_url: GROQ_API_BASE_URL,
      groq_keys: keyStates.length,
      groq_ready_keys: keyStates.filter((item) => item.status === "ready").length,
      groq_cooling_keys: keyStates.filter((item) => item.status === "cooling_down").length,
      key_states: keyStates,
      gemini_api_base_url: GEMINI_API_BASE_URL,
      gemini_keys: geminiStates.length,
      gemini_ready_keys: geminiStates.filter((item) => item.status === "ready").length,
      gemini_cooling_keys: geminiStates.filter((item) => item.status === "cooling_down").length,
      gemini_key_states: geminiStates,
      any_api_base_url: ANY_API_BASE_URL,
      any_keys: anyStates.length,
      any_ready_keys: anyStates.filter((item) => item.status === "ready").length,
      any_cooling_keys: anyStates.filter((item) => item.status === "cooling_down").length,
      any_key_states: anyStates,
      nvidia_api_base_url: NVIDIA_API_BASE_URL,
      nvidia_keys: nvidiaStates.length,
      nvidia_ready_keys: nvidiaStates.filter((item) => item.status === "ready").length,
      nvidia_cooling_keys: nvidiaStates.filter((item) => item.status === "cooling_down").length,
      nvidia_key_states: nvidiaStates,
      time: new Date().toISOString(),
    });
    return;
  }

  if (!APP_TOKEN_SECRET) {
    sendJson(res, 500, { error: { message: "missing_app_token_secret" } });
    return;
  }

  if (req.method === "POST" && url.pathname === "/device/register") {
    try {
      const body = await readJsonBody(req);
      const result = await registerDevice(body);
      sendJson(res, result.status, result.body);
    } catch (_error) {
      sendJson(res, 400, { error: { message: "invalid_json" } });
    }
    return;
  }

  // Clean uninstall: xóa device khỏi Supabase để cài lại tạo key mới (gỡ sạch)
  if (req.method === "POST" && url.pathname === "/device/delete") {
    try {
      const body = await readJsonBody(req);
      const deviceId = sanitizeString(body.device_id || req.headers["x-device-id"] || body.deviceId, 128);
      const deviceKey = sanitizeString(body.device_key || req.headers["x-device-key"] || body.deviceKey, 256);
      const machineFingerprint = sanitizeString(body.machine_fingerprint || req.headers["x-machine-fingerprint"] || body.machineFingerprint, 256);
      if (!machineFingerprint) {
        sendJson(res, 400, { error: { message: "missing_device_info" } });
        return;
      }
      let binding = null;
      if (deviceId) {
        binding = await bindingsStore.getByDeviceId(deviceId);
      }
      // Fallback: tìm theo deviceKeyHash nếu có key
      if (!binding && deviceKey) {
        try {
          const deviceKeyHashTmp = stableDeviceKeyHash(deviceKey);
          binding = await bindingsStore.getByDeviceKeyHash(deviceKeyHashTmp);
        } catch (_e) {}
      }
      if (!binding) {
        // Thử xóa theo fingerprint nếu không tìm thấy bằng id/key (trường hợp key bị mã hóa DPAPI)
        if (machineFingerprint) {
          try {
            const count = await bindingsStore.deleteByMachineFingerprint(machineFingerprint);
            if (count > 0) {
              console.log(`[DeviceDelete] deleted ${count} by fingerprint ${machineFingerprint.substring(0,12)}... via fallback`);
              sendJson(res, 200, { ok: true, deleted_by_fingerprint: true, count });
              return;
            }
          } catch (_e) {}
        }
        // Idempotent: nếu không tìm thấy thì coi như đã xóa
        sendJson(res, 200, { ok: true, deleted: false, message: "device_not_found" });
        return;
      }
      let deviceKeyHash = "";
      try {
        deviceKeyHash = deviceKey ? stableDeviceKeyHash(deviceKey) : "";
      } catch (_e) {}
      // Kiểm tra khớp: nếu có deviceKey thì phải khớp, fingerprint phải khớp (cho phép key khớp dù fingerprint khác do đổi hardware)
      if (deviceKey && binding.deviceKeyHash !== deviceKeyHash) {
        sendJson(res, 403, { error: { message: "device_mismatch" } });
        return;
      }
      if (binding.machineFingerprint !== machineFingerprint) {
        if (deviceKey && binding.deviceKeyHash === deviceKeyHash) {
          console.log(`[DeviceDelete] fingerprint mismatch but key matches, allowing delete for ${binding.deviceId}`);
        } else {
          sendJson(res, 403, { error: { message: "device_mismatch" } });
          return;
        }
      }
      const targetId = binding.deviceId || deviceId;
      await bindingsStore.deleteByDeviceId(targetId);
      console.log(`[DeviceDelete] ${targetId} deleted via clean uninstall (key=${binding.deviceKeyHash.substring(0,8)}...)`);
      sendJson(res, 200, { ok: true, deleted_device_id: targetId });
    } catch (_error) {
      console.error("[DeviceDelete] error", _error);
      sendJson(res, 400, { error: { message: "invalid_json" } });
    }
    return;
  }

  if (req.method === "POST" && url.pathname === "/openai/v1/chat/completions") {
    const authCheck = await verifyDeviceHeaders(req);
    if (!authCheck.ok) {
      sendJson(res, authCheck.status, { error: { message: authCheck.error } });
      return;
    }
    try {
      const payload = await readJsonBody(req);
      const upstream = await forwardToGroq(payload);
      sendJson(res, upstream.status, upstream.body);
    } catch (_error) {
      sendJson(res, 400, { error: { message: "invalid_json" } });
    }
    return;
  }

  sendJson(res, 404, { error: { message: "not_found" } });
});
}

async function startServer() {
  await bindingsStore.init();
  const server = createServer();
  server.listen(PORT, "0.0.0.0", () => {
    console.log(`EduPlay Northflank AI gateway listening on :${PORT}`);
    console.log(`Bindings store: ${bindingsStoreInfo.type}`);
    console.log(`Bindings target: ${bindingsStoreInfo.target}`);
    console.log(`Groq key count: ${getGroqKeys().length}`);
    console.log(`Groq API base URL: ${GROQ_API_BASE_URL}`);
    console.log(`Any-API key count: ${getAnyKeys().length}`);
    console.log(`Any-API base URL: ${ANY_API_BASE_URL}`);
    console.log(`Nvidia key count: ${getNvidiaKeys().length}`);
    console.log(`Nvidia API base URL: ${NVIDIA_API_BASE_URL}`);
    console.log(`Gemini key count: ${getGeminiKeys().length}`);
    console.log(`Gemini API base URL: ${GEMINI_API_BASE_URL}`);
  });
  return server;
}

if (require.main === module) {
  startServer().catch((error) => {
    console.error("Failed to start AI gateway", error);
    process.exit(1);
  });
}

module.exports = {
  createServer,
  registerDevice,
  verifyDeviceHeaders,
  startServer,
};
