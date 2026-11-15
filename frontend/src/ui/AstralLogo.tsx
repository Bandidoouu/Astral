// ASTRAL logo (team design): a drill bit inside a flame-shaped outline. Interface lime
// (#c9f68b) on the dark header (#0b1119). The favicon (public/favicon.svg) is the same design
// with a thicker outline and three wider grooves so it reads at 16 px.
export default function AstralLogo({ size = 30 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 64 64" fill="none" strokeLinecap="round" aria-hidden="true" focusable="false">
    <defs>
    <clipPath id="astral-logo-clip">
    <path d="M0 -27 L12 13 L-12 13 Z"/>
    </clipPath>
    </defs>
    <path d="M32 61 C17 61 9 52 11 40 C12 33 16 29 17 23 C21 28 21 33 23 35 C22 25 26 14 33 6 C33 15 39 20 42 27 C44 23 44 19 43 15 C51 23 55 33 53 43 C51 54 44 61 32 61 Z" stroke="#c9f68b" strokeWidth="2.4" strokeLinejoin="round"/>
    <g transform="translate(32 33) scale(0.86)">
    <path d="M0 -27 L12 13 L-12 13 Z" fill="#c9f68b" stroke="#0b1119" strokeWidth="5" strokeLinejoin="round"/>
    <path d="M0 -27 L12 13 L-12 13 Z" fill="#c9f68b" stroke="#c9f68b" strokeWidth="1.5" strokeLinejoin="round"/>
    <g clipPath="url(#astral-logo-clip)">
    <path d="M-16 -14 Q0 -15 16 -24 L16 -21 Q0 -12 -16 -11 Z" fill="#0b1119"/>
    <path d="M-16 -7 Q0 -8 16 -17 L16 -14 Q0 -5 -16 -4 Z" fill="#0b1119"/>
    <path d="M-16 0 Q0 -1 16 -10 L16 -7 Q0 2 -16 3 Z" fill="#0b1119"/>
    <path d="M-16 7 Q0 6 16 -3 L16 0 Q0 9 -16 10 Z" fill="#0b1119"/>
    <path d="M-16 14 Q0 13 16 4 L16 7 Q0 16 -16 17 Z" fill="#0b1119"/>
    <path d="M-16 21 Q0 20 16 11 L16 14 Q0 23 -16 24 Z" fill="#0b1119"/>
    </g>
    <rect x="-13.5" y="13" width="27" height="4.5" rx="1" fill="#c9f68b" stroke="#0b1119" strokeWidth="2"/>
    <rect x="-4.5" y="17.5" width="9" height="8" rx="1" fill="#c9f68b" stroke="#0b1119" strokeWidth="2"/>
    </g>
  </svg>;
}
