import { Plus } from "lucide-react";
import { useState } from "react";

export function ObservationComposer({
  disabled,
  onSubmit,
}: {
  disabled?: boolean;
  onSubmit: (content: string) => void;
}) {
  const [content, setContent] = useState("");
  return (
    <form
      className="observation-composer"
      onSubmit={(event) => {
        event.preventDefault();
        const value = content.trim();
        if (!value) return;
        onSubmit(value);
        setContent("");
      }}
    >
      <label htmlFor="observation-content">Add observation</label>
      <div>
        <input
          id="observation-content"
          onChange={(event) => setContent(event.target.value)}
          placeholder="Record a metric, deploy, or operator finding…"
          value={content}
        />
        <button
          aria-label="Add observation to session"
          disabled={disabled || !content.trim()}
          type="submit"
        >
          <Plus size={16} aria-hidden="true" />
        </button>
      </div>
      <small>Session-scoped until resolution is verified and promoted.</small>
    </form>
  );
}
