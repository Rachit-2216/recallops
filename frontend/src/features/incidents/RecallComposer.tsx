import { CornerDownLeft, Search } from "lucide-react";
import { useState } from "react";

import { PUBLIC_CASE_STUDY } from "../demo/publicCaseStudy";

export function RecallComposer({
  demo,
  disabled,
  onSubmit,
}: {
  demo: boolean;
  disabled?: boolean;
  onSubmit: (query: string) => void;
}) {
  const [query, setQuery] = useState(
    demo ? PUBLIC_CASE_STUDY.recallQuestion : "",
  );

  function submit() {
    const value = query.trim();
    if (value.length >= 3 && !disabled) onSubmit(value);
  }

  return (
    <section className="recall-composer" aria-labelledby="recall-title">
      <div className="recall-composer__heading">
        <Search size={16} aria-hidden="true" />
        <div>
          <span className="eyebrow">Scoped memory recall</span>
          <h2 id="recall-title">Ask incident memory</h2>
        </div>
      </div>
      <label className="sr-only" htmlFor="recall-question">
        Recall question
      </label>
      <textarea
        id="recall-question"
        onChange={(event) => setQuery(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
            event.preventDefault();
            submit();
          }
        }}
        rows={3}
        value={query}
      />
      <div className="recall-composer__footer">
        <span>Ctrl / ⌘ + Enter</span>
        <button
          className="primary-action"
          disabled={disabled || query.trim().length < 3}
          onClick={submit}
          type="button"
        >
          Recall evidence
          <CornerDownLeft size={15} aria-hidden="true" />
        </button>
      </div>
    </section>
  );
}
