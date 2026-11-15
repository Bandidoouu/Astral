// Original ASTRAL logo: a drill boring through an orbit (planetary sampling meets orbital
// mechanics). Three variants for the team to choose; the header uses LOGO_VARIANT.
// Colors: interface lime (#c9f68b) on the dark header (#0b1119).
export type LogoVariant = 'a' | 'b' | 'c';
export const LOGO_VARIANT: LogoVariant = 'b';

export default function AstralLogo({ size = 30, variant = LOGO_VARIANT }: { size?: number; variant?: LogoVariant }) {
  return <svg width={size} height={size} viewBox="0 0 64 64" fill="none" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
    {variant === 'a' && <><defs><clipPath id="a-body"><path d="M25 14 h14 v30 l-7 12 l-7 -12 z"/></clipPath></defs>
  <g transform="rotate(-16 32 34)"><path d="M5 34 A27 9 0 0 1 59 34" stroke="#c9f68b" strokeWidth="2.6" opacity="0.5"/></g>
  <g transform="rotate(38 32 32)">
    <rect x="29.5" y="3" width="5" height="12" rx="1" fill="#c9f68b"/>
    <path d="M25 14 h14 v30 l-7 12 l-7 -12 z" fill="#0b1119"/>
    <g clipPath="url(#a-body)" fill="#c9f68b">
      <path d="M20 12 L44 22 L44 28 L20 18 z"/><path d="M20 24 L44 34 L44 40 L20 30 z"/><path d="M20 36 L44 46 L44 52 L20 42 z"/>
      <path d="M20 48 L44 58 L44 64 L20 54 z"/>
    </g>
    <path d="M25 14 h14 v30 l-7 12 l-7 -12 z" stroke="#c9f68b" strokeWidth="2.6"/>
  </g>
  <g transform="rotate(-16 32 34)">
    <path d="M59 34 A27 9 0 0 1 5 34" stroke="#0b1119" strokeWidth="7"/>
    <path d="M59 34 A27 9 0 0 1 5 34" stroke="#c9f68b" strokeWidth="2.6"/>
  </g></>}
    {variant === 'b' && <><path d="M5 36 A27 8 0 0 1 59 36" stroke="#c9f68b" strokeWidth="2.4" opacity="0.55"/>
  <path d="M29 3 h6 v8 h-6 z" fill="#0b1119" stroke="#c9f68b" strokeWidth="3"/>
  <path d="M24 11 h16 v38 l-2.7 5 l-2.6 -5 l-2.7 5 l-2.7 -5 l-2.6 5 l-2.7 -5 z" fill="#0b1119" stroke="#c9f68b" strokeWidth="3"/>
  <path d="M24 18 L40 25 M24 30 L40 37 M24 42 L40 49" stroke="#c9f68b" strokeWidth="2.6"/>
  <path d="M59 36 A27 8 0 0 1 5 36" stroke="#0b1119" strokeWidth="7"/>
  <path d="M59 36 A27 8 0 0 1 5 36" stroke="#c9f68b" strokeWidth="2.4"/>
  <circle cx="53" cy="40.6" r="3.4" fill="#c9f68b"/></>}
    {variant === 'c' && <><path d="M32 58 L32 49
           C 40 49, 41 44.5, 32 44.5 C 23 44.5, 24 40, 32 40
           C 44 40, 45 34, 32 34 C 19 34, 20 28, 32 28
           C 50 28, 52 20.5, 32 20.5 C 12 20.5, 6 14, 32 14
           C 52 14, 60 10, 46 8"
        stroke="#c9f68b" strokeWidth="3.2"/>
  <circle cx="44" cy="7.6" r="3.2" fill="#c9f68b"/></>}
  </svg>;
}
