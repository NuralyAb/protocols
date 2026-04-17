'use client';
import { forwardRef, type ButtonHTMLAttributes } from 'react';
import { cn } from '@/lib/cn';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline';
type Size = 'sm' | 'md' | 'lg' | 'icon';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const base =
  'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors duration-150 ease-out ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-bg ' +
  'disabled:opacity-50 disabled:pointer-events-none select-none whitespace-nowrap';

const variants: Record<Variant, string> = {
  primary:
    'bg-primary text-primary-fg shadow-xs hover:bg-primary/90 active:bg-primary/95',
  secondary:
    'bg-surface-1 text-fg border border-border shadow-xs hover:bg-surface-2 active:bg-surface-2',
  outline:
    'border border-border text-fg hover:bg-surface-2 active:bg-surface-2',
  ghost:
    'text-fg hover:bg-muted-bg active:bg-muted-bg',
  danger:
    'bg-danger text-white shadow-xs hover:bg-danger/90 active:bg-danger/95',
};

const sizes: Record<Size, string> = {
  sm: 'h-8 px-3 text-sm gap-1.5 [&_svg]:size-4',
  md: 'h-10 px-4 text-sm gap-2 [&_svg]:size-4',
  lg: 'h-11 px-5 text-base gap-2 [&_svg]:size-5',
  icon: 'h-10 w-10 [&_svg]:size-4',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', loading, disabled, children, ...props }, ref) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      data-loading={loading || undefined}
      className={cn(base, variants[variant], sizes[size], className)}
      {...props}
    >
      {loading && (
        <span
          aria-hidden
          className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent"
        />
      )}
      {children}
    </button>
  )
);
Button.displayName = 'Button';
