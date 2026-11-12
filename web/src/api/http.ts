/**
 * web/src/api/http.ts —— 前端唯一 HTTP 出口（FRONTEND.md:7；M0-03-design.md §5/§6/§10）
 *
 * 只做六件事，S6 页面侧不得直接 fetch：
 *   1) cookie 会话：一律 credentials:"include"（会话态由服务端 Set-Cookie 决定，前端不存令牌）；
 *   2) Problem → ApiError 单一映射（ADR-005 §2.1/§2.2：分支键只用 code，title 原样透传不另编文案）；
 *   3) ETag：响应 ETag 入内存缓存，变更请求按需带 If-Match（412 由上层呈现新旧 revision）；
 *   4) Idempotency-Key：生成 + 契约长度校验（8..128），409 重试沿原 key，不重新生成；
 *   5) 202 轮询骨架：显式时钟 + 次数上限 + AbortSignal，释放由 useWorkspaceScope 负责；
 *   6) abort 与请求序列：晚到响应不得覆盖当前范围（FRONTEND.md:13）。
 *
 * 硬约束：
 *   - 不用系统当前时间推算会话过期（一律以服务端响应为准）；注入的 clock 只服务退避调度与证据时标；
 *   - 零 console.*（eslint no-console 已禁）：dev 断言进 assertions 水槽，由 S8 用例读取并断言为空；
 *   - 不内置 code 白名单：未知 code 走 default 分支，title/detail/request_id 全由服务端给；
 *   - 非 Problem 来源的失败 kind !== "problem"，此时 title 恒为空串，UI 只能用 COMMON.md 通用失败态。
 */
import type { InjectionKey } from "vue";
import type { components } from "@/api/types";

export type Problem = components["schemas"]["Problem"];
export type Issue = components["schemas"]["Issue"];

/* ------------------------------------------------------------------ 常量 */

/** ADR-005 §2.1：type 与 code 的一致性前缀（不一致时以 code 为准并记 dev 断言）。 */
export const PROBLEM_TYPE_PREFIX = "urn:campaignlab:problem:";
/** ADR-005 §2.3：JSON 正文上限 1 MiB（文件上传的 8/64 MiB 是另一对象，不得混用）。 */
export const JSON_BODY_LIMIT_BYTES = 1048576;
/** 活契约 components.parameters 对 Idempotency-Key 的 minLength/maxLength。 */
export const IDEMPOTENCY_KEY_MIN_LENGTH = 8;
export const IDEMPOTENCY_KEY_MAX_LENGTH = 128;
/** M0-03-design.md §5：429 指数退避首次 1s、上限 3 次。 */
export const RETRY_429_MAX = 3;
export const RETRY_429_BASE_MS = 1000;
/** 202 轮询默认档：1.5s x 20 = 30s（worker 心跳 15s，ADR-005 §2.3）；按作业可覆写。 */
export const POLL_INTERVAL_MS = 1500;
export const POLL_MAX_ATTEMPTS = 20;
/** dev 断言水槽上限：生产环境不得无界增长。 */
const ASSERTION_SINK_LIMIT = 100;
const DEFAULT_ACCEPT: readonly number[] = [200, 201, 202, 204];
const POLL_ACCEPT: readonly number[] = [200, 201, 202, 203, 204];

/* ------------------------------------------------------------------ 错误模型 */

/**
 * 失败类别。只有 "problem" 携带可渲染的服务端 title；其余五类是前端自身视角的传输/契约事实，
 * title 恒为空串（不另编文案，ADR-005 §2.2），S6 用 COMMON.md 的通用失败态 + request_id 呈现。
 */
export type ApiErrorKind = "problem" | "transport" | "aborted" | "payload" | "assertion" | "timeout";

