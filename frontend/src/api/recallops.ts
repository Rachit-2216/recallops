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

export const observationSchema = z.object({
  id: z.string(),
  incident_id: z.string(),
  timestamp: z.string(),
  source: z.string(),
  content: z.string(),
  memory_status: z.enum(["pending", "session_stored"]),
  memory_layer: z.literal("session"),
  retry_count: z.number(),
});

const incidentSchema = z.object({
  id: z.string(),
  title: z.string(),
  severity: z.string(),
  service: z.string(),
  status: z.string(),
  session_id: z.string(),
  started_at: z.string(),
  resolved_at: z.string().nullable(),
});

export const recallReferenceSchema = z.object({
  data_id: z.string(),
  chunk_id: z.string(),
  document_name: z.string(),
  snippet: z.string(),
});

export const recallResultSchema = z.object({
  answer: z.string().nullable(),
  verification: z.enum(["referenced", "unverified"]),
  source: z.string().optional(),
  search_type: z.string().optional(),
  references: z.array(recallReferenceSchema).optional().default([]),
  trace_id: z.string().optional(),
  why_recalled: z.array(z.string()).optional().default([]),
  no_result: z.boolean(),
  partial_memory: z.boolean(),
});

const incidentDetailSchema = z.object({
  incident: incidentSchema,
  observations: z.array(observationSchema),
  recalls: z.array(
    z.object({
      trace_id: z.string(),
      answer: z.string().nullable(),
      verification: z.string(),
    }),
  ),
  memory_candidates: z.array(
    z.object({
      id: z.string(),
      content: z.string(),
      state: z.string(),
      data_id: z.string().nullable(),
    }),
  ),
  resolution: z
    .object({
      root_cause: z.string(),
      mitigation: z.string(),
      verification: z.string(),
      promotion_state: z.string(),
      confirmed_at: z.string().nullable().optional(),
      trace_ids: z.array(z.string()).optional(),
    })
    .nullable(),
  budget: z.object({
    estimated_remaining: z.number(),
    protected_reserve: z.number(),
  }),
});

export type IncidentDetail = z.infer<typeof incidentDetailSchema>;
export type Observation = z.infer<typeof observationSchema>;
export type RecallResult = z.infer<typeof recallResultSchema>;

export type ResolutionRequest = {
  root_cause: string;
  mitigation: string;
  verification: string;
  trace_ids: string[];
  confirmed_by_human: boolean;
};

const resolutionResponseSchema = z.object({
  incident_id: z.string(),
  incident_status: z.string(),
  promotion_state: z.enum(["promotion_pending", "promotion_failed", "promoted"]),
  root_cause: z.string(),
  mitigation: z.string(),
  verification: z.string(),
  confirmed_at: z.string().nullable(),
  trace_ids: z.array(z.string()),
});

export type ResolutionResponse = z.infer<typeof resolutionResponseSchema>;

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

const forgetResultSchema = z.object({
  data_id: z.string(),
  status: z.literal("forgotten"),
  before_reference_found: z.boolean(),
  after_reference_found: z.boolean(),
});

export type ForgetResult = z.infer<typeof forgetResultSchema>;

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
  getIncident(incidentId: string, signal?: AbortSignal) {
    return request(`/api/incidents/${incidentId}`, {
      schema: incidentDetailSchema,
      signal,
    });
  },
  observeIncident(
    incidentId: string,
    content: string,
    observationId: string,
  ) {
    return request(`/api/incidents/${incidentId}/observe`, {
      method: "POST",
      body: { content, observation_id: observationId },
      schema: observationSchema,
    });
  },
  async recallIncident(
    incidentId: string,
    query: string,
    signal?: AbortSignal,
  ): Promise<RecallResult> {
    const result = await request(`/api/incidents/${incidentId}/recall`, {
      method: "POST",
      body: { query, include_trace: true },
      schema: recallResultSchema,
      signal,
    });
    return {
      ...result,
      references: result.references ?? [],
      why_recalled: result.why_recalled ?? [],
    };
  },
  forgetEvidence(
    item: EvidenceItem,
    verificationQuery = `"${item.name}"`,
  ) {
    return request(`/api/evidence/${item.data_id}`, {
      method: "DELETE",
      body: {
        confirmation: `FORGET ${item.name}`,
        verification_query: verificationQuery,
      },
      schema: forgetResultSchema,
    });
  },
  resolveIncident(incidentId: string, body: ResolutionRequest) {
    return request(`/api/incidents/${incidentId}/resolve`, {
      method: "POST",
      body,
      schema: resolutionResponseSchema,
    });
  },
  createIncident(body: {
    id: string;
    title: string;
    severity: string;
    service: string;
  }) {
    return request("/api/incidents", {
      method: "POST",
      body,
      schema: incidentSchema,
    });
  },
};
