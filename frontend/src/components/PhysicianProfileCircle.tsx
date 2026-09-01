import { ComponentProps } from "react";
import { Icons } from "./icons";
import { cn } from "@/utils/cssUtils";

interface PhysicianProfileCircleProps extends ComponentProps<"div"> {
  colorClassName?: string;
}

export function PhysicianProfileCircle({
  className,
  colorClassName = "text-brand-teal",
  ...props
}: PhysicianProfileCircleProps) {
  return (
    <div className={cn("w-6 rounded-xl flex-shrink-0", className)} {...props}>
      <Icons.threadIcon className={cn(colorClassName)} />
    </div>
  );
}
