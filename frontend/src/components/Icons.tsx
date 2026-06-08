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
  strokeWidth = "2",
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
    {...props}
  >
    {children}
  </svg>
);

export const Sun = (props: IconProps) => (
  <BaseIcon {...props}>
    <circle cx="12" cy="12" r="5" />
    <line x1="12" y1="1" x2="12" y2="3" />
    <line x1="12" y1="21" x2="12" y2="23" />
    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
    <line x1="1" y1="12" x2="3" y2="12" />
    <line x1="21" y1="12" x2="23" y2="12" />
    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
  </BaseIcon>
);

export const Moon = (props: IconProps) => (
  <BaseIcon {...props}>
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
  </BaseIcon>
);

export const Plane = (props: IconProps) => (
  <BaseIcon {...props}>
    <path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-1.1.1-1.4.5l-.3.4c-.4.5-.4 1.2 0 1.7l6.3 3.6-3.6 3.6-3.9-1.3c-.5-.2-1.1 0-1.4.4l-.2.3c-.4.5-.3 1.2.2 1.6l4 2.8 2.8 4c.4.5 1.1.6 1.6.2l.3-.2c.4-.3.6-.9.4-1.4l-1.3-3.9 3.6-3.6 3.6 6.3c.5.4 1.2.4 1.7 0l.4-.3c.4-.3.6-.9.5-1.4z" />
  </BaseIcon>
);

export const Ship = (props: IconProps) => (
  <BaseIcon {...props}>
    <path d="M2 21h20" />
    <path d="M19.3 14.8C21.1 13.5 22 11.7 22 10V8h-3V5a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v3H8V6a1 1 0 0 0-1-1H3a1 1 0 0 0-1 1v4c0 1.7.9 3.5 2.7 4.8" />
    <path d="M19 14.8c-.8.8-2 1.2-3 1.2s-2.2-.4-3-1.2c-.8.8-2 1.2-3 1.2s-2.2-.4-3-1.2" />
  </BaseIcon>
);

export const Users = (props: IconProps) => (
  <BaseIcon {...props}>
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
    <circle cx="9" cy="7" r="4" />
    <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
  </BaseIcon>
);
