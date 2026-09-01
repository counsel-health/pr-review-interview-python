import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../../utils/cssUtils";
import { Icons } from "../icons";

const buttonVariants = cva(
  cn(
    "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
    "disabled:pointer-events-none disabled:bg-button-disabled-background disabled:text-button-disabled-content"
  ),
  {
    variants: {
      variant: {
        primary:
          "bg-button-primary-background text-button-primary-content shadow hover:bg-button-primary-background/90",
        outline: "border border-border hover:bg-border/10",
        secondary:
          "bg-button-secondary-background text-button-secondary-content shadow-sm hover:bg-button-secondary-background/80",
        white: "bg-white shadow hover:bg-white/50",
        // ghost: "hover:bg-content-accent hover:text-accent-foreground",
        // link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        primary: "h-9 rounded-lg px-4 py-2",
        md: "h-8 rounded-md px-3 py-2",
        sm: "h-7 rounded-md px-3 py-[6px]",
        xs: "h-5 rounded-sm px-3 py-[6px]",
        lg: "h-12 rounded-lg px-4 py-3",
        // icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "primary",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      asChild = false,
      loading = false,
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    const Comp = asChild ? Slot : "button";
    const loadingSpiner = <Icons.spinner className="w-full h-full" />;
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
        disabled={disabled || loading}
      >
        {loading ? loadingSpiner : children}
      </Comp>
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
