import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Combines array of tailwind class values. Useful for conditional styling
 * @param inputs
 * @returns {string} - Combined tailwind classes
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const textOverflowEllipsis =
  "text-ellipsis overflow-hidden whitespace-nowrap";

export const centerAbsoluteStyle =
  "absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2";
