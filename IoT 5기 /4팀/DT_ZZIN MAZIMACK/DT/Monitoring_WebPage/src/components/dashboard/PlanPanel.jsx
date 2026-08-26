import { C, MONO } from '../../data/theme';
import { useNow, SENSOR_STALE_MS } from '../../hooks/useNow';
import LiveCctv from './LiveCctv';
import RobotCam from './RobotCam';

/**
 * Center column: floor plan with zone overlays, the animated patrol-robot
 * marker (position driven by scenario step) and two live CCTV feeds.
 */
// 박스에 표시할 값: 센서 세기(0~100) · 상태. 대기 상태(끊김 포함)면 안내 문구만.
function zoneReading(z, waiting) {
  return waiting ? '수신 대기중' : `${z.intensity.toFixed(1)} / 100 · ${z.level}`;
}

// 한 번도 안 왔거나(z.at 없음), 마지막 수신 후 SENSOR_STALE_MS 넘게 안 오면(끊김) 대기 상태.
function isWaiting(z, now) {
  return !z.at || now - z.at > SENSOR_STALE_MS;
}

// 한 행(A/B/C)을 3칸(예: A1/A2/A3)으로 쪼갠 위치. QR 체크포인트 단위라 센서는
// 구역당 하나뿐이므로, 같은 행의 3칸은 전부 그 구역 센서값을 그대로 공유합니다.
// 출구는 작은 점 표시로만 남기고 나머지는 구역 칸으로 꽉 채웁니다(4%~96%).
const COL_LEFT = ['4%', '35.67%', '67.33%'];
const COL_WIDTH = '28.67%';

export default function PlanPanel({ zones, robot, onOpenCctv, cctvEnabled = true }) {
  const now = useNow(1000);
  // A/B행은 실제 서브 센서(A1~A3, B1~B3) 값을 칸마다 따로 씀. C는 아직 구역당
  // 센서 하나뿐이라 같은 행의 3칸이 그 값을 공유함.
  const byKey = Object.fromEntries(zones.map((z) => [z.key, z]));
  const [za1, za2, za3] = [byKey['Zone A1'], byKey['Zone A2'], byKey['Zone A3']];
  const [zb1, zb2, zb3] = [byKey['Zone B1'], byKey['Zone B2'], byKey['Zone B3']];
  const [zc1, zc2, zc3] = [byKey['Zone C1'], byKey['Zone C2'], byKey['Zone C3']];
  return (
    <div style={{ position: 'relative', padding: 20, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <div style={{ fontWeight: 800, fontSize: 15 }}>평면도 · 로봇 위치</div>
        <div style={{ display: 'flex', gap: 14, fontSize: 11, color: C.muted }}>
          <span>● <span style={{ color: C.green }}>정상</span></span>
          <span>● <span style={{ color: C.amber }}>주의</span></span>
          <span>● <span style={{ color: C.red }}>위험</span></span>
        </div>
      </div>

      {/* Floor plan — takes the larger share (2 : 1) of the vertical space */}
      <div
        style={{
          flex: 2,
          position: 'relative',
          background: C.bgDeep,
          border: `1px solid ${C.line}`,
          borderRadius: 12,
          overflow: 'hidden',
          minHeight: 0,
          backgroundImage:
            `linear-gradient(${C.gridLine} 1px,transparent 1px),linear-gradient(90deg,${C.gridLine} 1px,transparent 1px)`,
          backgroundSize: '32px 32px',
        }}
      >
        {[za1, za2, za3].map((z, i) => {
          const waiting = isWaiting(z, now);
          return <ZoneBox key={`A${i + 1}`} left={COL_LEFT[i]} top="5%" width={COL_WIDTH} height="21%" border={z.pBorder} bg={z.pBg} title={`A${i + 1}`} reading={zoneReading(z, waiting)} readingColor={z.txt} closed={!waiting && z.level === '위험'} waiting={waiting} />;
        })}
        <Corridor top="30%" />
        {[zb1, zb2, zb3].map((z, i) => {
          const waiting = isWaiting(z, now);
          return <ZoneBox key={`B${i + 1}`} left={COL_LEFT[i]} top="38%" width={COL_WIDTH} height="21%" border={z.pBorder} bg={z.pBg} title={`B${i + 1}`} reading={zoneReading(z, waiting)} readingColor={z.txt} closed={!waiting && z.level === '위험'} waiting={waiting} />;
        })}
        <Corridor top="63%" />
        {[zc1, zc2, zc3].map((z, i) => {
          const waiting = isWaiting(z, now);
          return <ZoneBox key={`C${i + 1}`} left={COL_LEFT[i]} top="71%" width={COL_WIDTH} height="24%" border={z.pBorder} bg={z.pBg} title={`C${i + 1}`} reading={zoneReading(z, waiting)} readingColor={z.txt} closed={!waiting && z.level === '위험'} waiting={waiting} />;
        })}

        {/* 출구 4곳 — 상시 표시, 실시간 데이터 없는 고정 지점. A행 좌우 여백 / C행 좌우 여백. */}
        <ExitStrip key="exit-a-left" side="left" top="5%" height="21%" />
        <ExitStrip key="exit-a-right" side="right" top="5%" height="21%" />
        <ExitStrip key="exit-c-left" side="left" top="71%" height="24%" />
        <ExitStrip key="exit-c-right" side="right" top="71%" height="24%" />

        {/* Patrol robot marker */}
        <div
          style={{
            position: 'absolute',
            left: robot.left,
            top: robot.top,
            transform: 'translate(-50%,-50%)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 6,
            zIndex: 2,
            transition: 'left .9s ease, top .9s ease',
          }}
        >
          <div
            style={{
              width: 24,
              height: 24,
              borderRadius: '50%',
              background: robot.color,
              border: `3px solid ${C.bgDeep}`,
              boxShadow: `0 0 0 2px ${robot.ring}, 0 0 22px ${robot.ring}`,
              display: 'grid',
              placeItems: 'center',
              fontSize: 11,
              color: C.ink,
              animation: 'pulseDot 1.6s infinite',
            }}
          >
            ▲
          </div>
          <span
            style={{
              fontFamily: MONO,
              fontSize: 10,
              color: C.text,
              background: C.bgDeep,
              padding: '2px 6px',
              borderRadius: 4,
              fontWeight: 700,
              whiteSpace: 'nowrap',
            }}
          >
            {robot.label}
          </span>
        </div>
      </div>

      {/* 하단: CCTV(실시간) + 로봇 현장 스냅샷을 나란히 배치. CCTV가 더 넓게(2:1).
          CCTV 클릭하면 확대 팝업(CctvModal)으로 크게 볼 수 있다.
          팝업이 열려 있는 동안에는 cctvEnabled=false로 이쪽 스트림을 닫는다. */}
      <div style={{ flex: 1, minHeight: 120, marginTop: 12, display: 'flex', gap: 12 }}>
        <div
          role="button"
          tabIndex={0}
          onClick={onOpenCctv}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              onOpenCctv();
            }
          }}
          title="클릭하여 실시간 영상 크게 보기"
          style={{ flex: 2, display: 'flex', cursor: 'pointer', position: 'relative' }}
        >
          <LiveCctv label="CCTV · 실시간" enabled={cctvEnabled} objectFit="cover" />
          <span
            style={{
              position: 'absolute',
              right: 10,
              bottom: 8,
              fontFamily: MONO,
              fontSize: 9.5,
              color: C.text,
              background: 'rgba(0,0,0,.5)',
              padding: '3px 8px',
              borderRadius: 5,
              pointerEvents: 'none',
            }}
          >
            ⤢ 크게 보기
          </span>
        </div>

        <RobotCam label="로봇 카메라" />
      </div>
    </div>
  );
}