export interface ApiError {
  readonly kind: ApiErrorKind;
  /** HTTP 状态；0 表示请求未发出或未拿到响应。 */
  readonly status: number;
  readonly code: string;
  readonly type: string;
  readonly title: string;
  readonly detail: string;
  readonly requestId: string;
  readonly issues: readonly Issue[];
  /** kind === "payload" 时给出实算字节数，供 413 分支的字段级提示。 */
  readonly payload?: { readonly limitBytes: number; readonly actualBytes: number } | undefined;
  /** kind === "transport" 时的底层原因（仅证据/调试，不面向用户）。 */
  readonly cause?: string | undefined;
}

export interface ApiOk<T> {
  readonly ok: true;
  readonly status: number;
  readonly data: T;
  readonly etag: string | null;
  readonly requestId: string;
  /** 304：data 为 null，调用方沿用自己上一次的数据（契约当前未声明 304，默认不发 If-None-Match）。 */
  readonly notModified: boolean;
}

export interface ApiFailure {
  readonly ok: false;
  readonly error: ApiError;
}

export type ApiResult<T> = ApiOk<T> | ApiFailure;

function errorOf(kind: ApiErrorKind, status: number, extra?: Partial<ApiError>): ApiError {
  return {
    kind,
    status,
    code: "",
    type: "",
    title: "",
    detail: "",
    requestId: "",
    issues: [],
    ...extra,
  };
}

function failure(error: ApiError): ApiFailure {
  return { ok: false, error };
}

function isProblemShape(value: unknown): value is Problem {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v["type"] === "string" &&
    typeof v["title"] === "string" &&
    typeof v["status"] === "number" &&
    typeof v["code"] === "string" &&
    typeof v["detail"] === "string" &&
    typeof v["request_id"] === "string" &&
    Array.isArray(v["issues"])
  );
}

/** issues[] 逐条校验：残缺条目丢弃而不是塞给表单（location 定位错字段比不定位更糟）。 */
function toIssues(raw: unknown): Issue[] {
  if (!Array.isArray(raw)) return [];
  const out: Issue[] = [];
  for (const item of raw) {
    if (typeof item !== "object" || item === null) continue;
    const v = item as Record<string, unknown>;
    const severity = v["severity"];
    if (
      typeof v["code"] !== "string" ||
      typeof v["location"] !== "string" ||
      typeof v["message"] !== "string" ||
      (severity !== "ERROR" && severity !== "WARNING" && severity !== "INFO")
    ) {
      continue;
    }
    out.push({ code: v["code"], location: v["location"], message: v["message"], severity });
  }
  return out;
}

/* ------------------------------------------------------------------ 时钟与工具 */

/**
 * 显式时钟：只用于退避调度与证据时标。
 * 领域不变量「不得用系统当前时间推算会话过期」——会话有效性一律由服务端响应决定。
 */
export interface HttpClock {
  now(): number;
}

export type HttpSleep = (ms: number) => Promise<void>;

export const systemClock: HttpClock = { now: () => Date.now() };

export const realSleep: HttpSleep = (ms: number): Promise<void> =>
  new Promise((resolve) => {
    setTimeout(resolve, ms);
  });

export type QueryInput = Record<string, string | number | boolean | null | undefined>;

export function jsonBodyBytes(body: unknown): number {
  return new TextEncoder().encode(JSON.stringify(body)).length;
}

/** 契约约束 8..128；额外排除控制字符与空白（Header 值不得折行）。 */
export function isValidIdempotencyKey(key: string): boolean {
  return (
    key.length >= IDEMPOTENCY_KEY_MIN_LENGTH &&
    key.length <= IDEMPOTENCY_KEY_MAX_LENGTH &&
    !/[\s\u0000-\u001f\u007f]/.test(key)
  );
}

/**
 * 生成幂等键：一次用户意图一个 key，409 IDEMPOTENCY_CONFLICT 重试必须沿原 key（M0-03-design.md §5）。
 * purpose 只作前缀便于证据检索，不参与业务判定。
 */
export function newIdempotencyKey(purpose: string): string {
  const safePurpose = purpose.replace(/[^\w.-]/g, "-").slice(0, 32);
  const random =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2);
  const key = safePurpose.length > 0 ? safePurpose + "-" + random : random;
  return key.slice(0, IDEMPOTENCY_KEY_MAX_LENGTH);
}

