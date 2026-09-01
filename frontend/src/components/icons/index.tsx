import { cn } from "@/utils/cssUtils";
import React from "react";

export type IconProps = React.HTMLAttributes<SVGElement>;

export const Icons = {
  threadIcon: (props: IconProps) => (
    <svg
      width="100%"
      height="100%"
      viewBox="0 0 32 32"
      fill="currentColor"
      xmlns="http://www.w3.org/2000/svg"
      {...props}
    >
      <rect width="100%" height="100%" rx="16" fill="currentColor" />
      <path
        d="M16.8889 8.00009C16.8889 7.50918 16.4909 7.11121 16 7.11121C15.5091 7.11121 15.1111 7.50918 15.1111 8.00009C15.1111 10.8342 14.5165 12.6718 13.4381 13.8101C12.3699 14.9375 10.6578 15.5557 8.00002 15.5557C7.5091 15.5557 7.11113 15.9536 7.11113 16.4445C7.11113 16.9355 7.5091 17.3334 8.00002 17.3334C10.6578 17.3334 12.3699 17.9516 13.4381 19.079C14.5165 20.2173 15.1111 22.0549 15.1111 24.889C15.1111 25.3799 15.5091 25.7779 16 25.7779C16.4909 25.7779 16.8889 25.3799 16.8889 24.889C16.8889 22.0549 17.4836 20.2173 18.562 19.079C19.6301 17.9516 21.3423 17.3334 24 17.3334C24.4909 17.3334 24.8889 16.9355 24.8889 16.4445C24.8889 15.9536 24.4909 15.5557 24 15.5557C21.3423 15.5557 19.6301 14.9375 18.562 13.8101C17.4836 12.6718 16.8889 10.8342 16.8889 8.00009Z"
        fill="white"
      />
    </svg>
  ),
  plane: (props: IconProps & { disabled?: boolean }) => (
    <svg
      {...props}
      viewBox="0 0 24 24"
      fill={`${
        props.disabled ? "hsl(var(--content-disabled))" : "currentColor"
      }`}
      xmlns="http://www.w3.org/2000/svg"
    >
      <path d="M3.11289 6.1782C2.44793 4.07252 4.63982 2.20178 6.61488 3.18931L19.7639 9.76383C21.6066 10.6851 21.6065 13.3147 19.7639 14.236L6.61487 20.8105C4.63981 21.798 2.44794 19.9273 3.11289 17.8216L4.6355 13H9.00001C9.55229 13 10 12.5523 10 12C10 11.4477 9.55229 11 9.00001 11H4.63556L3.11289 6.1782Z" />
    </svg>
  ),
  image: (props: IconProps) => (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      {...props}
    >
      <g id="images-1">
        <path
          id="Vector"
          d="M17.5 9C17.5 10.3807 16.3807 11.5 15 11.5C13.6193 11.5 12.5 10.3807 12.5 9C12.5 7.61929 13.6193 6.5 15 6.5C16.3807 6.5 17.5 7.61929 17.5 9Z"
          fill="currentColor"
        />
        <path
          id="Vector_2"
          fillRule="evenodd"
          clipRule="evenodd"
          d="M7 3H16.99C19.2 3 20.99 4.79 20.99 7V17C20.99 19.21 19.2 21 16.99 21H7C4.79 21 3 19.21 3 17V7C3 4.79 4.79 3 7 3ZM17 5H7V5.01C5.9 5.01 5 5.91 5 7.01V12.22L6.27 11.27L6.29 11.25C7.51 10.43 9.15 10.62 10.15 11.7C11.62 13.28 13.09 14.45 15 14.45C16.7 14.45 17.86 13.89 19 12.83V7C19 5.9 18.1 5 17 5Z"
          fill="currentColor"
        />
      </g>
    </svg>
  ),
  spinner: (props: IconProps) => (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...{ ...props, className: cn(props.className, "animate-spin") }}
    >
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  ),
};
