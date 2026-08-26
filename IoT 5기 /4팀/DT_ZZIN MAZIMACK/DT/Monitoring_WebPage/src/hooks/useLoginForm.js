import { useState, useCallback } from 'react';
import { safescout } from '../api/safescout';

/**
 * 로그인/회원가입 폼 상태. 실제 백엔드(POST /api/auth/login, /api/auth/register)를
 * 호출합니다. 회원가입은 ID·비밀번호·역할(관리자/직원) 세 값만 받습니다.
 */
export function useLoginForm(onSubmit) {
  const [tab, setTab] = useState('login'); // 'login' | 'signup'
  const [id, setId] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('staff'); // 'staff' | 'admin' — 회원가입 시에만 씀
  const [remember, setRemember] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState(''); // 성공 안내(초록)
  const [submitting, setSubmitting] = useState(false);

  const changeTab = useCallback((next) => {
    setTab(next);
    setError('');
    setNotice('');
  }, []);

  const submit = useCallback(
    async (e) => {
      if (e && e.preventDefault) e.preventDefault();
      if (!id.trim() || !password.trim()) {
        setError('ID와 비밀번호를 입력하세요.');
        return;
      }
      setError('');
      setNotice('');
      setSubmitting(true);

      try {
        if (tab === 'signup') {
          await safescout.register(id.trim(), password, role);
          setNotice('가입이 완료되었습니다. 로그인해주세요.');
          setPassword('');
          setTab('login');
        } else {
          await safescout.login(id.trim(), password);
          onSubmit();
        }
      } catch (err) {
        setError(err.message || '요청 처리 중 오류가 발생했습니다.');
      } finally {
        setSubmitting(false);
      }
    },
    [tab, id, password, role, onSubmit],
  );

  return {
    tab,
    setTab: changeTab,
    id,
    setId,
    password,
    setPassword,
    role,
    setRole,
    remember,
    toggleRemember: () => setRemember((v) => !v),
    showPassword,
    toggleShowPassword: () => setShowPassword((v) => !v),
    error,
    notice,
    submitting,
    submit,
  };
}