/* ------------------------------------------------------------------ 配置 */

export interface HttpClientConfig {
  baseUrl?: string | undefined;
  fetchImpl?: typeof fetch | undefined;
  clock?: HttpClock | undefined;
  sleep?: HttpSleep | undefined;
  maxJsonBodyBytes?: number | undefined;
  retry429Max?: number | undefined;
  retry429BaseMs?: number | undefined;
  pollIntervalMs?: number | undefined;
  pollMaxAttempts?: number | undefined;
}

interface ResolvedConfig {
  readonly baseUrl: string;
  readonly fetchImpl: typeof fetch | undefined;
  readonly clock: HttpClock;
  readonly sleep: HttpSleep;
  readonly maxJsonBodyBytes: number;
  readonly retry429Max: number;
  readonly retry429BaseMs: number;
  readonly pollIntervalMs: number;
  readonly pollMaxAttempts: number;
}

/**
 * baseUrl 只从 VITE_API_BASE_URL 注入，默认同源相对路径。
 * 不在源码里写死后端端口（NOTE-01 端口纪律 + M0-03-design.md G7 自证口径）。
 */
function envBaseUrl(): string {
  const raw: unknown = import.meta.env["VITE_API_BASE_URL"];
  return typeof raw === "string" && raw.length > 0 ? raw : "";
}

function resolveConfig(config: HttpClientConfig): ResolvedConfig {
  return {
    baseUrl: (config.baseUrl ?? envBaseUrl()).replace(/\/+$/, ""),
    fetchImpl: config.fetchImpl,
    clock: config.clock ?? systemClock,
    sleep: config.sleep ?? realSleep,
    maxJsonBodyBytes: config.maxJsonBodyBytes ?? JSON_BODY_LIMIT_BYTES,
    retry429Max: config.retry429Max ?? RETRY_429_MAX,
    retry429BaseMs: config.retry429BaseMs ?? RETRY_429_BASE_MS,
    pollIntervalMs: config.pollIntervalMs ?? POLL_INTERVAL_MS,
    pollMaxAttempts: config.pollMaxAttempts ?? POLL_MAX_ATTEMPTS,
  };
}

/* ------------------------------------------------------------------ 请求选项 */

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface HttpRequestOptions {
  readonly method: HttpMethod;
  /** 契约路径原文，如 "/workspaces"；不得自带 origin。 */
  readonly path: string;
  readonly query?: QueryInput | undefined;
  readonly body?: unknown | undefined;
  readonly headers?: Record<string, string> | undefined;
  /** 变更请求的乐观并发：ETag 原值（含引号）。 */
  readonly ifMatch?: string | undefined;
  readonly idempotencyKey?: string | undefined;
  /** 契约当前未声明 304；仅在服务端显式支持条件 GET 后由调用方开启。 */
  readonly ifNoneMatch?: string | undefined;
  /** 视为成功的状态码集合，默认 200/201/202/204。 */
  readonly accept?: readonly number[] | undefined;
  readonly signal?: AbortSignal | undefined;
  /** 契约要求 Idempotency-Key 的操作（如 createWorkspace）置 true：缺失即前端缺陷，不发请求。 */
  readonly requireIdempotencyKey?: boolean | undefined;
  /** 契约要求 If-Match 的操作置 true：缺失即前端缺陷（对应服务端 428），不发请求。 */
  readonly requireIfMatch?: boolean | undefined;
}

export interface PollOptions {
  readonly path: string;
  readonly query?: QueryInput | undefined;
  /** 由调用方判定「已落地」：例如 status === 200。 */
  readonly settled: (status: number) => boolean;
  readonly intervalMs?: number | undefined;
  readonly maxAttempts?: number | undefined;
  readonly signal?: AbortSignal | undefined;
  readonly onAttempt?: ((info: { readonly attempt: number; readonly status: number }) => void) | undefined;
}

