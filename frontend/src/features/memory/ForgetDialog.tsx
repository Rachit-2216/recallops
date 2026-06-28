import { AlertTriangle, Check, DatabaseZap, X } from "lucide-react";
import { useEffect, useState } from "react";

import type {
  EvidenceItem,
  ForgetResult,
} from "../../api/recallops";

type ForgetDialogProps = {
  item: EvidenceItem;
  onClose: () => void;
  onForget: (item: EvidenceItem) => Promise<ForgetResult>;
};

export function ForgetDialog({
  item,
  onClose,
  onForget,
}: ForgetDialogProps) {
  const [confirmation, setConfirmation] = useState("");
  const [phase, setPhase] = useState<
    "idle" | "deleting" | "success" | "error"
  >("idle");
  const [result, setResult] = useState<ForgetResult | null>(null);
  const [error, setError] = useState("");
  const expected = `FORGET ${item.name}`;

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape" && phase !== "deleting") {
        onClose();
      }
    }
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [onClose, phase]);

  async function submit() {
    if (confirmation !== expected || phase === "deleting") return;
    setPhase("deleting");
    setError("");
    try {
      const proof = await onForget(item);
      setResult(proof);
      setPhase("success");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Verification failed");
      setPhase("error");
    }
  }

  return (
    <div className="dialog-backdrop">
      <section
        aria-labelledby="forget-title"
        aria-modal="true"
        className="forget-dialog"
        role="dialog"
      >
        <button
          aria-label="Close forget dialog"
          className="dialog-close"
          disabled={phase === "deleting"}
          onClick={onClose}
          type="button"
        >
          <X size={17} aria-hidden="true" />
        </button>
        <div className="danger-symbol">
          <DatabaseZap size={22} aria-hidden="true" />
        </div>
        <span className="eyebrow">Destructive memory lifecycle action</span>
        <h2 id="forget-title">Forget permanent evidence</h2>
        <p>
          This removes the graph and vector representations for this item, then
          runs a scoped recall to verify that the reference is gone.
        </p>
        <dl className="forget-target">
          <div>
            <dt>Document</dt>
            <dd>{item.name}</dd>
          </div>
          <div>
            <dt>Data ID</dt>
            <dd>{item.data_id}</dd>
          </div>
        </dl>

        <div className="forget-progress" aria-live="polite">
          <span
            className={
              phase === "deleting"
                ? "progress-step progress-step--active"
                : phase === "success"
                  ? "progress-step progress-step--done"
                  : "progress-step"
            }
          >
            {phase === "success" ? (
              <Check size={13} aria-hidden="true" />
            ) : (
              "1"
            )}
            Deleting graph + vector data
          </span>
          <span
            className={
              phase === "success"
                ? "progress-step progress-step--done"
                : "progress-step"
            }
          >
            {phase === "success" ? (
              <Check size={13} aria-hidden="true" />
            ) : (
              "2"
            )}
            Verifying scoped recall
          </span>
        </div>

        {result ? (
          <div className="forget-proof">
            <strong>
              Before ·{" "}
              {result.before_reference_found
                ? "reference found"
                : "no reference"}
            </strong>
            <strong>
              After ·{" "}
              {result.after_reference_found
                ? "reference still found"
                : "no reference"}
            </strong>
          </div>
        ) : null}
        {error ? (
          <p className="inline-error" role="alert">
            <AlertTriangle size={14} aria-hidden="true" /> {error}
          </p>
        ) : null}

        {phase !== "success" ? (
          <>
            <label htmlFor="forget-confirmation">
              Confirmation phrase
              <code>{expected}</code>
            </label>
            <input
              autoFocus
              autoComplete="off"
              id="forget-confirmation"
              onChange={(event) => setConfirmation(event.target.value)}
              value={confirmation}
            />
            <button
              className="danger-action"
              disabled={confirmation !== expected || phase === "deleting"}
              onClick={submit}
              type="button"
            >
              Forget memory
            </button>
          </>
        ) : (
          <button className="secondary-action" onClick={onClose} type="button">
            Close verified result
          </button>
        )}
      </section>
    </div>
  );
}
