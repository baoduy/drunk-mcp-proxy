import { useState } from "react";

const colors = {
  client: { bg: "#1e3a5f", border: "#3b82f6", text: "#bfdbfe" },
  entry: { bg: "#1a1a2e", border: "#6366f1", text: "#e0e7ff" },
  middleware: { bg: "#1f2937", border: "#8b5cf6", text: "#ddd6fe" },
  mcp: { bg: "#0f2e1a", border: "#22c55e", text: "#bbf7d0" },
  llm: { bg: "#2e1a0f", border: "#f97316", text: "#fed7aa" },
  auth: { bg: "#2d1b69", border: "#a78bfa", text: "#ede9fe" },
  backend: { bg: "#1c1c1c", border: "#6b7280", text: "#d1d5db" },
  cross: { bg: "#1e293b", border: "#94a3b8", text: "#cbd5e1" },
};

const Box = ({ x, y, w, h, color, title, subtitle, items = [], small = false }) => (
  <g>
    <rect
      x={x} y={y} width={w} height={h} rx="8"
      fill={color.bg}
      stroke={color.border}
      strokeWidth="1.5"
    />
    <text x={x + w / 2} y={y + (small ? 16 : 20)} textAnchor="middle"
      fill={color.text} fontSize={small ? 11 : 13} fontWeight="600" fontFamily="monospace">
      {title}
    </text>
    {subtitle && (
      <text x={x + w / 2} y={y + 34} textAnchor="middle"
        fill={color.border} fontSize={9} fontFamily="monospace" opacity="0.85">
        {subtitle}
      </text>
    )}
    {items.map((item, i) => (
      <text key={i} x={x + 10} y={y + (subtitle ? 50 : 40) + i * 16}
        fill={color.text} fontSize={9.5} fontFamily="monospace" opacity="0.9">
        {item}
      </text>
    ))}
  </g>
);

const Arrow = ({ x1, y1, x2, y2, label, color = "#6b7280", dashed = false }) => {
  const dx = x2 - x1, dy = y2 - y1;
  const len = Math.sqrt(dx * dx + dy * dy);
  const nx = dx / len, ny = dy / len;
  const ax = x2 - nx * 10, ay = y2 - ny * 10;
  const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
  return (
    <g>
      <line x1={x1} y1={y1} x2={ax} y2={ay}
        stroke={color} strokeWidth="1.5"
        strokeDasharray={dashed ? "5,3" : "none"}
        markerEnd={`url(#arrow-${color.replace("#", "")})`}
      />
      {label && (
        <text x={mx} y={my - 5} textAnchor="middle" fill={color}
          fontSize="8.5" fontFamily="monospace" opacity="0.85">
          {label}
        </text>
      )}
    </g>
  );
};

const GroupBox = ({ x, y, w, h, label, color }) => (
  <g>
    <rect x={x} y={y} width={w} height={h} rx="12"
      fill="none" stroke={color} strokeWidth="1" strokeDasharray="6,3" opacity="0.5" />
    <text x={x + 10} y={y + 13} fill={color} fontSize="10" fontFamily="monospace" opacity="0.7" fontStyle="italic">
      {label}
    </text>
  </g>
);

