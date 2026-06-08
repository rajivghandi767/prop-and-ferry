import React from "react";

interface IconProps extends React.SVGProps<SVGSVGElement> {
  size?: number | string;
}

const BaseIcon = ({
  size = 24,
  className = "",
  children,
  viewBox = "0 0 24 24",
  fill = "none",
  stroke = "currentColor",
  strokeWidth = "1.75",
  ...props
}: IconProps & { children: React.ReactNode }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={size}
    height={size}
    viewBox={viewBox}
    fill={fill}
    stroke={stroke}
    strokeWidth={strokeWidth}
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-hidden="true"
    {...props}
  >
    {children}
  </svg>
);

// ─── Sun ──────────────────────────────────────────────────────────────────────
// Rays kept well inside the 24x24 box so stroke never clips.
export const Sun = (props: IconProps) => (
  <BaseIcon {...props}>
    <circle cx="12" cy="12" r="4" />
    {/* Cardinal rays */}
    <line x1="12" y1="2.5" x2="12" y2="5" />
    <line x1="12" y1="19" x2="12" y2="21.5" />
    <line x1="2.5" y1="12" x2="5" y2="12" />
    <line x1="19" y1="12" x2="21.5" y2="12" />
    {/* Diagonal rays */}
    <line x1="5.1" y1="5.1" x2="6.8" y2="6.8" />
    <line x1="17.2" y1="17.2" x2="18.9" y2="18.9" />
    <line x1="18.9" y1="5.1" x2="17.2" y2="6.8" />
    <line x1="6.8" y1="17.2" x2="5.1" y2="18.9" />
  </BaseIcon>
);

// ─── Moon ─────────────────────────────────────────────────────────────────────
export const Moon = (props: IconProps) => (
  <BaseIcon {...props}>
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
  </BaseIcon>
);

// ─── Plane ────────────────────────────────────────────────────────────────────
// Top-down silhouette — most recognisable airplane shape at 20–24px.
export const Plane = (props: IconProps) => (
  <BaseIcon {...props}>
    {/* Fuselage — narrow vertical body */}
    <ellipse cx="12" cy="11" rx="1.5" ry="8" />
    {/* Main wings — swept back */}
    <path d="M10.5 11 L2 16 L10.5 14" />
    <path d="M13.5 11 L22 16 L13.5 14" />
    {/* Tail stabilisers */}
    <path d="M10.5 18 L7 21 L10.5 20" />
    <path d="M13.5 18 L17 21 L13.5 20" />
  </BaseIcon>
);


// ─── Ship / Ferry ─────────────────────────────────────────────────────────────
// A clear, recognisable ferry silhouette. Hull, deck, funnel, wave.
export const Ship = (props: IconProps) => (
  <BaseIcon {...props}>
    {/* Hull */}
    <path d="M3 14 L5 19 Q12 21.5 19 19 L21 14 Z" />
    {/* Deck / superstructure box */}
    <rect x="6" y="10" width="12" height="4" rx="1" />
    {/* Funnel */}
    <rect x="10.5" y="7" width="3" height="3" rx="0.5" />
    {/* Funnel cap */}
    <line x1="10" y1="7" x2="14" y2="7" />
    {/* Porthole windows */}
    <circle cx="9" cy="12" r="0.75" fill="currentColor" stroke="none" />
    <circle cx="12" cy="12" r="0.75" fill="currentColor" stroke="none" />
    <circle cx="15" cy="12" r="0.75" fill="currentColor" stroke="none" />
    {/* Wake / water line */}
    <path d="M2 20.5 Q6 19.5 9 20.5 Q12 21.5 15 20.5 Q18 19.5 22 20.5" strokeWidth="1" />
  </BaseIcon>
);

// ─── Users ────────────────────────────────────────────────────────────────────
export const Users = (props: IconProps) => (
  <BaseIcon {...props}>
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
    <circle cx="9" cy="7" r="4" />
    <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
  </BaseIcon>
);
