import { useEffect, type ReactNode } from "react";

export function Modal({
  title,
  onClose,
  closable = true,
  children,
}: {
  title: string;
  onClose: () => void;
  /** false — окно не закрыть, пока не сделан выбор. */
  closable?: boolean;
  children: ReactNode;
}) {
  useEffect(() => {
    if (!closable) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, closable]);

  return (
    <div className="modal-backdrop" onClick={closable ? onClose : undefined}>
      <div className="modal" role="dialog" aria-label={title} onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>{title}</h2>
          {closable && (
            <button className="link" onClick={onClose} aria-label="Закрыть">
              ✕
            </button>
          )}
        </div>
        {children}
      </div>
    </div>
  );
}
