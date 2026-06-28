import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import type { EvidenceItem } from "../../api/recallops";
import { ForgetDialog } from "./ForgetDialog";

const item: EvidenceItem = {
  data_id: "8bb6ef4e-2320-5d12-9d19-63130ba810fa",
  dataset: "recallops_evidence_v1",
  name: "stale-cache-reset-rule.md",
  kind: "runbook",
  source_uri: null,
  status: "ready",
  content_hash: "sha256:stale",
  source_date: "2025-01-10T00:00:00Z",
  is_stale: true,
  memory_layer: "permanent",
};

it("requires exact confirmation and shows before/after verification", async () => {
  const onForget = vi.fn().mockResolvedValue({
    data_id: item.data_id,
    status: "forgotten" as const,
    before_reference_found: true,
    after_reference_found: false,
  });
  render(<ForgetDialog item={item} onClose={() => undefined} onForget={onForget} />);

  expect(screen.getByText(item.name)).toBeVisible();
  expect(screen.getByText(item.data_id)).toBeVisible();
  expect(screen.getByText(/graph and vector/i)).toBeVisible();
  const confirm = screen.getByLabelText(/confirmation phrase/i);
  const submit = screen.getByRole("button", { name: /forget memory/i });
  expect(submit).toBeDisabled();

  fireEvent.change(confirm, { target: { value: `FORGET ${item.name}` } });
  fireEvent.click(submit);

  await waitFor(() => expect(onForget).toHaveBeenCalledTimes(1));
  expect(await screen.findByText(/before.*reference found/i)).toBeVisible();
  expect(screen.getByText(/after.*no reference/i)).toBeVisible();
  expect(screen.getByText(/deleting/i)).toBeVisible();
  expect(screen.getByText(/verifying/i)).toBeVisible();
});

it("stays open and reports a verification failure", async () => {
  const onForget = vi.fn().mockRejectedValue(new Error("Verification failed"));
  render(<ForgetDialog item={item} onClose={() => undefined} onForget={onForget} />);

  fireEvent.change(screen.getByLabelText(/confirmation phrase/i), {
    target: { value: `FORGET ${item.name}` },
  });
  fireEvent.click(screen.getByRole("button", { name: /forget memory/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Verification failed",
  );
  expect(screen.getByRole("dialog")).toBeVisible();
});
