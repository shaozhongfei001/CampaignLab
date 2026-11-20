/**
 * web/tests/e2e/activity/stubActivityApi.ts —— UI-02 的浏览器路由合成夹具
 *
 * 定位与边界（同 fixtures/stubApi.ts 的口径）：
 *   这些用例证明的是**前端层**的交互与呈现基线，不构成端到端联调结论；
 *   AC-001 的真 E2E 必须打真实后端，禁用 page.route 合成夹具（FU-31）。
 * 内容红线：夹具是合成数据 ⇒ 页面必须给出可见标注（ActivityListPage 的 data-part="source-class" 芯片）。
 *
 * 形状一律对齐 contracts/openapi.json 的 components.schemas（Activity/ActivityPage/Problem/Session/Health/Workspace），
 * additionalProperties:false 的字段一个不多一个不少。
 *
 * 与 fixtures/stubApi.ts 的差别（本文件为 UI-02 专用，不改既有夹具以免影响 UI-01 已入库证据）：
 *   1. 记录器除 method/pathname/search 外，还记 Idempotency-Key / If-Match / Content-Type / 请求正文原文，
 *      使「409 沿原幂等键重试」「空字段不出现在正文里」可被**请求形状**级断言，而不是靠页面文案间接推断；
 *   2. 返回**可变态控制器**（setListProblem / setListDelay / …），让同一用例内先失败后恢复、
 *      先骨架后就数据成为可能，避免为每个分支各写一份夹具；
 *   3. 详情查找池含 CREATED_ACTIVITY，故「创建成功进入详情」不会因为新建行不在列表里而误报 404。
 */
import type { Page } from "@playwright/test";

export const SYNTHETIC_SESSION = {
  actor_id: "op-synthetic",
  actor_name: "本机操作员（合成）",
  allowed_roles: ["OPERATOR"],
};

export const SYNTHETIC_HEALTH = {
  status: "READY",
  app_version: "0.0.0",
  contract_version: "1.0.1",
  worker: "READY",
  schema_revision: "r1",
};

export type StubSourceClass = "SYNTHETIC" | "AUTHORIZED_DEIDENTIFIED";

/**
 * 工作区集合的合成回包（形状取 contracts/openapi.json 的 Workspace / WorkspacePage）。
 * source_class 可换值：用于证明页头芯片跟随服务端取值而非写死（正负对照）。
 */
export function workspacePageOf(sourceClass: StubSourceClass) {
  return {
    items: [
      {
        id: "ws-1",
        revision: 1,
        created_at: "2026-11-11T09:00:00+08:00",
        name: "合成工作区甲",
        source_class: sourceClass,
        authorization_note: sourceClass === "SYNTHETIC" ? null : "DR-2026-11",
      },
    ],
    next_cursor: null,
  };
}

export const SYNTHETIC_WORKSPACE_PAGE = workspacePageOf("SYNTHETIC");

export interface StubActivity {
  readonly id: string;
  readonly revision: number;
  readonly created_at: string;
  readonly name: string;
  readonly bank_id: string | null;
  readonly external_activity_id: string | null;
  readonly description: string;
  readonly status: "OPEN" | "ARCHIVED";
  readonly current_rule_id: string | null;
  readonly bindings: readonly unknown[];
  readonly rule_ids: readonly string[];
  readonly receipt_ids: readonly string[];
}

/** 默认四行：两行 OPEN、两行 ARCHIVED（UI-02:32「已归档活动可检索和查看」），其中一行三字段全缺。 */
export const DEFAULT_ACTIVITIES: readonly StubActivity[] = [
  {
    id: "act-001",
    revision: 3,
    created_at: "2026-11-01T09:00:00+08:00",
    name: "满额赠券 A 方案",
    bank_id: "BANK-A",
    external_activity_id: "EXT-A-101",
    description: "合成数据，仅用于前端层断言",
    status: "OPEN",
    current_rule_id: "rule-a-003",
    bindings: [
      {
        strategy_id: "S-101",
        source_version: "v1",
        valid_from: "2026-11-01",
        valid_until: "2026-12-01",
        evidence_id: "EV-001",
      },
    ],
    rule_ids: ["rule-a-001", "rule-a-002", "rule-a-003"],
    receipt_ids: ["REL-101"],
  },
  {
    id: "act-002",
    revision: 1,
    created_at: "2026-11-02T09:00:00+08:00",
    name: "远程回拨 B 方案",
    bank_id: "BANK-B",
    external_activity_id: "EXT-B-202",
    description: "",
    status: "OPEN",
    current_rule_id: null,
    bindings: [],
    rule_ids: [],
    receipt_ids: [],
  },
  {
    id: "act-003",
    revision: 2,
    created_at: "2026-11-03T09:00:00+08:00",
    name: "缺值对照活动",
    bank_id: null,
    external_activity_id: null,
    description: "",
    status: "ARCHIVED",
    current_rule_id: null,
    bindings: [],
    rule_ids: [],
    receipt_ids: [],
  },
  {
    id: "act-004",
    revision: 5,
    created_at: "2026-11-04T09:00:00+08:00",
    name: "已归档对照活动",
    bank_id: "BANK-A",
    external_activity_id: "EXT-A-404",
    description: "归档后仍可检索",
    status: "ARCHIVED",
    current_rule_id: "rule-a-404",
    bindings: [],
    rule_ids: ["rule-a-404"],
    receipt_ids: [],
  },
];