// waiting(끊김/미수신)이면 상태색 대신 중립 회색으로 덮어써서 "정상"처럼 보이지 않게 합니다.
function ZoneBox({ left, top, width, height, border, bg, title, reading, readingColor, closed, waiting }) {
  const effBorder = waiting ? C.line2 : border;
  const effBg = waiting ? C.card : bg;
  const effReadingColor = waiting ? C.faint : readingColor;
  return (
    <div
      style={{
        position: 'absolute',
        left,
        top,
        width,
        height,
        border: `2px solid ${effBorder}`,
        borderRadius: 8,
        background: effBg,
        padding: 14,
        overflow: 'hidden',
      }}
    >
      <div style={{ fontWeight: 700, fontSize: 14 }}>{title}</div>
      <div style={{ fontFamily: MONO, fontSize: 12, color: effReadingColor, marginTop: 4 }}>{reading}</div>
      {closed && <ClosedBadge />}
    </div>
  );
}

// 구역 센서 값이 위험이면 표시되는 "폐쇄" 오버레이 — 현장 접근 금지를 알림.
function ClosedBadge() {
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'flex-end',
        padding: 10,
        background: 'repeating-linear-gradient(45deg,transparent,transparent 12px,rgba(240,68,56,.08) 12px,rgba(240,68,56,.08) 24px)',
        pointerEvents: 'none',
      }}
    >
      <span
        style={{
          fontFamily: MONO,
          fontSize: 11,
          fontWeight: 800,
          letterSpacing: '.05em',
          color: '#fff',
          background: C.red,
          padding: '4px 10px',
          borderRadius: 5,
        }}
      >
        ⛔ 폐쇄
      </span>
    </div>
  );
}

// 고정 출구 지점 — 구역 칸 바깥 여백(4%)을 세로 바로 표시. 경고 테이프(호박색/검정 사선)
// 배경 위에 대비 확실한 라벨 칩을 얹어서 "출구"가 항상 또렷이 보이게 함.
function ExitStrip({ side, top, height }) {
  return (
    <div
      style={{
        position: 'absolute',
        [side]: 0,
        top,
        width: '4%',
        height,
        background: `repeating-linear-gradient(45deg, ${C.amber} 0 8px, ${C.ink} 8px 16px)`,
        border: `1px solid ${C.amber}`,
        borderRadius: 4,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 4,
        zIndex: 2,
        pointerEvents: 'none',
      }}
    >
      <span
        style={{
          fontFamily: MONO,
          fontSize: 11,
          fontWeight: 800,
          color: C.ink,
          background: C.amber,
          padding: '3px 4px',
          borderRadius: 4,
          writingMode: 'vertical-rl',
          textOrientation: 'upright',
          letterSpacing: '.05em',
        }}
      >
        🚪출구
      </span>
    </div>
  );
}

// 복도 벽은 통짜가 아니라 각 칸(A1/A2/A3 등) 바로 아래에만 있고, 칸과 칸 사이
// 이음매(COL_LEFT 갭)는 뚫려있습니다 — 그 틈으로 옆 칸으로 넘어갈 수 있습니다.
function Corridor({ top }) {
  return (
    <>
      {COL_LEFT.map((left) => (
        <div key={left} style={{ position: 'absolute', left, top, width: COL_WIDTH, height: '4%', background: C.faint, borderRadius: 3 }} />
      ))}
    </>
  );
}
