import { C, MONO } from '../../data/theme';

/** Right column: event feed with status lifecycle legend and action buttons. */
export default function EventPanel({ events, onOpenDetail, onOpenLog }) {
  return (
    <div style={{ borderLeft: `1px solid ${C.line}`, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <div
        style={{
          padding: '16px 18px',
          borderBottom: `1px solid ${C.line}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <span style={{ fontWeight: 800, fontSize: 14 }}>발생 이벤트</span>
        <button
          type="button"
          onClick={onOpenLog}
          className="btn-ghost"
          style={{ background: 'transparent', border: 'none', color: C.muted, fontSize: 11.5, fontWeight: 600, cursor: 'pointer', padding: '4px 6px' }}
        >
          이벤트 로그
        </button>
      </div>

      {/* status lifecycle legend */}
      <div
        style={{
          padding: '12px 18px',
          borderBottom: `1px solid ${C.line}`,
          display: 'flex',
          gap: 6,
          fontSize: 9.5,
          fontFamily: MONO,
          color: C.muted,
          flexWrap: 'wrap',
          alignItems: 'center',
        }}
      >
        <LegendTag bg={C.line3}>미확인</LegendTag>›
        <LegendTag bg="#3a1f14" color={C.orangeSoft}>확인중</LegendTag>›
        <LegendTag bg="#3a2410" color={C.amberSoft}>확정</LegendTag>›
        <LegendTag bg="#14301d" color={C.greenSoft}>처리완료</LegendTag>
      </div>

      {/* event list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 10, minHeight: 0 }}>
        {events.length === 0 && (
          <div style={{ padding: '24px 12px', textAlign: 'center', color: C.faint, fontSize: 12 }}>
            발생한 이벤트 없음
          </div>
        )}
        {events.map((e) => (
          <EventCard key={e.id} e={e} onOpenDetail={onOpenDetail} />
        ))}
      </div>
    </div>
  );
}

function LegendTag({ bg, color, children }) {
  return (
    <span style={{ background: bg, color: color || C.text, padding: '2px 6px', borderRadius: 4 }}>{children}</span>
  );
}

function EventCard({ e, onOpenDetail }) {
  return (
    <div
      className="event-card"
      style={{
        background: e.cardBg,
        border: e.border,
        borderRadius: 10,
        padding: 13,
        transition: 'transform .12s',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 7 }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: e.sc, background: e.sb, padding: '3px 8px', borderRadius: 5 }}>
          {e.status}
        </span>
        <span style={{ fontFamily: MONO, fontSize: 10, color: C.muted }}>{e.time}</span>
      </div>
      <div style={{ fontWeight: 700, fontSize: 13.5 }}>{e.title}</div>
      <div style={{ fontSize: 11, color: C.sub, marginTop: 4, lineHeight: 1.5 }}>{e.desc}</div>

      {e.showDetailBtn && (
        <button
          type="button"
          onClick={() => onOpenDetail(e.id)}
          style={
            e.showConfirmBtn
              ? {
                  width: '100%',
                  marginTop: 10,
                  background: C.orange,
                  border: 'none',
                  color: C.ink,
                  fontWeight: 800,
                  fontSize: 11.5,
                  padding: 9,
                  borderRadius: 7,
                  cursor: 'pointer',
                }
              : {
                  width: '100%',
                  marginTop: 10,
                  background: '#3a1f14',
                  border: '1px solid #6b3418',
                  color: C.orangeSoft,
                  fontWeight: 700,
                  fontSize: 11.5,
                  padding: 8,
                  borderRadius: 7,
                  cursor: 'pointer',
                }
          }
        >
          {/* 위험 미확인 이벤트는 지시사항을 써야 처리완료되므로 상세 모달로 보냅니다. */}
          {e.showConfirmBtn ? '지시사항 작성 · 처리완료' : '상세 · 스냅샷 보기'}
        </button>
      )}
    </div>
  );
}