export interface HttpClient {
  request<T>(options: HttpRequestOptions): Promise<ApiResult<T>>;
  poll<T>(options: PollOptions): Promise<ApiResult<T>>;
  /** 请求缓存键：method + path + 排序后的 query（ETag 缓存与请求序列共用同一口径）。 */
  keyOf(options: Pick<HttpRequestOptions, "method" | "path" | "query">): string;
  etagFor(key: string): string | null;
  rememberEtag(key: string, etag: string | null): void;
  devAssertions(): readonly string[];
  drainDevAssertions(): string[];
  readonly baseUrl: string;
}

/* ------------------------------------------------------------------ 请求序列闸门 */

export interface InflightRequest {
  readonly key: string;
  readonly token: number;
  readonly signal: AbortSignal;
  /** 同 key 有更新的请求发起后即 true：调用方必须丢弃本次结果（FRONTEND.md:13）。 */
  isStale(): boolean;
}

export interface RequestGate {
  begin(key: string): InflightRequest;
  isCurrent(key: string, token: number): boolean;
  /** 切工作区 / 登出 / 路由离开：中止全部在飞请求，token 全部转为 stale。 */
  cancelAll(): void;
  inflightCount(): number;
}

export function createRequestGate(): RequestGate {
  const seq = new Map<string, number>();
  const controllers = new Map<string, AbortController>();

  return {
    begin(key: string): InflightRequest {
      controllers.get(key)?.abort();
      const controller = new AbortController();
      controllers.set(key, controller);
      const token = (seq.get(key) ?? 0) + 1;
      seq.set(key, token);
      return {
        key,
        token,
        signal: controller.signal,
        isStale: () => seq.get(key) !== token,
      };
    },
    isCurrent(key: string, token: number): boolean {
      return seq.get(key) === token;
    },
    cancelAll(): void {
      // 中止 + 递增序列号：被取消的请求即使仍以 aborted 结果返回，也一律判为 stale 而丢弃，
      // 不得写回 store（否则切工作区/登出时会闪一条假的传输错误）。
      for (const [key, controller] of controllers) {
        controller.abort();
        seq.set(key, (seq.get(key) ?? 0) + 1);
      }
      controllers.clear();
    },
    inflightCount(): number {
      return controllers.size;
    },
  };
}

/* ------------------------------------------------------------------ 客户端 */

