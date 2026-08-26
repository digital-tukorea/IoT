import { useWebRtcStream } from '../../hooks/useWebRtcStream';
import { C, MONO } from '../../data/theme';

/**
 * ============================================================================
 *  CCTV 실시간 영상 출력 컴포넌트
 * ============================================================================
 *  IP 카메라(RTSP) → FastAPI + aiortc → WebRTC(WHEP) → 이 <video> 로 출력됩니다.
 *  연결/상태 판정은 `useWebRtcStream` 훅이 담당합니다.
 *
 *  ⚠️ 서버(aiortc)는 시청자 1명당 소프트웨어 인코더를 하나씩 돌립니다.
 *     화면에 안 보이는 스트림은 `enabled={false}`로 꺼 주세요.
 *     (예: 모달이 열리면 뒤쪽 썸네일 off — Dashboard에서 처리)
 * ============================================================================
 */

// status → 우상단 배지 표시 방식
const STATUS_META = {
  idle: { text: 'OFF', color: C.dim, pulse: false },
  connecting: { text: '연결중', color: C.muted, pulse: false },
  live: { text: 'LIVE', color: C.red, pulse: true },
  stale: { text: '신호 지연', color: C.amber, pulse: false },
  'camera-offline': { text: '카메라 오프라인', color: C.redSoft, pulse: false },
  'stream-error': { text: '스트림 오류', color: C.redSoft, pulse: false },
  'server-offline': { text: '서버 연결 끊김', color: C.redSoft, pulse: false },
};

// status → 영상 위에 띄울 안내 문구
const STATUS_NOTE = {
  idle: '스트림 대기중',
  connecting: 'WebRTC 연결중…',
  stale: '프레임 수신이 지연되고 있습니다',
  'camera-offline': 'IP 카메라에 연결할 수 없습니다',
  'stream-error': '스트림 연결에 실패했습니다 · 재시도중',
  'server-offline': '스트리밍 서버에 연결할 수 없습니다',
};

export default function LiveCctv({
  label = 'CCTV · 실시간',
  enabled = true,
  // 이 서버 안 어느 스트림에 붙을지. '/api'(기본) = CCTV, '/api/robot' = 로봇캠.
  apiPath = '/api',
  background = 'repeating-linear-gradient(45deg,#1c1b18,#1c1b18 9px,#232120 9px,#232120 18px)',
  border = C.line,
  containerStyle = {},
  // 'contain' = 화면 전체를 보여주고 남는 곳은 레터박스.
  // 'cover'로 두면 컨테이너를 꽉 채우는 대신 화면 위아래가 잘려나갑니다.
  // 관제 화면은 잘린 영역에 상황이 있을 수 있으므로 기본을 contain으로 둡니다.
  objectFit = 'contain',
}) {
  const { videoRef, status, hasVideo, fps } = useWebRtcStream({ enabled, apiPath });

  const meta = STATUS_META[status] || STATUS_META.connecting;
  const isLive = status === 'live';

  return (
    <div
      style={{
        position: 'relative',
        flex: 1,
        borderRadius: 10,
        overflow: 'hidden',
        border: `1px solid ${border}`,
        background,
        display: 'grid',
        placeItems: 'center',
        ...containerStyle,
      }}
    >
      {/* WebRTC 실시간 영상. 훅이 ontrack에서 srcObject에 MediaStream을 연결합니다. */}
      <video
        ref={videoRef}
        autoPlay
        muted
        playsInline
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          objectFit,
          background: '#000',
          opacity: hasVideo ? 1 : 0,
          transition: 'opacity .3s',
        }}
      />

      {/* 아직 영상이 없을 때: 스캔라인 애니메이션 플레이스홀더 */}
      {!hasVideo && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(110deg,transparent 40%,rgba(255,255,255,.05) 50%,transparent 60%)',
            animation: 'sweep 3.5s infinite',
          }}
        />
      )}

      {/* 상태 안내 — 영상이 없으면 그대로, 있으면 어두운 오버레이 위에 */}
      {!isLive && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'grid',
            placeItems: 'center',
            background: hasVideo ? 'rgba(15,14,12,.62)' : 'transparent',
            pointerEvents: 'none',
          }}
        >
          <span style={{ fontFamily: MONO, fontSize: 12, color: C.faint, textAlign: 'center', lineHeight: 1.6 }}>
            {label}
            <br />
            <span style={{ fontSize: 9.5, color: meta.color }}>
              {STATUS_NOTE[status] || 'WebRTC 연결중…'}
            </span>
          </span>
        </div>
      )}

      {/* 좌상단: 녹화 표시 (재생중일 때만) */}
      {isLive && (
        <span style={{ position: 'absolute', left: 10, top: 8, fontFamily: MONO, fontSize: 9.5, color: C.red }}>
          ● REC
        </span>
      )}

      {/* 우상단: 실제 스트림 상태 배지 */}
      <span
        style={{
          position: 'absolute',
          right: 10,
          top: 8,
          display: 'flex',
          alignItems: 'center',
          gap: 5,
          fontFamily: MONO,
          fontSize: 9.5,
          color: meta.color,
          fontWeight: 700,
        }}
      >
        <span
          style={{
            width: 7,
            height: 7,
            borderRadius: '50%',
            background: meta.color,
            animation: meta.pulse ? 'pulseDot 1.1s infinite' : 'none',
          }}
        />
        {meta.text}
      </span>

      {/* 좌하단: 카메라 수신 FPS (재생중일 때만) */}
      {isLive && fps > 0 && (
        <span
          style={{
            position: 'absolute',
            left: 10,
            bottom: 8,
            fontFamily: MONO,
            fontSize: 9.5,
            color: C.muted,
            background: 'rgba(0,0,0,.45)',
            padding: '2px 6px',
            borderRadius: 4,
          }}
        >
          {fps} fps
        </span>
      )}
    </div>
  );
}
