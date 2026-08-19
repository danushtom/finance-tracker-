import * as React from "react"
import { cn } from "../lib/utils"

type ButtonVariant = "default" | "outline" | "ghost" | "secondary" | "destructive"
type ButtonSize = "default" | "sm" | "lg" | "icon"

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  /**
   * Render the single child element instead of a `<button>`, keeping the
   * button's styling. Mirrors the shadcn/Radix `asChild` API without
   * pulling in `@radix-ui/react-slot` — used for anchors (e.g. the export
   * download links) that should look like buttons but must stay `<a>`.
   */
  asChild?: boolean
}

const VARIANTS: Record<ButtonVariant, string> = {
  default: "bg-primary text-white hover:bg-primary-hover",
  outline: "border border-border bg-transparent hover:bg-muted text-card-foreground",
  ghost: "hover:bg-muted text-card-foreground",
  secondary: "bg-muted text-muted-foreground hover:bg-muted/80",
  destructive: "bg-red-600 text-white hover:bg-red-700",
}

const SIZES: Record<ButtonSize, string> = {
  default: "h-10 px-4 py-2",
  sm: "h-9 rounded-full px-3",
  lg: "h-11 rounded-full px-8",
  icon: "h-10 w-10",
}

const BASE_CLASSES =
  "inline-flex items-center justify-center rounded-full text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50"

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { className, variant = "default", size = "default", asChild = false, children, ...props },
    ref
  ) => {
    const classes = cn(BASE_CLASSES, VARIANTS[variant], SIZES[size], className)

    if (asChild && React.isValidElement(children)) {
      const child = children as React.ReactElement<Record<string, unknown>>
      return React.cloneElement(child, {
        ...props,
        className: cn(classes, child.props.className as string | undefined),
      })
    }

    return (
      <button ref={ref} className={classes} {...props}>
        {children}
      </button>
    )
  }
)
Button.displayName = "Button"

export { Button }