export function createHttpClient(config: HttpClientConfig = {}): HttpClient {
  const cfg = resolveConfig(config);
  const etags = new Map<string, string>();
  const assertions: string[] = [];

  function note(message: string): void {
    if (assertions.length < ASSERTION_SINK_LIMIT) assertions.push(message);
  }

  function searchOf(query: QueryInput | undefined): string {
    if (!query) return "";
    const usp = new URLSearchParams();
    for (const name of Object.keys(query).sort()) {
      const value = query[name];
      if (value === undefined || value === null) continue;
      usp.set(name, String(value));
    }
    const text = usp.toString();
    return text.length > 0 ? "?" + text : "";
  }

  function keyOf(options: Pick<HttpRequestOptions, "method" | "path" | "query">): string {
    return options.method + " " + options.path + searchOf(options.query);
  }

  function isAbort(reason: unknown, signal: AbortSignal | undefined): boolean {
    if (signal?.aborted === true) return true;
    return reason instanceof Error && reason.name === "AbortError";
  }

  function messageOf(reason: unknown): string {
    if (reason instanceof Error) return reason.name + ": " + reason.message;
    return String(reason);
  }

  async function readProblem(response: Response, text: string, requestId: string): Promise<ApiError> {
    if (text.length === 0) {
      note("非 2xx 且正文为空：" + response.status + " " + response.url);
      return errorOf("transport", response.status, { requestId });
    }
    let parsed: unknown;
    try {
      parsed = JSON.parse(text) as unknown;
    } catch (reason) {
      note("非 2xx 且正文非 JSON：" + response.status + " " + messageOf(reason));
      return errorOf("transport", response.status, { requestId, cause: messageOf(reason) });
    }
    if (!isProblemShape(parsed)) {
      note("非 2xx 但正文不符合 Problem（additionalProperties:false 七字段）：" + response.status);
      return errorOf("transport", response.status, { requestId });
    }
    const expectedType = PROBLEM_TYPE_PREFIX + parsed.code.toLowerCase();
    if (parsed.type !== expectedType) {
      // ADR-005 §2.1：不一致以 code 为准；dev 断言进水槽，S8 用例断言水槽为空。
      note("Problem.type 与 code 不一致：type=" + parsed.type + " 期望=" + expectedType + "（以 code 为准）");
    }
    return {
      kind: "problem",
      status: response.status,
      code: parsed.code,
      type: parsed.type,
      title: parsed.title,
      detail: parsed.detail,
      requestId: requestId.length > 0 ? requestId : parsed.request_id,
      issues: toIssues(parsed.issues),
    };
  }

  async function once<T>(options: HttpRequestOptions, url: string, key: string): Promise<ApiResult<T>> {
    const headers: Record<string, string> = { Accept: "application/json", ...(options.headers ?? {}) };
    if (options.ifMatch !== undefined) headers["If-Match"] = options.ifMatch;
    if (options.ifNoneMatch !== undefined) headers["If-None-Match"] = options.ifNoneMatch;
    if (options.idempotencyKey !== undefined) headers["Idempotency-Key"] = options.idempotencyKey;

    let payload: string | undefined;
    if (options.body !== undefined) {
      payload = JSON.stringify(options.body);
      headers["Content-Type"] = "application/json";
    }

    const impl = cfg.fetchImpl ?? (typeof globalThis.fetch === "function" ? globalThis.fetch : undefined);
    if (impl === undefined) {
      return failure(errorOf("transport", 0, { cause: "运行环境无 fetch 实现" }));
    }

    let response: Response;
    try {
      response = await impl(url, {
        method: options.method,
        headers,
        credentials: "include",
        // exactOptionalPropertyTypes：RequestInit.signal 不接受显式 undefined，故按需展开。
        ...(options.signal === undefined ? {} : { signal: options.signal }),
        ...(payload === undefined ? {} : { body: payload }),
      });
    } catch (reason) {
      if (isAbort(reason, options.signal)) return failure(errorOf("aborted", 0, { cause: messageOf(reason) }));
      return failure(errorOf("transport", 0, { cause: messageOf(reason) }));
    }

    const requestId = response.headers.get("X-Request-Id") ?? "";
    const etag = response.headers.get("ETag");
    if (etag !== null && etag.length > 0) etags.set(key, etag);

    if (response.status === 304) {
      if (options.ifNoneMatch === undefined) {
        note("收到 304 但请求未带 If-None-Match（契约未声明 304）：" + key);
        return failure(errorOf("transport", 304, { requestId }));
      }
      return { ok: true, status: 304, data: null as unknown as T, etag: etags.get(key) ?? null, requestId, notModified: true };
    }

    let text = "";
    try {
      text = await response.text();
    } catch (reason) {
      return failure(errorOf("transport", response.status, { requestId, cause: messageOf(reason) }));
    }

    const accept = options.accept ?? DEFAULT_ACCEPT;
    if (!accept.includes(response.status)) {
      return failure(await readProblem(response, text, requestId));
    }

    if (text.length === 0 || response.status === 204) {
      return { ok: true, status: response.status, data: null as unknown as T, etag: etag ?? null, requestId, notModified: false };
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(text) as unknown;
    } catch (reason) {
      note("2xx 正文非 JSON：" + response.status + " " + key + " " + messageOf(reason));
      return failure(errorOf("transport", response.status, { requestId, cause: messageOf(reason) }));
    }
    return { ok: true, status: response.status, data: parsed as T, etag: etag ?? null, requestId, notModified: false };
  }

  async function request<T>(options: HttpRequestOptions): Promise<ApiResult<T>> {
    // --- 客户端预检：三类「请求不发出去」的失败（前端缺陷或超限，均记 dev 断言） ---
    if (options.idempotencyKey !== undefined && !isValidIdempotencyKey(options.idempotencyKey)) {
      note("Idempotency-Key 非法（长度须 " + IDEMPOTENCY_KEY_MIN_LENGTH + ".." + IDEMPOTENCY_KEY_MAX_LENGTH + "）：" + options.method + " " + options.path);
      return failure(errorOf("assertion", 0, { detail: "Idempotency-Key 不满足契约长度约束，请求未发出" }));
    }
    if (options.requireIdempotencyKey === true && options.idempotencyKey === undefined) {
      note("缺 Idempotency-Key（契约必填）：" + options.method + " " + options.path);
      return failure(errorOf("assertion", 0, { detail: "契约要求 Idempotency-Key，请求未发出" }));
    }
    if (options.requireIfMatch === true && options.ifMatch === undefined) {
      // 服务端对应 428 PRECONDITION_REQUIRED；在客户端拦下即前端缺陷自检（M0-03-design.md §5）
      note("缺 If-Match（契约要求乐观并发）：" + options.method + " " + options.path);
      return failure(errorOf("assertion", 0, { detail: "契约要求 If-Match，请求未发出" }));
    }
    if (options.body !== undefined) {
      const actualBytes = jsonBodyBytes(options.body);
      if (actualBytes > cfg.maxJsonBodyBytes) {
        note("JSON 正文超 1 MiB 上限：" + actualBytes + " > " + cfg.maxJsonBodyBytes + "（" + options.method + " " + options.path + "）");
        return failure(
          errorOf("payload", 0, {
            detail: "JSON 正文超过上限，请求未发出",
            payload: { limitBytes: cfg.maxJsonBodyBytes, actualBytes },
          }),
        );
      }
    }

    const key = keyOf(options);
    const url = cfg.baseUrl + options.path + searchOf(options.query);

    for (let attempt = 0; ; attempt += 1) {
      const result = await once<T>(options, url, key);
      if (result.ok || result.error.status !== 429 || attempt >= cfg.retry429Max) return result;
      await cfg.sleep(cfg.retry429BaseMs * 2 ** attempt);
      if (options.signal?.aborted === true) return failure(errorOf("aborted", 0, { cause: "退避等待期间被取消" }));
    }
  }

  async function poll<T>(options: PollOptions): Promise<ApiResult<T>> {
    const intervalMs = options.intervalMs ?? cfg.pollIntervalMs;
    const maxAttempts = options.maxAttempts ?? cfg.pollMaxAttempts;
    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      const result = await request<T>({
        method: "GET",
        path: options.path,
        query: options.query,
        accept: POLL_ACCEPT,
        signal: options.signal,
      });
      if (!result.ok) return result;
      options.onAttempt?.({ attempt, status: result.status });
      if (options.settled(result.status)) return result;
      if (attempt === maxAttempts) break;
      await cfg.sleep(intervalMs);
      if (options.signal?.aborted === true) return failure(errorOf("aborted", 0, { cause: "轮询期间被取消" }));
    }
    return failure(errorOf("timeout", 0, { detail: "202 轮询在 " + maxAttempts + " 次内未落地" }));
  }

  return {
    request,
    poll,
    keyOf,
    etagFor: (key: string) => etags.get(key) ?? null,
    rememberEtag: (key: string, etag: string | null) => {
      if (etag === null) etags.delete(key);
      else etags.set(key, etag);
    },
    devAssertions: () => assertions.slice(),
    drainDevAssertions: () => assertions.splice(0, assertions.length),
    baseUrl: cfg.baseUrl,
  };
}

/** 组合根注入用的单例（main.ts 以 app.provide(httpKey, http) 接线）。 */
export const http: HttpClient = createHttpClient();
export const httpKey: InjectionKey<HttpClient> = Symbol("campaignlab.http");
