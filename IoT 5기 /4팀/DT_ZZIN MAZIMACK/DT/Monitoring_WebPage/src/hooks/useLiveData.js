import { useEffect, useRef, useState } from 'react';
import { safescout } from '../api/safescout';

/**
 * ============================================================================
 *  실시간 데이터 훅 (WebSocket, /ws/realtime)
 * ============================================================================
 *  MQTT(로봇/센서/화재) → server(main.py) → WebSocket push → 이 훅.
 *  서버는 새 MQTT 메시지가 올 때마다 { topic, data } 를 그대로 밀어줍니다.
 *  topic: 'robot/event' | 'sensor/reading' | 'fire/event'
 *  data : models.py 의 Pydantic 모델을 exclude_none=True 로 덤프한 값
 *         (DB row가 아니라 MQTT payload 그대로라 id 는 없습니다)
 *
 *  구성:
 *    - readings   : 구역별 { level, intensity, at } — SensorPanel/PlanPanel/이벤트 입력
 *    - fireAlert  : { seq, level:'warn'|'danger', location, flameDetected, alertLevel, at } | null
 *                   화재 메시지가 오면 세팅, FIRE_HOLD_MS 동안 사람이 처리완료 안 하면 자동 소멸.
 *                   seq는 메시지가 올 때마다 증가하는 순번(ack 비교용, DB id 아님).
 *    - robotPos   : { x, y, at } | null — QR 퍼블리셔가 robot/event로 보내는 "(x,y)" 위치.
 *                   QR을 못 읽는 동안엔 메시지가 안 오므로 마지막 값이 그대로 유지됩니다.
 *
 *  접속 시점 이후의 새 메시지만 오므로, 페이지를 막 열었을 때의 "현재 상태"는
 *  REST로 한 번 스냅샷을 받아 채웁니다(zones latest 1회). 그 뒤로는 WS만 씁니다.
 * ============================================================================
 */

const WS_BASE = (import.meta.env.VITE_DB_BASE || 'http://localhost:8080').replace(/^http/, 'ws');
const RETRY_MS = 3000;
const FIRE_HOLD_MS = 120000; // 화재 감지 후 유지 시간(사람이 처리완료 안 누르면 자동 정상 복귀)

const LEVELS = new Set(['정상', '주의', '위험']);

// 'zone_A' → 'Zone A', 'zone_A1' → 'Zone A1' (접미사 전체를 보존)
function zoneKey(zoneId) {
  const s = String(zoneId);
  const m = /^zone_(.+)$/i.exec(s);
  return m ? `Zone ${m[1].toUpperCase()}` : s;
}

function toReading(row, atMs) {
  const strength = row.strength == null ? undefined : Number(row.strength);
  return {
    level: LEVELS.has(row.status) ? row.status : undefined,
    intensity: strength == null || Number.isNaN(strength) ? undefined : Math.max(0, Math.min(100, Math.round(strength * 10) / 10)),
    at: atMs,
  };
}

// flame_detected 는 REST(DB row, pymysql)로는 0/1, WS(Pydantic dump)로는 true/false로 옵니다.
function isDanger(row) {
  return row.flame_detected === true || row.flame_detected === 1 || row.alert_level === '위험';
}

// QR publisher가 보내는 location은 "(3,5)" 형태의 문자열입니다. 그 외 형식(구역명 등)이면 null.
function parseQrLocation(location) {
  const m = /^\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)$/.exec(String(location ?? ''));
  if (!m) return null;
  const x = Number(m[1]);
  const y = Number(m[2]);
  return Number.isNaN(x) || Number.isNaN(y) ? null : { x, y };
}

export function useLiveData() {
  const [readings, setReadings] = useState(null); // { 'Zone A': {level, intensity, at}, ... } | null
  const [fireAlert, setFireAlert] = useState(null);
  const [robotPos, setRobotPos] = useState(null); // { x, y, at } | null
  const [status, setStatus] = useState('connecting'); // 'connecting' | 'live' | 'error'
  const fireSeqRef = useRef(0);
  const fireTimerRef = useRef(null);

  // 접속 시점 스냅샷(1회). WS로 이미 받은 구역 값은 덮어쓰지 않습니다(늦게 도착한 REST가
  // 더 최신 WS 값을 되돌리지 않도록, prev를 우선합니다).
  useEffect(() => {
    let cancelled = false;
    safescout
      .fixedSensorLatest()
      .then((rows) => {
        if (cancelled || !Array.isArray(rows)) return;
        const snapshot = {};
        for (const r of rows) {
          if (!r || !r.zone_id) continue;
          const at = r.reading_time ? new Date(r.reading_time).getTime() : Date.now();
          snapshot[zoneKey(r.zone_id)] = toReading(r, at);
        }
        setReadings((prev) => ({ ...snapshot, ...(prev || {}) }));
      })
      .catch(() => {}); // 실패해도 WS가 이어서 채워줍니다
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    let ws;
    let retryTimer;

    function connect() {
      setStatus('connecting');
      ws = new WebSocket(`${WS_BASE}/ws/realtime`);

      ws.onopen = () => {
        if (!cancelled) setStatus('live');
      };

      ws.onmessage = (event) => {
        if (cancelled) return;
        let msg;
        try {
          msg = JSON.parse(event.data);
        } catch {
          return;
        }
        const { topic, data } = msg || {};
        if (!topic || !data) return;

        if (topic.startsWith('sensor/') && data.zone_id) {
          setReadings((prev) => ({ ...(prev || {}), [zoneKey(data.zone_id)]: toReading(data, Date.now()) }));
        } else if (topic.startsWith('fire/')) {
          fireSeqRef.current += 1;
          setFireAlert({
            seq: fireSeqRef.current,
            level: isDanger(data) ? 'danger' : 'warn',
            location: data.location || null,
            flameDetected: data.flame_detected === true || data.flame_detected === 1,
            alertLevel: data.alert_level || null,
            at: Date.now(),
          });
          clearTimeout(fireTimerRef.current);
          fireTimerRef.current = setTimeout(() => setFireAlert(null), FIRE_HOLD_MS);
        } else if (topic.startsWith('robot/') && data.location) {
          const pos = parseQrLocation(data.location);
          if (pos) setRobotPos({ ...pos, at: Date.now() });
        }
      };

      ws.onerror = () => {
        if (!cancelled) setStatus('error');
      };

      ws.onclose = () => {
        if (cancelled) return;
        setStatus('error');
        retryTimer = setTimeout(connect, RETRY_MS);
      };
    }

    connect();

    return () => {
      cancelled = true;
      clearTimeout(retryTimer);
      clearTimeout(fireTimerRef.current);
      if (ws) ws.close();
    };
  }, []);

  return { readings, fireAlert, robotPos, status };
}
