import { forwardRef, type InputHTMLAttributes } from "react";

type Props = InputHTMLAttributes<HTMLInputElement>;

export const Input = forwardRef<HTMLInputElement, Props>(function Input(
  { className, ...props },
  ref
) {
  return (
    <input
      ref={ref}
      className={[
        "medical-input",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...props}
    />
  );
});


