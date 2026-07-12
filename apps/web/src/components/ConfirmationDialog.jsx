import { useEffect, useRef } from "react";

const ConfirmationDialog = ({
  open,
  title,
  description,
  affectedItems = [],
  safeItems = [],
  confirmLabel,
  cancelLabel = "Batal",
  isLoading = false,
  onConfirm,
  onCancel,
}) => {
  const cancelButtonRef = useRef(null);
  const dialogRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;

    const previousFocus = document.activeElement;
    cancelButtonRef.current?.focus();

    const handleKeyDown = (event) => {
      if (event.key === "Escape" && !isLoading) onCancel();
      if (event.key === "Tab") {
        const focusable = Array.from(dialogRef.current?.querySelectorAll("button:not(:disabled)") || []);
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      previousFocus?.focus?.();
    };
  }, [isLoading, onCancel, open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4" role="presentation">
      <div
        ref={dialogRef}
        className="dialog-panel w-full max-w-lg p-6"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirmation-dialog-title"
        aria-describedby="confirmation-dialog-description"
      >
        <h2 id="confirmation-dialog-title" className="text-xl font-bold text-main">{title}</h2>
        {description && <p id="confirmation-dialog-description" className="mt-3 text-sm leading-6 text-muted">{description}</p>}

        {affectedItems.length > 0 && (
          <div className="alert-panel alert-panel--danger mt-4 p-4">
            <p className="text-sm font-bold text-main">Yang akan terjadi:</p>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted">
              {affectedItems.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </div>
        )}

        {safeItems.length > 0 && (
          <div className="alert-panel alert-panel--success mt-3 p-4">
            <p className="text-sm font-bold text-main">Yang tetap aman:</p>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted">
              {safeItems.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </div>
        )}

        <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <button ref={cancelButtonRef} type="button" onClick={onCancel} disabled={isLoading} className="secondary-button rounded-xl px-4 py-2 font-bold">{cancelLabel}</button>
          <button type="button" onClick={onConfirm} disabled={isLoading} className="destructive-button rounded-xl px-4 py-2 font-bold">{isLoading ? "Memproses..." : confirmLabel}</button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmationDialog;
