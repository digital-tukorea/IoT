// safescout.js — SafeScout DB 조회 서버(ServerDB/main.py) REST 클라이언트
//
// 서버는 CORS를 전체 허용("*")하므로 Vite 프록시 없이 브라우저에서 바로 호출합니다.
// (CCTV 서버와 경로가 둘 다 /api/* 라 프록시를 공유할 수 없어, DB는 절대 URL로 직접 붙습니다)
//
// 기본 주소는 localhost:8080 입니다. (DB 서버 8080, CCTV 스트리밍은 로컬 8081)
//   python main.py   → 8080 (config.py SERVER_PORT)
// 다른 장비/포트면 .env.local 에 VITE_DB_BASE 를 지정하세요.

const DB_BASE = import.meta.env.VITE_DB_BASE || 'http://localhost:8080';
const TIMEOUT_MS = 5000; // 서버가 응답 없으면 이 시간 뒤 실패 처리

async function apiRequest(path, { method = 'GET', body, signal } = {}) {
  // 요청별 타임아웃. 서버가 죽어 있거나 멈춰 있을 때 무한정 매달리지 않게 합니다.
  const timer = new AbortController();
  const timeout = setTimeout(() => timer.abort(), TIMEOUT_MS);
  // 호출부가 준 signal과 타임아웃 중 먼저 오는 쪽으로 중단
  if (signal) signal.addEventListener('abort', () => timer.abort(), { once: true });

  let res;
  try {
    res = await fetch(`${DB_BASE}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: timer.signal,
    });
  } catch (e) {
    // AbortError면 타임아웃, 그 외엔 연결 거부 등 네트워크 오류
    const msg = e.name === 'AbortError' ? `응답 없음 (${TIMEOUT_MS / 1000}초 초과)` : '서버에 연결할 수 없습니다';
    throw new Error(msg, { cause: e });
  } finally {
    clearTimeout(timeout);
  }

  const text = await res.text();

  let responseBody = null;
  if (text) {
    try {
      responseBody = JSON.parse(text);
    } catch {
      responseBody = text; // JSON이 아니면 원문 그대로 (에러 메시지 등)
    }
  }

  if (!res.ok) {
    // FastAPI는 오류를 { detail: "..." } 형태로 내려줍니다.
    const msg = responseBody && responseBody.detail ? responseBody.detail : `HTTP ${res.status}`;
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }
  return responseBody;
}

const apiGet = (path, o) => apiRequest(path, o);
const apiPost = (path, body, o) => apiRequest(path, { ...o, method: 'POST', body });

// ServerDB/main.py 의 엔드포인트와 1:1 대응합니다.
export const safescout = {
  base: DB_BASE,

  root: (o) => apiGet('/', o),
  health: (o) => apiGet('/health', o),

  // role: 'admin' | 'staff'. 서버의 users 테이블(username, password_hash, role)에 대응.
  register: (username, password, role, o) => apiPost('/api/auth/register', { username, password, role }, o),
  login: (username, password, o) => apiPost('/api/auth/login', { username, password }, o),

  robotEvents: (limit = 50, o) => apiGet(`/api/robot-events?limit=${limit}`, o),
  robotEventDetail: (eventId, o) => apiGet(`/api/robot-events/${eventId}`, o),

  fixedSensorLatest: (o) => apiGet('/api/fixed-sensor/latest', o),
  fixedSensorHistory: (zoneId, limit = 100, o) =>
    apiGet(`/api/fixed-sensor/${encodeURIComponent(zoneId)}/history?limit=${limit}`, o),
  fixedSensorBaseline: (o) => apiGet('/api/fixed-sensor/baseline', o),

  fireEvents: (limit = 50, o) => apiGet(`/api/fire-events?limit=${limit}`, o),
  alertsRecent: (limit = 20, o) => apiGet(`/api/alerts/recent?limit=${limit}`, o),

  createInstruction: (eventKind, eventLabel, instruction, o) =>
    apiPost('/api/instructions', { event_kind: eventKind, event_label: eventLabel, instruction }, o),
};
