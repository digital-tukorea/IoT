import { useEffect, useState } from 'react';

// 마지막 수신값을 계속 표시(= "대기" 전환 없음)하기로 해서 사실상 무한대로 둡니다.
// SensorPanel·PlanPanel이 같은 기준을 씁니다.
export const SENSOR_STALE_MS = Infinity;

/** intervalMs마다 갱신되는 현재 시각. "마지막 수신 후 몇 초 지났나" 같은 걸
 * 계산하는 컴포넌트가 주기적으로 재평가되게 하려고 씁니다. */
export function useNow(intervalMs) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}
