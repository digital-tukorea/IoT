import ModalOverlay from './ModalOverlay';
import LiveCctv from '../dashboard/LiveCctv';
import { C } from '../../data/theme';

/**
 * 실시간 CCTV 확대 팝업.
 * 대시보드의 CCTV 썸네일을 클릭하면 열리며, 동일한 스트림을 큰 화면으로 재생한다.
 * (IP캠 RTSP → FastAPI(aiortc) → WebRTC, 실제 재생은 LiveCctv/useWebRtcStream에서 처리)
 *
 * LIVE 여부는 LiveCctv 우상단 배지가 실제 스트림 상태를 반영해 표시하므로
 * 이 헤더에서는 따로 표시하지 않는다.
 */
export default function CctvModal({ label = 'CCTV · 실시간', onClose }) {
  return (
    <ModalOverlay onClose={onClose} width="min(1040px, 92vw)">
      {/* header */}
      <div
        style={{
          padding: '16px 22px',
          borderBottom: `1px solid ${C.line}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontWeight: 800, fontSize: 16 }}>{label}</span>
        </div>
        <button
          type="button"
          onClick={onClose}
          style={{ background: C.line3, border: 'none', color: C.text, width: 30, height: 30, borderRadius: 7, cursor: 'pointer', fontSize: 15, flex: 'none' }}
        >
          ✕
        </button>
      </div>

      {/* video */}
      <div style={{ padding: 18, display: 'flex' }}>
        <LiveCctv
          label={label}
          containerStyle={{ aspectRatio: '16 / 9', maxHeight: '72vh', minHeight: 320 }}
        />
      </div>
    </ModalOverlay>
  );
}
