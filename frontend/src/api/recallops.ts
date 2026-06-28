import { z } from "zod";

import { request } from "./client";

export const evidenceStatusSchema = z.enum([
  "queued",
  "processing",
  "ready",
  "failed",
  "forgotten",
]);

export const evidenceItemSchema = z.object({
  data_id: z.string(),
  dataset: z.string(),
  name: z.string(),
  kind: z.string(),
  source_uri: z.string().nullable(),
  status: evidenceStatusSchema,
  content_hash: z.string(),
  source_date: z.string().nullable(),
  is_stale: z.boolean(),
  memory_layer: z.literal("permanent"),
});

export type EvidenceItem = z.infer<typeof evidenceItemSchema>;

const evidenceListSchema = z.object({
  items: z.array(evidenceItemSchema),
});

const demoResetSchema = z.object({
  incident_id: z.string(),
  observation_count: z.number(),
  candidate_count: z.number(),
  synthetic: z.literal(true),
});

const demoSeedSchema = z.object({
  dataset: z.string(),
  seeded: z.number(),
  reused: z.number(),
  failed: z.number(),
  ready: z.boolean(),
});

export const recallOpsApi = {
  listEvidence(signal?: AbortSignal) {
    return request("/api/evidence", {
      schema: evidenceListSchema,
      signal,
    });
  },
  resetDemo() {
    return request("/api/demo/reset", {
      method: "POST",
      schema: demoResetSchema,
    });
  },
  seedDemo(adminToken: string) {
    return request("/api/demo/seed", {
      method: "POST",
      headers: { "X-Demo-Admin-Token": adminToken },
      schema: demoSeedSchema,
    });
  },
};
