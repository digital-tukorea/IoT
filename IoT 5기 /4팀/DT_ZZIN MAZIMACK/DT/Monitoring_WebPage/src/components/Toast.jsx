import { C } from '../data/theme';

/** Bottom-centered success toast. */
export default function Toast({ message }) {
  if (!message) return null;
  return (
    <div
      style={{
        position: 'absolute',
        bottom: 26,
        left: '50%',
        transform: 'translateX(-50%)',
        background: '#14301d',
        border: '1px solid #2f6b45',
        color: C.greenSoft,
        fontWeight: 700,
        fontSize: 13.5,
        padding: '13px 22px',
        borderRadius: 11,
        zIndex: 20,
        animation: 'fadeUp .25s ease',
        boxShadow: '0 20px 50px -12px rgba(0,0,0,.6)',
      }}
    >
      ✓ {message}
    </div>
  );
}
