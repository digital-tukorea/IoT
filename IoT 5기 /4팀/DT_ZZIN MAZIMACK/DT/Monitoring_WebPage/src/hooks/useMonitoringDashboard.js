import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { useToast } from './useToast';
import { useLiveData } from './useLiveData';
import { safescout } from '../api/safescout';
import {
  getZones,
  applyLiveReadings,
  buildZoneEvent,
  buildFireEvent,
  buildHeadline,
  buildRobot,
} from '../data/scenario';

/**
 * 화면 라우팅 + 실시간 데이터(MQTT → WebSocket) 기반 뷰 모델을 조립합니다.
 * 이벤트는 실제 신호(구역 센서 위험/주의, fire_event)로부터 직접 만들어지고,
 * 사람은 위험 이벤트를 하나씩 '처리완료 확인'만 합니다.
 * 정상으로 돌아가 카드가 사라진 이벤트도 sessionLog에 발생/해제/확인 기록으로 남습니다.
 */
export function useMonitoringDashboard(initialScreen = 'login') {
  const [screen, setScreen] = useState(initialScreen); // 'login' | 'dashboard'
  const [detailEventId, setDetailEventId] = useState(null);
  const [cctvOpen, setCctvOpen] = useState(false);
  const [logOpen, setLogOpen] = useState(false);
  const { toast, show } = useToast();

  const { readings: liveReadings, fireAlert, robotPos } = useLiveData();

  // 확인 처리된 이벤트 id 모음 ('zone:Zone A', 'fire:12' ...).
  // 화재는 메시지마다 seq가 새로 붙어 자동으로 재알림되지만, 구역은 같은 키가
  // 계속 재사용되므로 '위험으로 새로 진입'할 때 이전 ack를 지워 재알림시킵니다.
  const [ackedIds, setAckedIds] = useState(() => new Set());

  // 이벤트 로그. 카드가 정상 복귀로 사라져도 여기엔 남습니다.
  // 화재는 DB에 이력이 있어 마운트 시 한 번 REST로 불러와 앞에 채웁니다(새로고침에도 유지).
  // 구역 센서는 이런 이력 API가 없어 이번 세션에서 실제로 관찰한 전이만 쌓입니다.
  const [sessionLog, setSessionLog] = useState([]);

  useEffect(() => {
    let cancelled = false;
    safescout
      .fireEvents(50)
      .then((rows) => {
        if (cancelled || !Array.isArray(rows)) return;
        const hist = rows
          .map((r) => ({
            id: `fire-hist:${r.id}`,
            at: r.event_time ? new Date(r.event_time).getTime() : Date.now(),
            kind: 'fire',
            label: r.location || '위치 미상',
            type: 'created',
            level: r.flame_detected === 1 || r.flame_detected === true || r.alert_level === '위험' ? '위험' : '주의',
          }))
          .reverse(); // 오래된 것부터 먼저 오도록
        setSessionLog((prev) => [...hist, ...prev]);
      })
      .catch(() => {}); // 실패해도 실시간 로그는 계속 쌓입니다
    return () => {
      cancelled = true;
    };
  }, []);

  // 구역 센서는 이벤트 이력 API가 따로 없지만, fixed_sensor_reading은 측정마다
  // 전부 저장되어 있어서(dedup 없음) 그 원본 이력에서 주의/위험 전이를 다시
  // 계산해 새로고침해도 로그가 남게 합니다. (ack 기록은 DB에 없어 이건 복원 불가)
  useEffect(() => {
    let cancelled = false;
    const ZONES = [
      ['zone_A1', 'Zone A1'],
      ['zone_A2', 'Zone A2'],
      ['zone_A3', 'Zone A3'],
      ['zone_B1', 'Zone B1'],
      ['zone_B2', 'Zone B2'],
      ['zone_B3', 'Zone B3'],
      ['zone_C1', 'Zone C1'],
      ['zone_C2', 'Zone C2'],
      ['zone_C3', 'Zone C3'],
    ];
    Promise.all(ZONES.map(([zoneId]) => safescout.fixedSensorHistory(zoneId, 500).catch(() => [])))
      .then((results) => {
        if (cancelled) return;
        const entries = [];
        results.forEach((rows, i) => {
          if (!Array.isArray(rows) || rows.length === 0) return;
          const [, label] = ZONES[i];
          const asc = [...rows].reverse(); // API는 reading_time DESC → 오래된 것부터 보게 뒤집기
          let prevLevel = null;
          for (const r of asc) {
            const level = ['정상', '주의', '위험'].includes(r.status) ? r.status : null;
            if (level === prevLevel) continue;
            const at = r.reading_time ? new Date(r.reading_time).getTime() : Date.now();
            if (level === '주의' || level === '위험') {
              entries.push({ id: `zone-hist:${label}:${at}`, at, kind: 'zone', label, type: 'created', level });
            } else if (prevLevel && prevLevel !== '정상') {
              entries.push({ id: `zone-hist:${label}:resolved:${at}`, at, kind: 'zone', label, type: 'resolved', level: prevLevel });
            }
            prevLevel = level;
          }
        });
        if (entries.length > 0) setSessionLog((prev) => [...entries, ...prev]);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // 직전 렌더의 구역별 level 스냅샷 / 화재 스냅샷. effect가 아니라 렌더 도중
  // 조건부로 갱신합니다(React 공식 패턴: "prop/상태가 바뀌면 렌더 중 다른 상태를
  // 조정하기"). effect에 넣으면 한 프레임 늦게 반응하고, setState 업데이터 안에서
  // 이 비교를 하면 React가 개발 모드에서 업데이터를 두 번 호출할 때 결과가 꼬입니다.
  const [prevLevels, setPrevLevels] = useState({});
  if (liveReadings) {
    const enteredDanger = [];
    const newLogs = [];
    let levelsChanged = false;
    const nextLevels = { ...prevLevels };
    for (const [key, r] of Object.entries(liveReadings)) {
      if (nextLevels[key] !== r.level) {
        if (r.level === '위험' && nextLevels[key] !== '위험') enteredDanger.push(key);
        // 로그 시각은 항상 그 리딩 자체의 at(수신 시각)을 씁니다 — 렌더 중에는
        // Date.now() 같은 비순수 호출을 할 수 없습니다(React 렌더 순수성 규칙).
        if (r.level === '주의' || r.level === '위험') {
          newLogs.push({ id: `zone:${key}:${r.level}:${r.at}`, at: r.at, kind: 'zone', label: key, type: 'created', level: r.level });
        } else if (nextLevels[key] && nextLevels[key] !== '정상') {
          newLogs.push({ id: `zone:${key}:resolved:${r.at}`, at: r.at, kind: 'zone', label: key, type: 'resolved', level: nextLevels[key] });
        }
        nextLevels[key] = r.level;
        levelsChanged = true;
      }
    }
    if (levelsChanged) {
      setPrevLevels(nextLevels);
      if (newLogs.length > 0) setSessionLog((prev) => [...prev, ...newLogs]);
      if (enteredDanger.length > 0) {
        setAckedIds((prev) => {
          const next = new Set(prev);
          let changed = false;
          for (const key of enteredDanger) {
            if (next.delete(`zone:${key}`)) changed = true;
          }
          return changed ? next : prev;
        });
      }
    }
  }

  // 새 화재 신호 등장은 fireAlert.at(수신 시각, 순수 데이터)을 그대로 써서 렌더 중에 기록합니다.
  const [prevFireSeq, setPrevFireSeq] = useState(null);
  if ((fireAlert?.seq ?? null) !== prevFireSeq) {
    setPrevFireSeq(fireAlert?.seq ?? null);
    if (fireAlert) {
      setSessionLog((prev) => [
        ...prev,
        { id: `fire:${fireAlert.seq}:created`, at: fireAlert.at, kind: 'fire', label: fireAlert.location || '위치 미상', type: 'created', level: fireAlert.level === 'danger' ? '위험' : '주의' },
      ]);
    }
  }

  // fireAlert가 null로 사라지는 건 useLiveData 내부 타이머(진짜 외부 이벤트)가 만드는
  // 신호라 여기서도 effect로 감지합니다. Date.now()는 effect 안에서는 허용됩니다.
  const prevFireAlertRef = useRef(null);
  useEffect(() => {
    const prev = prevFireAlertRef.current;
    if (!fireAlert && prev) {
      setSessionLog((log) => [
        ...log,
        { id: `fire:${prev.seq}:resolved:${Date.now()}`, at: Date.now(), kind: 'fire', label: prev.location || '위치 미상', type: 'resolved', level: prev.level === 'danger' ? '위험' : '주의' },
      ]);
    }
    prevFireAlertRef.current = fireAlert;
  }, [fireAlert]);

  // --- navigation ---
  const goDashboard = useCallback(() => setScreen('dashboard'), []);
  const goLogout = useCallback(() => {
    setScreen('login');
    setAckedIds(new Set());
    setDetailEventId(null);
    setCctvOpen(false);
    setLogOpen(false);
  }, []);

  // 위험 이벤트 하나를 처리완료로 표시. instruction은 직원 앱으로 보낼 지시사항
  // (DetailModal에서 입력 강제). POST /api/instructions로 실제 서버에 남기고,
  // 실패해도 화면 상태(확인 처리)는 그대로 유지 — 재시도는 이벤트 로그로 확인.
  const confirmEvent = useCallback(
    (id, instruction) => {
      if (!id) return;
      setAckedIds((prev) => new Set(prev).add(id));
      const [kind, label] = id.split(':');
      // 확인 버튼은 위험 이벤트에만 뜨므로(showConfirmBtn = danger && !acked) 항상 위험입니다.
      setSessionLog((prev) => [
        ...prev,
        { id: `${id}:acked:${Date.now()}`, at: Date.now(), kind, label, type: 'acked', level: '위험', instruction: instruction || undefined },
      ]);
      setDetailEventId(null);
      if (instruction) {
        safescout
          .createInstruction(kind, label, instruction)
          .then(() => show('지시사항이 전달되었습니다 · 처리완료로 전환되었습니다'))
          .catch(() => show('처리완료는 반영됐지만 지시사항 전송에 실패했습니다'));
      } else {
        show('이벤트가 처리완료로 전환되었습니다');
      }
    },
    [show],
  );

  // --- modals ---
  const openDetail = useCallback((id) => setDetailEventId(id), []);
  const closeDetail = useCallback(() => setDetailEventId(null), []);
  const openCctv = useCallback(() => setCctvOpen(true), []);
  const closeCctv = useCallback(() => setCctvOpen(false), []);
  const openLog = useCallback(() => setLogOpen(true), []);
  const closeLog = useCallback(() => setLogOpen(false), []);

  // --- derived view model ---
  const view = useMemo(() => {
    const zones = applyLiveReadings(getZones(), liveReadings);

    // 처리완료(ack) 이벤트는 목록에서 바로 뺀다 — 다시 위험에 진입하면
    // (아래 렌더 중 로직에서 ack가 지워지므로) 새 카드로 재등장한다.
    const events = [];
    if (fireAlert && !ackedIds.has(`fire:${fireAlert.seq}`)) {
      events.push(buildFireEvent(fireAlert, false));
    }
    for (const z of zones) {
      if ((z.level === '주의' || z.level === '위험') && !ackedIds.has(`zone:${z.key}`)) {
        events.push(buildZoneEvent(z, false));
      }
    }

    // 상단 배너도 이벤트 카드와 동일하게 처리완료분은 제외 — 실제 신호는
    // 남아있어도(zones 배열 자체는 안 건드림) "확인 필요" 표시는 사라진다.
    const activeFireAlert = fireAlert && !ackedIds.has(`fire:${fireAlert.seq}`) ? fireAlert : null;
    const danger = zones.find((z) => z.level === '위험' && !ackedIds.has(`zone:${z.key}`));
    const warn = zones.find((z) => z.level === '주의' && !ackedIds.has(`zone:${z.key}`));
    const severity = activeFireAlert ? (activeFireAlert.level === 'danger' ? 'danger' : 'warn') : danger ? 'danger' : warn ? 'warn' : 'none';
    const zoneName = activeFireAlert ? activeFireAlert.location || '카메라 감지 구역' : danger ? danger.key : warn ? warn.key : '';

    return {
      zones,
      events,
      head: buildHeadline(severity, zoneName),
      robot: buildRobot(!!danger, robotPos),
    };
  }, [liveReadings, fireAlert, ackedIds, robotPos]);

  const selectedEvent = view.events.find((e) => e.id === detailEventId) || null;
  const eventLog = useMemo(() => [...sessionLog].sort((a, b) => b.at - a.at), [sessionLog]);

  return {
    screen,
    detailOpen: detailEventId != null,
    detailEvent: selectedEvent,
    cctvOpen,
    logOpen,
    eventLog,
    toast,
    ...view,
    actions: {
      goDashboard,
      goLogout,
      confirmEvent,
      openDetail,
      closeDetail,
      openCctv,
      closeCctv,
      openLog,
      closeLog,
    },
  };
}
