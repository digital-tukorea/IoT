import ModalOverlay from './ModalOverlay';
import { C, MONO } from '../../data/theme';

const GRID_COLS = '84px 90px 110px 90px 1fr';

const TYPE_LABEL = {
  created: '발생',
  resolved: '정상 복귀',
  acked: '처리완료 확인',
};
const TYPE_COLOR = {
  created: C.redSoft,
  resolved: C.greenSoft,
  acked: C.amberSoft,
};
const KIND_LABEL = { zone: '구역 센서', fire: '화재' };

/** 이벤트 로그: 카드가 정상 복귀로 사라져도 여기엔 발생/해제/확인 기록이 남습니다. */
export default function EventLogModal({ rows, onClose }) {
  return (
    <ModalOverlay onClose={onClose} width={780} maxHeight={640}>
      <div style={{ padding: '20px 24px', borderBottom: `1px solid ${C.line}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontWeight: 800, fontSize: 17 }}>이벤트 로그</div>
        <button
          type="button"
          onClick={onClose}
          style={{ background: C.line3, border: 'none', color: C.text, width: 30, height: 30, borderRadius: 7, cursor: 'pointer', fontSize: 15 }}
        >
          ✕
        </button>
      </div>

      <div style={{ padding: '16px 24px 22px', overflowY: 'auto' }}>
        {rows.length === 0 ? (
          <div style={{ padding: '32px 12px', textAlign: 'center', color: C.faint, fontSize: 12.5 }}>기록된 이벤트가 없습니다</div>
        ) : (
          <div style={{ border: `1px solid ${C.line}`, borderRadius: 10, overflow: 'hidden' }}>
            <div style={{ display: 'grid', gridTemplateColumns: GRID_COLS, background: C.panel2, padding: '10px 14px', fontSize: 11, color: C.muted, fontFamily: MONO, fontWeight: 600 }}>
              <span>시각</span>
              <span>종류</span>
              <span>구역/위치</span>
              <span>레벨</span>
              <span>내용</span>
            </div>
            {rows.map((r) => (
              <div key={r.id} style={{ borderTop: '1px solid #252320' }}>
                <div style={{ display: 'grid', gridTemplateColumns: GRID_COLS, padding: '10px 14px', fontSize: 12, alignItems: 'center' }}>
                  <span style={{ fontFamily: MONO, color: C.sub }}>{new Date(r.at).toLocaleTimeString('ko-KR', { hour12: false })}</span>
                  <span style={{ color: C.muted }}>{KIND_LABEL[r.kind] || r.kind}</span>
                  <span>{r.label}</span>
                  <span style={{ color: r.level === '위험' ? C.redSoft : r.level === '주의' ? C.amberSoft : C.faint }}>{r.level || '—'}</span>
                  <span style={{ fontWeight: 700, color: TYPE_COLOR[r.type] || C.text }}>{TYPE_LABEL[r.type] || r.type}</span>
                </div>
                {r.instruction && (
                  <div style={{ padding: '0 14px 10px 14px', fontSize: 11.5, color: C.amberSoft }}>
                    <span style={{ color: C.faint }}>지시사항: </span>
                    {r.instruction}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </ModalOverlay>
  );
}
