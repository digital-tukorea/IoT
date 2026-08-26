import { useEffect } from 'react';

/**
 * Backdrop + centered dialog. Closes on backdrop click and on Escape;
 * clicks inside the dialog are stopped from bubbling to the backdrop.
 */
export default function ModalOverlay({ onClose, children, width, maxHeight }) {
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div
      onClick={onClose}
      style={{
        position: 'absolute',
        inset: 0,
        background: 'rgba(8,7,6,.72)',
        backdropFilter: 'blur(3px)',
        display: 'grid',
        placeItems: 'center',
        zIndex: 10,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width,
          maxHeight,
          background: '#1f1e1b',
          border: '1px solid #33302b',
          borderRadius: 16,
          overflow: 'hidden',
          boxShadow: '0 40px 90px -20px rgba(0,0,0,.7)',
          animation: 'fadeUp .22s ease',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {children}
      </div>
    </div>
  );
}
