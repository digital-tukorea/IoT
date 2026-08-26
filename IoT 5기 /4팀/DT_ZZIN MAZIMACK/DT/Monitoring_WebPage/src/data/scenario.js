// Pure view-model builders driven by real data (MQTT sensor/fire → useLiveData).
// No more fabricated step machine — zone color/level and events come straight
// from live readings; headline/robot marker are derived from that same state.

// Per-level visual palette for sensor zones and the plan overlay boxes.
const LEVEL_PALETTE = {
  정상: { txt: '#4caf6d', bar: '#4caf6d', cardBg: '#211f1c', left: '#4caf6d', pBorder: '#2f6b45', pBg: 'rgba(76,175,109,.09)' },
  주의: { txt: '#e0a020', bar: '#e0a020', cardBg: '#211f1c', left: '#e0a020', pBorder: '#7a5c17', pBg: 'rgba(224,160,32,.1)' },
  위험: { txt: '#ff6b5e', bar: '#f04438', cardBg: '#2a1714', left: '#f04438', pBorder: '#7a2a22', pBg: 'rgba(240,68,56,.13)' },
};

// `intensity`는 센서의 상대 세기(0~100)입니다. 실제 ppm 농도 계산은 어려워
// MQ2 등 센서의 상대 출력 세기를 0~100으로 정규화한 값만 표시합니다.
// at: 이 값을 마지막으로 받은 시각(ms). 기본값(라이브 데이터 도착 전)엔 없음.
function makeZone(key, level, intensity, at) {
  const p = LEVEL_PALETTE[level];
  return {
    key,
    level,
    intensity,
    at,
    barW: `${intensity}%`,
    txt: p.txt,
    bar: p.bar,
    cardBg: p.cardBg,
    left: p.left,
    pBorder: p.pBorder,
    pBg: p.pBg,
    intensityColor: level === '정상' ? '#eceae5' : p.txt,
  };
}

// 라이브 데이터 도착 전 기본값. 전부 정상/0으로 시작합니다.
export function getZones() {
  return [
    makeZone('Zone A1', '정상', 0),
    makeZone('Zone A2', '정상', 0),
    makeZone('Zone A3', '정상', 0),
    makeZone('Zone B1', '정상', 0),
    makeZone('Zone B2', '정상', 0),
    makeZone('Zone B3', '정상', 0),
    makeZone('Zone C1', '정상', 0),
    makeZone('Zone C2', '정상', 0),
    makeZone('Zone C3', '정상', 0),
  ];
}

/**
 * 실시간 센서값(WebSocket)이 도착하면 기본값 위에 덮어씁니다.
 * readings 형태: { 'Zone A': { level, intensity, at }, ... }
 * (아직 아무 메시지도 안 왔으면 readings=null → 기본값 그대로 사용)
 */
export function applyLiveReadings(zones, readings) {
  if (!readings) return zones;
  return zones.map((z) => {
    const r = readings[z.key];
    if (!r) return z;
    return makeZone(z.key, r.level ?? z.level, r.intensity ?? z.intensity, r.at ?? z.at);
  });
}

function timeLabel(atMs) {
  return atMs ? new Date(atMs).toLocaleTimeString('ko-KR', { hour12: false }) : '';
}

// 구역 센서(fixed_sensor_reading)의 주의/위험 상태로부터 이벤트 카드를 만듭니다.
export function buildZoneEvent(zone, acked) {
  const danger = zone.level === '위험';
  return {
    id: `zone:${zone.key}`,
    kind: 'zone',
    status: acked ? '처리완료' : danger ? '위험' : '주의',
    sc: acked ? '#7fd99b' : danger ? '#ff6b5e' : '#e0a020',
    sb: acked ? '#14301d' : danger ? '#2a1714' : '#332a14',
    title: `${zone.key} · 세기 ${(zone.intensity ?? 0).toFixed(1)}/100`,
    desc: danger
      ? '위험 감지 · 담당자 확인 필요'
      : 'MQ2 주의 수준 감지 · 지속 관찰 필요',
    time: timeLabel(zone.at),
    cardBg: acked ? '#1a1917' : danger ? '#2a1714' : '#211f1c',
    border: acked ? '1px solid #252320' : danger ? '1px solid #6b3418' : '1px solid #332a14',
    primary: danger,
    showDetailBtn: true,
    showConfirmBtn: danger && !acked,
    metrics: { kind: 'zone', intensity: zone.intensity },
  };
}

