import React, { PropsWithChildren, ComponentProps, ReactNode } from "react";

export type TextKind =
  | "title"
  | "h1-bold"
  | "h2"
  | "h2-medium"
  | "h2-bold"
  | "h3"
  | "h3-bold"
  | "body1"
  | "body1-medium"
  | "body1-bold"
  | "body2"
  | "body2-bold"
  | "meta"
  | "meta-bold"
  | "tag"
  | "tag-bold";

export interface TextStyle {
  fontSize: string;
  fontStyle?: "normal" | "italic";
  fontWeight: string;
  lineHeight: string;
  letterSpacing?: string;
}
export const textStyles: Record<TextKind, TextStyle> = {
  title: {
    fontSize: "34px",
    fontStyle: "normal",
    fontWeight: "600",
    lineHeight: "41px",
    // letterSpacing: "0.4px",
  },
  "h1-bold": {
    fontSize: "28px",
    fontStyle: "normal",
    fontWeight: "599",
    lineHeight: "34px",
    // letterSpacing: "0.38px",
  },
  h2: {
    fontSize: "22px",
    fontStyle: "normal",
    fontWeight: "410",
    lineHeight: "28px",
    // letterSpacing: "-0.26px",
  },
  "h2-medium": {
    fontSize: "22px",
    fontStyle: "normal",
    fontWeight: "500",
    lineHeight: "28px",
    // letterSpacing: "-0.26px",
  },
  "h2-bold": {
    fontSize: "22px",
    fontStyle: "normal",
    fontWeight: "599",
    lineHeight: "28px",
    // letterSpacing: "-0.26px",
  },
  h3: {
    fontSize: "20px",
    fontStyle: "normal",
    fontWeight: "410",
    lineHeight: "25px",
    // letterSpacing: "-0.43px",
  },
  "h3-bold": {
    fontSize: "20px",
    fontStyle: "normal",
    fontWeight: "600",
    lineHeight: "25px",
    // letterSpacing: "-0.43px",
  },
  body1: {
    fontSize: "17px",
    fontStyle: "normal",
    fontWeight: "410",
    lineHeight: "24px",
    // letterSpacing: "-0.3px",
  },
  "body1-medium": {
    fontSize: "15px",
    fontStyle: "normal",
    fontWeight: "500",
    lineHeight: "24px",
    // letterSpacing: "-0.43px",
  },
  "body1-bold": {
    fontSize: "17px",
    fontStyle: "normal",
    fontWeight: "599",
    lineHeight: "24px",
    // letterSpacing: "-0.23px",
  },
  body2: {
    fontSize: "15px",
    fontStyle: "normal",
    fontWeight: "410",
    lineHeight: "20px",
    // letterSpacing: "-0.23px",
  },
  "body2-bold": {
    fontSize: "15px",
    fontStyle: "normal",
    fontWeight: "590",
    lineHeight: "20px",
    // letterSpacing: "-0.23px",
  },
  meta: {
    fontSize: "12px",
    fontStyle: "normal",
    fontWeight: "410",
    lineHeight: "16px",
    // letterSpacing: "-0.23px",
  },
  "meta-bold": {
    fontSize: "12px",
    fontStyle: "normal",
    fontWeight: "490",
    lineHeight: "16px",
  },
  tag: {
    fontSize: "11px",
    fontStyle: "normal",
    fontWeight: "300",
    lineHeight: "13px",
    // letterSpacing: "0.06px",
  },
  "tag-bold": {
    fontSize: "11px",
    fontStyle: "normal",
    fontWeight: "599",
    lineHeight: "13px",
    // letterSpacing: "0.06px",
  },
};

interface TextProps extends ComponentProps<"div"> {
  kind: TextKind;
}

export function Text({
  kind,
  children,
  ...props
}: PropsWithChildren<TextProps>) {
  const textStyle = textStyles[kind];
  return (
    <div {...props} style={{ ...textStyle, ...props.style }}>
      {children}
    </div>
  );
}