export default function ArchDiagram() {
  const [hover, setHover] = useState(null);
  const W = 1100, H = 780;

  return (
    <div style={{ background: "#0d1117", minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", padding: "24px" }}>
      <div style={{ color: "#e2e8f0", fontFamily: "monospace", fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
        drunk-mcp-proxy — Architecture
      </div>
      <div style={{ color: "#64748b", fontFamily: "monospace", fontSize: 11, marginBottom: 20 }}>
        Unified MCP &amp; LLM Gateway
      </div>

      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ maxWidth: "100%", borderRadius: 12 }}>
        <defs>
          {["#3b82f6", "#22c55e", "#f97316", "#6b7280", "#a78bfa", "#6366f1"].map(c => (
            <marker key={c} id={`arrow-${c.replace("#", "")}`} markerWidth="8" markerHeight="8"
              refX="6" refY="3" orient="auto">
              <path d="M0,0 L0,6 L8,3 z" fill={c} />
            </marker>
          ))}
        </defs>

        {/* Background */}
        <rect width={W} height={H} fill="#0d1117" rx="12" />

        {/* ── CLIENTS column ── */}
        <GroupBox x={10} y={20} w={160} h={420} label="Clients" color="#3b82f6" />

        <Box x={20} y={40} w={140} h={60} color={colors.client}
          title="MCP Client" subtitle="Claude / Cursor / IDE" small />
        <Box x={20} y={120} w={140} h={60} color={colors.client}
          title="LLM API Client" subtitle="OpenAI / Anthropic SDK" small />
        <Box x={20} y={200} w={140} h={60} color={colors.client}
          title="drunk_ai_client" subtitle="stdio bridge" small />
        <Box x={20} y={280} w={140} h={60} color={colors.client}
          title="Browser / Curl" subtitle="REST / Swagger UI" small />
        <Box x={20} y={360} w={140} h={60} color={colors.client}
          title="WebSocket Client" subtitle="Realtime Responses API" small />

        {/* Arrows from clients → entry */}
        <Arrow x1={160} y1={70} x2={215} y2={170} color="#3b82f6" label="/mcp" />
        <Arrow x1={160} y1={150} x2={215} y2={200} color="#f97316" label="/api/v1" />
        <Arrow x1={160} y1={230} x2={215} y2={230} color="#3b82f6" label="stdio→SSE" dashed />
        <Arrow x1={160} y1={310} x2={215} y2={260} color="#6b7280" label="/health /docs" />
        <Arrow x1={160} y1={390} x2={215} y2={290} color="#f97316" label="ws /responses" />

        {/* ── ENTRY LAYER ── */}
        <GroupBox x={205} y={60} w={250} h={420} label="Entry Layer  (Starlette ASGI)" color="#6366f1" />

        {/* Middleware stack */}
        <Box x={215} y={80} w={230} h={55} color={colors.middleware}
          title="Security Middleware"
          items={["• RequestSizeLimitMiddleware", "• SecurityHeadersMiddleware", "• CORS"]}
          small />
        <Box x={215} y={150} w={230} h={55} color={colors.middleware}
          title="Auth Middleware"
          items={["• FastAuthMiddleware (per-route)", "• 14 provider types (JWT/OAuth…)", "• Bearer pass-through option"]}
          small />
        <Box x={215} y={220} w={230} h={50} color={colors.middleware}
          title="Rate Limiter"
          items={["• Per-client throttling", "• Configurable via YAML"]}
          small />

        {/* Router */}
        <Box x={215} y={285} w={230} h={65} color={colors.entry}
          title="Starlette Router"
          items={["• GET /health", "• GET /  (root)", "• GET /docs (Swagger, optional)"]}
          small />

        {/* Arrows middleware → proxies */}
        <Arrow x1={445} y1={130} x2={490} y2={130} color="#22c55e" label="MCP routes" />
        <Arrow x1={445} y1={200} x2={490} y2={350} color="#f97316" label="LLM routes" />
        <Arrow x1={445} y1={230} x2={490} y2={500} color="#a78bfa" label="agent/prompt" dashed />

        {/* ── MCP PROXY COLUMN ── */}
        <GroupBox x={480} y={20} w={240} h={300} label="MCP Proxy  (proxies/mcp)" color="#22c55e" />

        <Box x={490} y={40} w={220} h={60} color={colors.mcp}
          title="McpProxyBuilder"
          subtitle="build_mcp_proxy_configs()"
          items={["• FastMCP server per route", "• Optional CodeMode transforms"]}
          small />

        <Box x={490} y={120} w={220} h={55} color={colors.mcp}
          title="Proxy Providers"
          items={["• McpProxyProvider  (remote MCP)", "• StaticProvider  (static tools)", "• OpenAPI → MCP converter"]}
          small />

        <Box x={490} y={190} w={220} h={55} color={colors.mcp}
          title="Content Providers"
          items={["• SkillProvider  (./skills dir)", "• PromptProvider  (./prompts dir)", "• AgentProvider  (./agents dir)"]}
          small />

        <Box x={490} y={260} w={220} h={50} color={colors.mcp}
          title="Resource Service"
          items={["• OnDemandRemoteResourceService", "• RemoteResourceSyncTask (bg)"]}
          small />

        {/* ── LLM PROXY COLUMN ── */}
        <GroupBox x={480} y={330} w={240} h={280} label="LLM Gateway  (proxies/llm)" color="#f97316" />

        <Box x={490} y={350} w={220} h={55} color={colors.llm}
          title="LlmRouter  (FastAPI)"
          subtitle="POST /api/v1/..."
          items={["• /chat/completions", "• /embeddings  /audio  /images", "• /v1/messages (Anthropic compat)"]}
          small />

        <Box x={490} y={420} w={220} h={50} color={colors.llm}
          title="RequestDispatcher"
          items={["• Route to correct backend provider", "• Streaming / non-streaming", "• Model catalog lookup"]}
          small />

        <Box x={490} y={485} w={220} h={55} color={colors.llm}
          title="Providers"
          items={["• BaseProvider (OpenAI protocol)", "• AnthropicProvider (translates format)", "• WebSocketProvider (Responses API)"]}
          small />

        <Box x={490} y={555} w={220} h={45} color={colors.llm}
          title="ClientFactory"
          items={["• Per-backend httpx client pool", "• Auth injection (bearer / OAuth)"]}
          small />

        {/* ── CROSS-CUTTING RIGHT COLUMN ── */}
        <GroupBox x={735} y={20} w={185} h={590} label="Cross-cutting" color="#94a3b8" />

        <Box x={745} y={40} w={165} h={95} color={colors.auth}
          title="Auth Registry"
          subtitle="14 provider types"
          items={["basic / bearer / JWT", "Auth0 / Azure AD / AWS", "GitHub / Google / Discord", "OCI / Supabase / Introspection"]}
          small />

        <Box x={745} y={150} w={165} h={70} color={colors.cross}
          title="Config YAML"
          items={["• config_yaml_models.py", "• EnvResolver  (${VAR} subs)", "• Hot-reload on startup"]}
          small />

        <Box x={745} y={235} w={165} h={55} color={colors.cross}
          title="Cache  (TTL KV)"
          items={["• In-memory / Redis / Keyring", "• py-key-value-aio backend"]}
          small />

        <Box x={745} y={305} w={165} h={55} color={colors.cross}
          title="Lifespan Manager"
          items={["• AppLifespanManager", "• MCP app startup/shutdown", "• Background task wiring"]}
          small />

        <Box x={745} y={375} w={165} h={55} color={colors.cross}
          title="Swagger / Docs"
          items={["• SwaggerProvider", "• Auto-collects all MCP + LLM", "• Optional (SWAGGER_ENABLED)"]}
          small />

        <Box x={745} y={445} w={165} h={55} color={colors.cross}
          title="Security Utils"
          items={["• sanitize_error_response()", "• AuthHeaderPolicy", "• Global exception handler"]}
          small />

        <Box x={745} y={515} w={165} h={55} color={colors.cross}
          title="Env / Config"
          items={["• HOST / PORT / SERVER_NAME", "• SWAGGER_ENABLED", "• SERVER_VERSION"]}
          small />

        {/* ── BACKENDS ── */}
        <GroupBox x={10} y={460} w={460} h={300} label="Backend Services" color="#6b7280" />

        <Box x={20} y={480} w={130} h={60} color={colors.backend}
          title="MCP Server (SSE)"
          items={["Remote HTTP/SSE", "MCP protocol"]}
          small />
        <Box x={165} y={480} w={130} h={60} color={colors.backend}
          title="MCP Server (stdio)"
          items={["Local subprocess", "stdin/stdout"]}
          small />
        <Box x={310} y={480} w={150} h={60} color={colors.backend}
          title="OpenAPI Service"
          items={["Any REST API", "→ auto-wrapped as MCP"]}
          small />

        <Box x={20} y={560} w={130} h={65} color={colors.backend}
          title="OpenAI API"
          items={["gpt-4o, o3-mini…", "chat / embed / image", "audio / responses"]}
          small />
        <Box x={165} y={560} w={130} h={65} color={colors.backend}
          title="Anthropic API"
          items={["claude-3-5-sonnet…", "Messages API", "(format translated)"]}
          small />
        <Box x={310} y={560} w={150} h={65} color={colors.backend}
          title="Any OpenAI-compat LLM"
          items={["Ollama / LiteLLM /", "Azure OpenAI /", "Local vLLM…"]}
          small />

        {/* Arrows MCP proxy → backends */}
        <Arrow x1={600} y1={270} x2={360} y2={490} color="#22c55e" />
        <Arrow x1={600} y1={270} x2={230} y2={490} color="#22c55e" />
        <Arrow x1={600} y1={270} x2={385} y2={490} color="#22c55e" dashed />

        {/* Arrows LLM proxy → backends */}
        <Arrow x1={600} y1={570} x2={150} y2={580} color="#f97316" />
        <Arrow x1={600} y1={575} x2={295} y2={590} color="#f97316" />
        <Arrow x1={600} y1={580} x2={460} y2={595} color="#f97316" />

        {/* Cross-cutting → main layers */}
        <Arrow x1={745} y1={90} x2={715} y2={200} color="#a78bfa" dashed />
        <Arrow x1={745} y1={185} x2={715} y2={215} color="#94a3b8" dashed />

        {/* Legend */}
        <g transform="translate(940, 630)">
          <rect x={0} y={0} width={150} height={120} rx="6" fill="#111827" stroke="#374151" strokeWidth="1" />
          <text x={8} y={16} fill="#9ca3af" fontSize="9" fontFamily="monospace" fontWeight="600">LEGEND</text>
          {[
            { c: "#3b82f6", l: "Client" },
            { c: "#6366f1", l: "Entry / Middleware" },
            { c: "#22c55e", l: "MCP Proxy" },
            { c: "#f97316", l: "LLM Gateway" },
            { c: "#a78bfa", l: "Auth / Cross-cutting" },
            { c: "#6b7280", l: "Backend Services" },
          ].map(({ c, l }, i) => (
            <g key={i} transform={`translate(8, ${26 + i * 16})`}>
              <rect width={12} height={10} rx="2" fill={c} opacity="0.8" />
              <text x={18} y={9} fill="#d1d5db" fontSize="9" fontFamily="monospace">{l}</text>
            </g>
          ))}
        </g>
      </svg>

      <div style={{ color: "#475569", fontFamily: "monospace", fontSize: 10, marginTop: 12 }}>
        drunk-ai-proxy v0.1.0 · Python 3.10+ · FastMCP · Starlette · FastAPI · Pydantic v2
      </div>
    </div>
  );
}