/** 第二页（cursor 翻页用）：一行 ARCHIVED，验证「加载更多」是追加而非替换。 */
export const MORE_ACTIVITIES: readonly StubActivity[] = [
  {
    id: "act-005",
    revision: 1,
    created_at: "2026-11-05T09:00:00+08:00",
    name: "第二页对照活动",
    bank_id: null,
    external_activity_id: "EXT-A-505",
    description: "",
    status: "ARCHIVED",
    current_rule_id: null,
    bindings: [],
    rule_ids: [],
    receipt_ids: [],
  },
];

export const CREATED_ACTIVITY: StubActivity = {
  id: "act-900",
  revision: 1,
  created_at: "2026-11-20T09:00:00+08:00",
  name: "新建的合成活动",
  bank_id: "BANK-A",
  external_activity_id: "EXT-A-900",
  description: "由 UI-02 新建流程产生",
  status: "OPEN",
  current_rule_id: null,
  bindings: [],
  rule_ids: [],
  receipt_ids: [],
};

export interface StubProblem {
  readonly status: number;
  readonly code: string;
  readonly title: string;
  readonly detail: string;
  readonly request_id: string;
}

export const PROBLEM_500: StubProblem = {
  status: 500,
  code: "INTERNAL_ERROR",
  title: "服务内部错误（合成）",
  detail: "合成夹具：列表读取失败，用于验证失败态呈现与 request_id 可见。",
  request_id: "req-synthetic-500",
};

export const PROBLEM_412: StubProblem = {
  status: 412,
  code: "REVISION_CONFLICT",
  title: "修订号冲突（合成）",
  detail: "合成夹具：本地输入保留，显示新旧版本与重新获取入口。",
  request_id: "req-synthetic-412",
};

export const PROBLEM_409: StubProblem = {
  status: 409,
  code: "IDEMPOTENCY_CONFLICT",
  title: "同一银行行内活动编号已存在（合成）",
  detail: "合成夹具：既有记录为 act-001，页面应按行内编号定位。",
  request_id: "req-synthetic-409",
};

/**
 * Problem 正文：七字段一个不能少（contracts/openapi.json components.schemas.Problem
 * required = type/title/status/code/detail/request_id/issues，additionalProperties:false）。
 * 少一个字段 http.ts 的 isProblemShape() 就会判为 transport 错误，页面上看不到 code / HTTP 摘要
 * —— 这是本夹具首版真实踩过的坑，故在此留痕。
 */
function problemBody(problem: StubProblem) {
  return {
    type: "urn:campaignlab:problem:" + problem.code.toLowerCase(),
    status: problem.status,
    code: problem.code,
    title: problem.title,
    detail: problem.detail,
    request_id: problem.request_id,
    issues: [],
  };
}

export interface ActivityStubOptions {
  readonly workspaceId?: string;
  readonly activities?: readonly StubActivity[];
  readonly nextCursor?: string | null;
  readonly listProblem?: StubProblem | null;
  readonly createProblem?: StubProblem | null;
  readonly detailProblem?: StubProblem | null;
  /** 列表响应延迟（毫秒）：用于取证首载骨架与「上一结果」保留态。 */
  readonly listDelayMs?: number;
  /** 工作区数据用途（默认 SYNTHETIC）：换值可证明页头芯片不是写死的。 */
  readonly workspaceSourceClass?: StubSourceClass;
}

/** 记录到的请求形状（判据取解析值，不比对渲染串）。 */
export interface RecordedRequest {
  readonly method: string;
  readonly pathname: string;
  readonly search: string;
  readonly idempotencyKey: string | null;
  readonly ifMatch: string | null;
  readonly contentType: string | null;
  readonly bodyText: string | null;
}

/** 可变态控制器：同一用例内切换后端行为，避免为每个分支各写一份夹具。 */
export interface ActivityStub {
  readonly recorded: RecordedRequest[];
  readonly collectionPath: string;
  setListProblem(problem: StubProblem | null): void;
  setCreateProblem(problem: StubProblem | null): void;
  setDetailProblem(problem: StubProblem | null): void;
  setActivities(items: readonly StubActivity[]): void;
  setNextCursor(cursor: string | null): void;
  setListDelay(ms: number): void;
  /** 命中集合路径的请求（默认 GET）。 */
  listRequests(method?: string): RecordedRequest[];
  /** 命中活动单项路径的请求（默认 GET）。 */
  detailRequests(method?: string): RecordedRequest[];
  /** 解析某条请求的查询参数（禁裸串比对）。 */
  paramsOf(request: RecordedRequest): URLSearchParams;
}

