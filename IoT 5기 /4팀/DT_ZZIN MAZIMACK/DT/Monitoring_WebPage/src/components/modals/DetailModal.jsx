import { useState } from 'react';
import ModalOverlay from './ModalOverlay';
import LiveCctv from '../dashboard/LiveCctv';
import RobotCam from '../dashboard/RobotCam';
import { C, MONO } from '../../data/theme';

// event.metrics(kind별) → 실제 표시할 항목만 뽑습니다. 없는 값은 만들어내지 않습니다.
function metricRows(event) {
  if (!event) return [];
  if (event.metrics.kind === 'zone') {
    return [{ label: 'MQ2 상대 세기', value: (event.metrics.intensity ?? 0).toFixed(1), unit: '/100' }];
  }
  if (event.metrics.kind === 'fire') {
    return [
      { label: '불꽃 감지', value: event.metrics.flameDetected ? '감지됨' : '미감지' },
      { label: '경보 수준', value: event.metrics.alertLevel || '—' },
    ];
  }
  return [];
}

/**
 * Event detail modal: robot snapshot + CCTV + real event metrics + confirm.
 *
 * 위험 이벤트는 바로 '처리완료'할 수 없습니다 — 직원 앱으로 보낼 지시사항을
 * 먼저 작성해야 합니다(현장 확인 지시 없이 그냥 닫히는 걸 막기 위함).
 *
 * 확인 시 POST /api/instructions로 서버에 저장되고(useMonitoringDashboard의
 * confirmEvent), 동시에 이벤트 로그에도 남습니다.
 */
export default function DetailModal({ event, onClose, onConfirm }) {
  const [instruction, setInstruction] = useState('');
  if (!event) return null;
  const rows = metricRows(event);
  const needsInstruction = event.showConfirmBtn;
  const canConfirm = !needsInstruction || instruction.trim().length > 0;

  return (
    <ModalOverlay onClose={onClose} width={760}>
      {/* header */}
      <div
        style={{
          padding: '20px 24px',
          borderBottom: `1px solid ${C.line}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: event.sc, background: event.sb, padding: '3px 9px', borderRadius: 5 }}>
              {event.status}
            </span>
            <span style={{ fontFamily: MONO, fontSize: 11, color: C.muted }}>{event.time}</span>
          </div>
          <div style={{ fontWeight: 800, fontSize: 18, marginTop: 9 }}>{event.title}</div>
          <div style={{ fontSize: 12.5, color: C.sub, marginTop: 5, maxWidth: 520, lineHeight: 1.55 }}>{event.desc}</div>
        </div>
        <button
          type="button"
          onClick={onClose}
          style={{ background: C.line3, border: 'none', color: C.text, width: 30, height: 30, borderRadius: 7, cursor: 'pointer', fontSize: 15, flex: 'none' }}
        >
          ✕
        </button>
      </div>

      {/* media */}
      <div style={{ padding: '20px 24px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        <div>
          <div style={{ fontSize: 11, color: C.muted, marginBottom: 7, fontFamily: MONO }}>현장 스냅샷 · 로봇 카메라</div>
          <RobotCam label="로봇 카메라" style={{ height: 170 }} />
        </div>
        <div>
          <div style={{ fontSize: 11, color: C.muted, marginBottom: 7, fontFamily: MONO }}>CCTV · 실시간</div>
          {/* IP캠 RTSP → FastAPI(aiortc) → WebRTC 실시간 영상 (LiveCctv 컴포넌트에서 처리) */}
          <LiveCctv label="실시간 CCTV (육안 확인)" containerStyle={{ height: 170 }} />
        </div>
      </div>

      {/* metrics: 이벤트 종류에 실제로 있는 값만 표시 */}
      {rows.length > 0 && (
        <div style={{ padding: '0 24px 8px', display: 'grid', gridTemplateColumns: `repeat(${rows.length},1fr)`, gap: 12 }}>
          {rows.map((m) => (
            <Metric key={m.label} label={m.label} value={m.value} unit={m.unit} valueColor={event.sc} />
          ))}
        </div>
      )}

      {/* 직원 지시사항: 위험 미확인 이벤트만 — 작성해야 처리완료할 수 있습니다 */}
      {needsInstruction && (
        <div style={{ padding: '10px 24px 0' }}>
          <label style={{ fontSize: 11, color: C.muted, fontFamily: MONO, display: 'block', marginBottom: 7 }}>
            직원 지시사항 <span style={{ color: C.redSoft }}>*</span>
            <span style={{ color: C.faint, fontWeight: 400 }}> — 현장 직원 앱으로 전달됩니다</span>
          </label>
          <textarea
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            placeholder="예: 현장 확인 후 소화기 위치로 이동, 인근 인원 대피 유도"
            rows={3}
            style={{
              width: '100%',
              resize: 'vertical',
              background: C.bgDeep,
              border: `1px solid ${instruction.trim() ? C.line2 : '#6b3418'}`,
              borderRadius: 8,
              padding: '10px 12px',
              color: C.text,
              fontSize: 13,
              lineHeight: 1.5,
              fontFamily: 'inherit',
              outline: 'none',
            }}
          />
        </div>
      )}

      {/* footer */}
      <div style={{ padding: '16px 24px 22px', display: 'flex', gap: 10, justifyContent: 'flex-end', alignItems: 'center' }}>
        {needsInstruction && !canConfirm && (
          <span style={{ fontSize: 11.5, color: C.faint, marginRight: 'auto' }}>지시사항을 입력해야 처리완료할 수 있습니다</span>
        )}
        <button
          type="button"
          onClick={onClose}
          className="btn-ghost"
          style={{ background: C.line3, border: `1px solid ${C.line2}`, color: C.text, fontWeight: 600, fontSize: 13, padding: '11px 20px', borderRadius: 9, cursor: 'pointer' }}
        >
          닫기
        </button>
        {event.showConfirmBtn && (
          <button
            type="button"
            disabled={!canConfirm}
            onClick={() => onConfirm(event.id, instruction.trim())}
            className="btn-primary"
            style={{
              background: C.orange,
              border: 'none',
              color: C.ink,
              fontWeight: 800,
              fontSize: 13,
              padding: '11px 24px',
              borderRadius: 9,
              cursor: canConfirm ? 'pointer' : 'default',
              opacity: canConfirm ? 1 : 0.45,
            }}
          >
            ✓ 지시 전달 · 처리완료
          </button>
        )}
      </div>
    </ModalOverlay>
  );
}

function Metric({ label, value, unit, valueColor }) {
  return (
    <div style={{ background: C.card, border: `1px solid ${C.line2}`, borderRadius: 9, padding: 13 }}>
      <div style={{ fontSize: 11, color: C.muted }}>{label}</div>
      <div style={{ fontFamily: MONO, fontSize: 22, fontWeight: 700, color: valueColor, marginTop: 4 }}>
        {value} {unit && <span style={{ fontSize: 12, color: C.muted }}>{unit}</span>}
      </div>
    </div>
  );
}
