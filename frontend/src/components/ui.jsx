import React, { useEffect, useRef } from "react";
import { X } from "lucide-react";

export function Brand({ small = false }) {
  return (
    <div className={"brand " + (small ? "small" : "")}>
      <span className="brand-mark">
        <span />
        <span />
        <span />
      </span>
      {!small && (
        <>
          docmind<span className="brand-dot">.</span>
        </>
      )}
    </div>
  );
}
export function IconButton({ title, children, ...props }) {
  return (
    <button
      type="button"
      className="icon-button"
      aria-label={title}
      title={title}
      {...props}
    >
      {children}
    </button>
  );
}
export function Modal({ title, subtitle, close, children, wide = false }) {
  const ref = useRef();
  useEffect(() => {
    const previous = document.activeElement;
    ref.current.showModal();
    return () => previous?.focus();
  }, []);
  return (
    <dialog
      ref={ref}
      className={"modal " + (wide ? "wide" : "")}
      onCancel={(event) => {
        event.preventDefault();
        close();
      }}
      onClick={(event) => {
        if (event.target === ref.current) close();
      }}
    >
      <div className="modal-header">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        <IconButton title="Close dialog" onClick={close}>
          <X size={20} />
        </IconButton>
      </div>
      {children}
    </dialog>
  );
}

export function ResizeHandle({ side, value, change }) {
  const start = useRef(null);
  const min = side === "left" ? 220 : 240;
  const max = side === "left" ? 400 : 440;
  function resize(next) {
    change(
      Math.max(
        min,
        Math.min(
          max,
          window.innerWidth * (side === "left" ? 0.32 : 0.36),
          next,
        ),
      ),
    );
  }
  return (
    <div
      className={`resize-handle ${side}`}
      role="separator"
      tabIndex={0}
      aria-label={`Resize ${side === "left" ? "navigation" : "sources"} panel`}
      aria-orientation="vertical"
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={Math.round(value)}
      onPointerDown={(e) => {
        start.current = { x: e.clientX, value };
        e.currentTarget.setPointerCapture(e.pointerId);
      }}
      onPointerMove={(e) => {
        if (start.current)
          resize(
            start.current.value +
              (e.clientX - start.current.x) * (side === "left" ? 1 : -1),
          );
      }}
      onPointerUp={() => {
        start.current = null;
      }}
      onLostPointerCapture={() => {
        start.current = null;
      }}
      onKeyDown={(e) => {
        if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) {
          e.preventDefault();
          resize(
            e.key === "Home"
              ? min
              : e.key === "End"
                ? max
                : value +
                  (e.key === "ArrowRight" ? 10 : -10) *
                    (side === "left" ? 1 : -1),
          );
        }
      }}
    />
  );
}
