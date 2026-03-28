import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-emerald-500/10 text-emerald-400",
        emerald: "bg-emerald-500/10 text-emerald-400",
        cyan: "bg-cyan-500/10 text-cyan-400",
        amber: "bg-amber-500/10 text-amber-400",
        rose: "bg-rose-500/10 text-rose-400",
        gray: "bg-gray-500/10 text-gray-400",
        outline: "border border-sg-border text-muted-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
