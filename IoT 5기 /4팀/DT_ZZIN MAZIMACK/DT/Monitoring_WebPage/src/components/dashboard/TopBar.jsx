import { useEffect, useState } from 'react';
import { C, MONO } from '../../data/theme';

/** Dashboard header: brand, live situation badge, clock, logout. */
export default function TopBar({ head, onLogout }) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div
      style={{
        height: 58,
        flex: 'none',
        background: C.panel,
        borderBottom: `1px solid ${C.line}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
        <div
          style={{
            width: 30,
            height: 30,
            borderRadius: 7,
            background: C.orange,
            display: 'grid',
            placeItems: 'center',
            fontWeight: 800,
            color: C.ink,
            fontSize: 15,
          }}
        >
          S
        </div>
        <div style={{ fontWeight: 800, fontSize: 15, letterSpacing: '.03em' }}>SafeScout</div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '7px 13px',
            borderRadius: 7,
            background: head.bg,
            border: `1px solid ${head.border}`,
          }}
        >
          <span style={{ width: 9, height: 9, borderRadius: '50%', background: head.color, animation: 'pulseDot 1.1s infinite' }} />
          <span style={{ fontWeight: 700, color: head.color, fontSize: 12.5 }}>{head.headline}</span>
        </div>

        <span style={{ fontFamily: MONO, color: C.muted, fontSize: 13 }}>
          {now.toLocaleString('ko-KR', { hour12: false })}
        </span>

        <button
          type="button"
          onClick={onLogout}
          title="로그아웃"
          className="btn-ghost"
          style={{
            height: 32,
            padding: '0 14px',
            borderRadius: 16,
            background: C.line3,
            border: 'none',
            color: C.text,
            fontSize: 12.5,
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          로그아웃
        </button>
      </div>
    </div>
  );
}
