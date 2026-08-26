import { C, MONO } from '../../data/theme';

/**
 * 로봇캠(라즈베리파이 USB 웹캠) 실시간 영상.
 *
 * 브라우저는 라즈베리파이(사설 IP)에 직접 못 붙습니다 — 크롬 Private Network Access가
 * 공인 페이지에서 사설망으로의 접속을 막습니다. 그래서 CCTV 서버(GCP, 공인 IP)가
 * Tailscale로 대신 라즈베리파이에 접속해 릴레이하고(main.py의 /api/robot-cam/stream),
 * 브라우저는 그 GCP 주소만 봅니다.
 *
 * MJPEG(multipart/x-mixed-replace)를 <img>로 직접 끼워넣으면 크롬이 크로스오리진
 * 임베드일 때 이 MIME 타입을 제대로 안 그려줘서(알려진 크로미움 이슈), <iframe>으로
 * 직접 스트림 URL을 열어 우회합니다(최상위 문서 탐색은 정상 동작).
 */
const STREAM_PAGE_URL = import.meta.env.VITE_CCTV_BASE
  ? `${import.meta.env.VITE_CCTV_BASE}/api/robot-cam/`
  : null;

export default function RobotCam({ label = '로봇 카메라', style }) {
  return (
    <div
      style={{
        position: 'relative',
        flex: 1,
        borderRadius: 10,
        overflow: 'hidden',
        border: `1px solid ${C.line}`,
        background: 'repeating-linear-gradient(-45deg,#1c1b18,#1c1b18 9px,#252320 9px,#252320 18px)',
        display: 'grid',
        placeItems: 'center',
        ...style,
      }}
    >
      {STREAM_PAGE_URL ? (
        <iframe
          src={STREAM_PAGE_URL}
          title={label}
          style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', border: 'none' }}
        />
      ) : (
        <span style={{ fontFamily: MONO, fontSize: 10.5, color: C.faint, textAlign: 'center' }}>
          {label}
          <br />
          주소 미설정
        </span>
      )}

      <span
        style={{
          position: 'absolute',
          left: 10,
          top: 8,
          fontFamily: MONO,
          fontSize: 9.5,
          color: C.faint,
          background: 'rgba(0,0,0,.45)',
          padding: '2px 6px',
          borderRadius: 4,
          pointerEvents: 'none',
        }}
      >
        {label}
      </span>
    </div>
  );
}
