import { C, MONO } from '../../data/theme';
import { useNow, SENSOR_STALE_MS } from '../../hooks/useNow';

/** Left column: per-zone gas sensor cards, 구역별로 서브 항목 형태로 묶어서 표시.
 * Zone A는 실제 서브 센서(A1/A2/A3) 값을 그대로 씀. B/C는 아직 구역당 센서
 * 하나뿐이라 첫 서브 슬롯에만 채우고 나머지는 대기 상태로 남겨둠.
 */
export default function SensorPanel({ zones }) {
  const now = useNow(1000);
  const byKey = Object.fromEntries(zones.map((z) => [z.key, z]));
  const categories = [
    { key: 'Zone A', subs: [{ label: 'Zone A1', z: byKey['Zone A1'] }, { label: 'Zone A2', z: byKey['Zone A2'] }, { label: 'Zone A3', z: byKey['Zone A3'] }] },
    { key: 'Zone B', subs: [{ label: 'Zone B1', z: byKey['Zone B1'] }, { label: 'Zone B2', z: byKey['Zone B2'] }, { label: 'Zone B3', z: byKey['Zone B3'] }] },
    { key: 'Zone C', subs: [{ label: 'Zone C1', z: byKey['Zone C1'] }, { label: 'Zone C2', z: byKey['Zone C2'] }, { label: 'Zone C3', z: byKey['Zone C3'] }] },
  ];

  return (
    <div
      style={{
        borderRight: `1px solid ${C.line}`,
        padding: 18,
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
        overflowY: 'auto',
      }}
    >
      <div style={{ fontFamily: MONO, fontSize: 11, letterSpacing: '.1em', color: C.muted, fontWeight: 600 }}>
        SENSORS
      </div>

      {categories.map((cat) => (
        <ZoneCategory key={cat.key} category={cat} now={now} />
      ))}
    </div>
  );
}

function ZoneCategory({ category, now }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ fontFamily: MONO, fontSize: 11, fontWeight: 700, color: C.muted, letterSpacing: '.04em' }}>
        {category.key.toUpperCase()}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, paddingLeft: 10, borderLeft: `2px solid ${C.line3}` }}>
        {category.subs.map((sub) => (
          <SensorCard key={sub.label} label={sub.label} z={sub.z} now={now} />
        ))}
      </div>
    </div>
  );
}

// z가 없거나(아직 이 서브 항목에 붙은 센서가 없음), 마지막 수신 후 STALE_MS 넘게
// 안 왔으면(끊김) 대기 상태로 표시.
function SensorCard({ label, z, now }) {
  const waiting = !z || !z.at || now - z.at > SENSOR_STALE_MS;
  const level = waiting ? null : z.level;
  const intensity = waiting ? null : z.intensity;
  return (
    <div style={{ background: waiting ? C.card : z.cardBg, borderLeft: `3px solid ${waiting ? C.line2 : z.left}`, borderRadius: 9, padding: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontWeight: 700, fontSize: 13 }}>{label}</span>
        <span style={{ fontSize: 11, color: waiting ? C.faint : z.txt, fontWeight: 700 }}>{waiting ? '대기' : level}</span>
      </div>
      {/* 센서 세기 (0~100). 숫자는 두 자리로, 아래 막대도 이 값에 맞춰 채워집니다. */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, margin: '7px 0 5px' }}>
        <span style={{ fontFamily: MONO, fontSize: 24, fontWeight: 700, color: waiting ? C.faint : z.intensityColor }}>
          {waiting ? '--' : intensity.toFixed(1)}
        </span>
        <span style={{ fontSize: 12, color: C.muted }}>/ 100</span>
      </div>
      <div style={{ height: 5, background: C.line3, borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: waiting ? '0%' : z.barW, height: '100%', background: waiting ? C.line3 : z.bar, transition: 'width .6s' }} />
      </div>
    </div>
  );
}