export async function stubActivityApi(page: Page, options: ActivityStubOptions = {}): Promise<ActivityStub> {
  const workspaceId = options.workspaceId ?? "ws-1";
  const collection = "/workspaces/" + workspaceId + "/activities";

  let activities: readonly StubActivity[] = options.activities ?? DEFAULT_ACTIVITIES;
  let nextCursor: string | null = options.nextCursor ?? null;
  let listProblem: StubProblem | null = options.listProblem ?? null;
  let createProblem: StubProblem | null = options.createProblem ?? null;
  let detailProblem: StubProblem | null = options.detailProblem ?? null;
  let listDelayMs = options.listDelayMs ?? 0;
  const workspacePage = workspacePageOf(options.workspaceSourceClass ?? "SYNTHETIC");
  const recorded: RecordedRequest[] = [];

  const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();
    const pathname = url.pathname;
    const headers = route.request().headers();
    recorded.push({
      method,
      pathname,
      search: url.search,
      idempotencyKey: headers["idempotency-key"] ?? null,
      ifMatch: headers["if-match"] ?? null,
      contentType: headers["content-type"] ?? null,
      bodyText: route.request().postData() ?? null,
    });

    const sendJson = (body: unknown, status = 200) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    const sendProblem = (problem: StubProblem) =>
      route.fulfill({
        status: problem.status,
        contentType: "application/problem+json",
        headers: { "X-Request-Id": problem.request_id },
        body: JSON.stringify(problemBody(problem)),
      });

    if (pathname === "/session/exchange" && method === "POST") return sendJson(SYNTHETIC_SESSION);
    if (pathname === "/session" && method === "GET") return sendJson(SYNTHETIC_SESSION);
    if (pathname === "/health") return sendJson(SYNTHETIC_HEALTH);
    if (pathname === "/workspaces" && method === "GET") return sendJson(workspacePage);

    if (pathname === collection && method === "GET") {
      if (listDelayMs > 0) await sleep(listDelayMs);
      if (listProblem !== null) return sendProblem(listProblem);
      // 游标翻页：带 cursor 的请求返回第二页且不再给游标（验证「加载更多」是追加）。
      if (url.searchParams.get("cursor") !== null) {
        return sendJson({ items: MORE_ACTIVITIES, next_cursor: null });
      }
      // 按契约 status / q 过滤：让「筛选」与「已归档可检索」可被真实断言，而不是恒返回全量。
      const status = url.searchParams.get("status");
      const q = url.searchParams.get("q");
      const filtered = activities.filter((item) => {
        if (status !== null && status.length > 0 && item.status !== status) return false;
        if (q !== null && q.length > 0) {
          const haystack = [item.name, item.id, item.external_activity_id ?? ""].join(" ");
          if (!haystack.includes(q)) return false;
        }
        return true;
      });
      return sendJson({ items: filtered, next_cursor: nextCursor });
    }

    if (pathname === collection && method === "POST") {
      if (createProblem !== null) return sendProblem(createProblem);
      return sendJson(CREATED_ACTIVITY, 201);
    }

    if (pathname.startsWith(collection + "/") && method === "GET") {
      if (detailProblem !== null) return sendProblem(detailProblem);
      const id = decodeURIComponent(pathname.slice(collection.length + 1));
      // 查找池含新建行：UI-02「创建成功进入详情」在合成后端下同样可走通。
      const hit = activities.find((item) => item.id === id) ?? (id === CREATED_ACTIVITY.id ? CREATED_ACTIVITY : null);
      if (hit === null) {
        return sendProblem({
          status: 404,
          code: "RESOURCE_NOT_FOUND",
          title: "活动不存在（合成）",
          detail: "夹具里没有 " + id,
          request_id: "req-synthetic-404",
        });
      }
      return sendJson(hit);
    }

    return route.fallback();
  });

  const matchCollection = (request: RecordedRequest, expected: string): boolean =>
    request.pathname === collection && request.method === expected;
  const matchDetail = (request: RecordedRequest, expected: string): boolean =>
    request.pathname.startsWith(collection + "/") && request.method === expected;

  return {
    recorded,
    collectionPath: collection,
    setListProblem(problem) {
      listProblem = problem;
    },
    setCreateProblem(problem) {
      createProblem = problem;
    },
    setDetailProblem(problem) {
      detailProblem = problem;
    },
    setActivities(items) {
      activities = items;
    },
    setNextCursor(cursor) {
      nextCursor = cursor;
    },
    setListDelay(ms) {
      listDelayMs = ms;
    },
    listRequests(method = "GET") {
      return recorded.filter((request) => matchCollection(request, method));
    },
    detailRequests(method = "GET") {
      return recorded.filter((request) => matchDetail(request, method));
    },
    paramsOf(request) {
      return new URLSearchParams(request.search);
    },
  };
}