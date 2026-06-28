import { z, type ZodType } from "zod";

const errorEnvelopeSchema = z
  .object({
    error: z
      .object({
        code: z.string(),
        message: z.string(),
        request_id: z.string().optional(),
      })
      .optional(),
    detail: z.string().optional(),
  })
  .passthrough();

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId?: string;

  constructor(options: {
    status: number;
    code: string;
    message: string;
    requestId?: string;
  }) {
    super(options.message);
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code;
    this.requestId = options.requestId;
  }
}

type RequestOptions<T> = {
  schema: ZodType<T>;
  method?: "GET" | "POST" | "DELETE" | "PATCH" | "PUT";
  body?: unknown;
  headers?: HeadersInit;
  signal?: AbortSignal;
};

export async function request<T>(
  path: string,
  options: RequestOptions<T>,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, {
    method: options.method ?? "GET",
    headers,
    credentials: "include",
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  });
  const requestId =
    response.headers.get("X-Request-ID") ?? response.headers.get("x-request-id");
  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const parsed = errorEnvelopeSchema.safeParse(payload);
    const error = parsed.success ? parsed.data.error : undefined;
    const detail = parsed.success ? parsed.data.detail : undefined;
    throw new ApiError({
      status: response.status,
      code: error?.code ?? `HTTP_${response.status}`,
      message: error?.message ?? detail ?? "The request could not be completed.",
      requestId: error?.request_id ?? requestId ?? undefined,
    });
  }

  return options.schema.parse(payload);
}