// 화재 이벤트(fire_event MQTT)로부터 이벤트 카드를 만듭니다.
export function buildFireEvent(fireAlert, acked) {
  if (!fireAlert) return null;
  const danger = fireAlert.level === 'danger';
  return {
    id: `fire:${fireAlert.seq}`,
    kind: 'fire',
    status: acked ? '처리완료' : danger ? '확정 · 화재' : '확인중',
    sc: acked ? '#7fd99b' : danger ? '#ffcf7a' : '#ffab73',
    sb: acked ? '#14301d' : danger ? '#3a2410' : '#3a1f14',
    title: `${fireAlert.location || '위치 미상'} · 화재 감지`,
    desc: danger
      ? '화염/경보 신호 확정 · 현장 확인 필요'
      : '화재 의심 신호 감지 · 판별 진행중',
    time: timeLabel(fireAlert.at),
    cardBg: acked ? '#1a1917' : '#2a1714',
    border: acked ? '1px solid #252320' : '1px solid #6b3418',
    primary: true,
    showDetailBtn: true,
    showConfirmBtn: danger && !acked,
    metrics: { kind: 'fire', flameDetected: fireAlert.flameDetected, alertLevel: fireAlert.alertLevel },
  };
}

// 상단 헤드라인 배지: 현재 가장 심각한 신호를 반영합니다.
const HEAD_CHROME = {
  none: { color: '#4caf6d', bg: '#14301d', border: '#2f6b45' },
  warn: { color: '#e0a020', bg: '#3a2410', border: '#6b5418' },
  danger: { color: '#ff6b5e', bg: '#3a1714', border: '#6b3418' },
};

export function buildHeadline(severity, zoneName) {
  const chrome = HEAD_CHROME[severity] || HEAD_CHROME.none;
  const headline =
    severity === 'danger' ? `${zoneName} 위험 — 담당자 확인 필요`
    : severity === 'warn' ? `${zoneName} 이상 감지 — 알림 전파`
    : '정상 감시중';
  return { headline, ...chrome };
}

// QR 좌표(row,col) → 평면도 위 위치(%).
// 8/20 개정 -- 라파 map_data.py 실측 맵 기준(행 0~11, 열 0~12)으로 맞춤.
// robot/event의 location "(row,col)"을 그대로 비례 변환한다(칸 스냅 없음 —
// 이제 로봇이 실제로 지나는 QR 좌표 자체가 이미 정수 격자라 스냅이 불필요).
const MAP_ROWS = 11; // 행 0~11
const MAP_COLS = 12; // 열 0~12
const PLAN_AREA = { left: 4, right: 96, top: 5, bottom: 95 }; // 평면도 박스들이 차지하는 %

function qrToPlan(x, y) {
  // x=행(row), y=열(col) — map_data.py의 (행,열) 표기와 동일 순서.
  const rowFrac = Math.max(0, Math.min(1, x / MAP_ROWS));
  const colFrac = Math.max(0, Math.min(1, y / MAP_COLS));
  return {
    left: `${PLAN_AREA.left + colFrac * (PLAN_AREA.right - PLAN_AREA.left)}%`,
    top: `${PLAN_AREA.top + rowFrac * (PLAN_AREA.bottom - PLAN_AREA.top)}%`,
  };
}

// 순찰 로봇 마커: robotPos(QR로 읽은 실좌표)가 있으면 그 위치에, 없으면 대기 위치(Zone C 앞)에
// 표시합니다. dispatched(가스 구역 위험 미확인 있음)일 때만 "출동중" — 화재는
// 로봇 자동출동 트리거 대상이 아니라서 여기 안 섞습니다.
export function buildRobot(dispatched, robotPos) {
  const pos = robotPos ? qrToPlan(robotPos.x, robotPos.y) : { left: '40%', top: '76%' };
  if (dispatched) {
    return { ...pos, label: 'SG-01 출동중', color: '#f26419', ring: '#f26419' };
  }
  return { ...pos, label: 'SG-01 대기중', color: '#8a877f', ring: '#8a877f' };
}
