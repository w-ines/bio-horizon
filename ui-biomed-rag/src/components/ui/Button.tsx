import { forwardRef, type ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement>;

export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { className, ...props },
  ref
) {
  return (
    <button
      ref={ref}
      className={[
        "medical-button-primary",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...props}
    />
  );
});


