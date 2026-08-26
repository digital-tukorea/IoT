import { useLoginForm } from '../hooks/useLoginForm';
import { C, MONO } from '../data/theme';

const fieldStyle = {
  background: C.bgDeep,
  border: `1px solid ${C.line2}`,
  borderRadius: 8,
  padding: '13px 15px',
  margin: '7px 0 18px',
  color: C.text,
  fontSize: 14,
  width: '100%',
  outline: 'none',
};

const labelStyle = {
  fontSize: 12,
  color: C.muted,
  fontWeight: 600,
  fontFamily: MONO,
};

export default function LoginScreen({ onLogin }) {
  const f = useLoginForm(onLogin);

  return (
    <div style={{ position: 'absolute', inset: 0, display: 'flex' }}>
      {/* Left branding panel */}
      <div
        style={{
          flex: 1.2,
          position: 'relative',
          background: C.bgDeep,
          backgroundImage:
            `linear-gradient(${C.gridLine} 1px,transparent 1px),linear-gradient(90deg,${C.gridLine} 1px,transparent 1px)`,
          backgroundSize: '34px 34px',
          padding: 64,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          borderRight: `1px solid ${C.line}`,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
          <div
            style={{
              width: 34,
              height: 34,
              borderRadius: 8,
              background: C.orange,
              display: 'grid',
              placeItems: 'center',
              fontWeight: 800,
              color: C.ink,
              fontSize: 17,
            }}
          >
            S
          </div>
          <div style={{ fontWeight: 800, fontSize: 18 }}>SafeScout</div>
        </div>
        <div>
          <div style={{ fontFamily: MONO, fontSize: 12, color: C.orange, letterSpacing: '.12em', marginBottom: 14 }}>
            FIRE · GAS · ROBOT PATROL
          </div>
          <div style={{ fontSize: 36, fontWeight: 800, lineHeight: 1.3 }}>
            현장은 넓고,
            <br />
            눈은 하나면 됩니다.
          </div>
          <p style={{ fontSize: 15, color: C.sub, lineHeight: 1.7, marginTop: 16, maxWidth: 430 }}>
            로봇이 순찰하고, 평면도 위 모든 신호를 한 화면에서 확인하세요.
          </p>
        </div>
        <div />
      </div>

      {/* Right form panel */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '64px 72px',
          background: C.panel,
        }}
      >
        <div style={{ display: 'flex', gap: 24, marginBottom: 30, borderBottom: `1px solid ${C.line3}` }}>
          <TabButton active={f.tab === 'login'} onClick={() => f.setTab('login')}>
            로그인
          </TabButton>
          <TabButton active={f.tab === 'signup'} onClick={() => f.setTab('signup')}>
            회원가입
          </TabButton>
        </div>

        <form onSubmit={f.submit}>
          <label style={labelStyle} htmlFor="login-id">
            ID
          </label>
          <input
            id="login-id"
            value={f.id}
            onChange={(e) => f.setId(e.target.value)}
            autoComplete="username"
            style={fieldStyle}
          />

          <label style={labelStyle} htmlFor="login-pw">
            PASSWORD
          </label>
          <div style={{ position: 'relative', margin: '7px 0 10px' }}>
            <input
              id="login-pw"
              type={f.showPassword ? 'text' : 'password'}
              value={f.password}
              onChange={(e) => f.setPassword(e.target.value)}
              autoComplete="current-password"
              style={{ ...fieldStyle, margin: 0, letterSpacing: f.showPassword ? 'normal' : '.2em', paddingRight: 54 }}
            />
            <button
              type="button"
              onClick={f.toggleShowPassword}
              style={{
                position: 'absolute',
                right: 10,
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'none',
                border: 'none',
                color: C.muted,
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              {f.showPassword ? '숨김' : '표시'}
            </button>
          </div>

          {f.tab === 'signup' ? (
            <div style={{ marginBottom: 24 }}>
              <label style={labelStyle}>계정 유형</label>
              <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
                <RoleOption label="직원" active={f.role === 'staff'} onClick={() => f.setRole('staff')} />
                <RoleOption label="관리자" active={f.role === 'admin'} onClick={() => f.setRole('admin')} />
              </div>
            </div>
          ) : (
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                fontSize: 12.5,
                color: C.muted,
                marginBottom: 24,
              }}
            >
              <span
                onClick={f.toggleRemember}
                style={{ display: 'flex', alignItems: 'center', gap: 7, cursor: 'pointer', userSelect: 'none' }}
              >
                <span
                  style={{
                    width: 15,
                    height: 15,
                    borderRadius: 4,
                    border: `1px solid ${f.remember ? C.orange : C.line2}`,
                    background: f.remember ? '#3a1f14' : 'transparent',
                    display: 'inline-grid',
                    placeItems: 'center',
                    color: C.orange,
                    fontSize: 10,
                  }}
                >
                  {f.remember ? '✓' : ''}
                </span>
                로그인 유지
              </span>
              <a href="#" onClick={(e) => e.preventDefault()}>
                비밀번호 찾기
              </a>
            </div>
          )}

          {f.error && (
            <div style={{ color: C.redSoft, fontSize: 12.5, marginBottom: 12 }}>{f.error}</div>
          )}
          {f.notice && (
            <div style={{ color: C.greenSoft, fontSize: 12.5, marginBottom: 12 }}>{f.notice}</div>
          )}

          <button
            type="submit"
            disabled={f.submitting}
            className="btn-primary"
            style={{
              width: '100%',
              background: C.orange,
              border: 'none',
              color: C.ink,
              fontWeight: 800,
              fontSize: 15,
              padding: 15,
              borderRadius: 9,
              cursor: f.submitting ? 'default' : 'pointer',
              opacity: f.submitting ? 0.6 : 1,
              transition: 'filter .15s',
            }}
          >
            {f.submitting ? '처리중…' : f.tab === 'login' ? '로그인' : '회원가입 신청'}
          </button>
        </form>

        <p style={{ fontSize: 12.5, color: C.muted, textAlign: 'center', marginTop: 18 }}>
          계정이 없으신가요?{' '}
          <a href="#" onClick={(e) => { e.preventDefault(); f.setTab('signup'); }}>
            회원가입 신청
          </a>
        </p>
      </div>
    </div>
  );
}

function RoleOption({ label, active, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        flex: 1,
        padding: '11px 0',
        borderRadius: 8,
        border: `1px solid ${active ? C.orange : C.line2}`,
        background: active ? '#3a1f14' : C.bgDeep,
        color: active ? C.orange : C.muted,
        fontWeight: 700,
        fontSize: 13.5,
        cursor: 'pointer',
      }}
    >
      {label}
    </button>
  );
}

function TabButton({ active, onClick, children }) {
  return (
    <span
      onClick={onClick}
      style={{
        paddingBottom: 12,
        fontWeight: active ? 700 : 600,
        fontSize: 14,
        borderBottom: active ? `2.5px solid ${C.orange}` : '2.5px solid transparent',
        color: active ? C.orange : C.muted,
        cursor: 'pointer',
        marginBottom: -1,
      }}
    >
      {children}
    </span>
  );
}
