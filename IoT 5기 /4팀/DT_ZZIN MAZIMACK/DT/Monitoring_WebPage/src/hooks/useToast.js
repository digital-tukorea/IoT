import { useState, useRef, useCallback, useEffect } from 'react';

/**
 * Transient toast message with auto-dismiss.
 * `show(message)` displays it and clears any previous timer.
 */
export function useToast(duration = 3200) {
  const [toast, setToast] = useState('');
  const timerRef = useRef(null);

  const show = useCallback(
    (message) => {
      setToast(message);
      clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setToast(''), duration);
    },
    [duration],
  );

  const clear = useCallback(() => {
    clearTimeout(timerRef.current);
    setToast('');
  }, []);

  // Clean up the pending timer on unmount.
  useEffect(() => () => clearTimeout(timerRef.current), []);

  return { toast, show, clear };
}
