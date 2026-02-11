# Gateway & Daemon Architecture - OpenClaw Code Extraction

**Source**: OpenClaw Gateway & Daemon implementation  
**Purpose**: Reference for building Emonk's gateway daemon system  
**Extraction Date**: 2026-02-11

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Gateway Client Implementation](#gateway-client-implementation)
3. [Gateway Daemon Process](#gateway-daemon-process)
4. [Gateway Lock Mechanism](#gateway-lock-mechanism)
5. [Service Management](#service-management)
6. [Boot & Initialization](#boot--initialization)
7. [Protocol & Communication](#protocol--communication)
8. [Key Takeaways](#key-takeaways)
9. [Emonk Adaptations](#emonk-adaptations)

---

## Architecture Overview

### What is the Gateway?

The Gateway is a **persistent background daemon** that maintains connections to messaging platforms (Telegram, Discord, Slack) and provides a unified WebSocket API for agent interaction.

**Core responsibilities:**
- Maintain persistent connections to messaging platforms
- Route messages between channels and the agent core
- Handle authentication and access control
- Manage connection lifecycle (reconnect, graceful shutdown)
- Provide a unified API via WebSocket (ws://127.0.0.1:18789)

### Why This Architecture?

OpenClaw uses a daemon architecture for several key reasons:

1. **Always-on availability**: Gateway stays running even when CLI tools exit
2. **Connection persistence**: Maintains long-lived connections to messaging platforms
3. **Resource efficiency**: Single process manages all channels
4. **Clean separation**: UI (Telegram) separate from logic (agent core)
5. **Restart resilience**: Can restart without losing channel connections

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   Gateway Daemon                         │
│                  (Background Process)                    │
│                                                          │
│  ┌────────────────────────────────────────────┐         │
│  │         WebSocket Server                    │         │
│  │         ws://127.0.0.1:18789               │         │
│  │      (Loopback-only binding)               │         │
│  └─────────────┬──────────────────────────────┘         │
│                │                                          │
│                ▼                                          │
│  ┌────────────────────────────────────────────┐         │
│  │       Message Router                        │         │
│  │   - Route incoming messages                │         │
│  │   - Dispatch to handlers                   │         │
│  │   - Queue management                       │         │
│  └─────────────┬──────────────────────────────┘         │
│                │                                          │
│                ▼                                          │
│  ┌────────────────────────────────────────────┐         │
│  │      Channel Connectors                    │         │
│  │   - Telegram Bot API                       │         │
│  │   - Discord Gateway                        │         │
│  │   - Other platforms                        │         │
│  └────────────────────────────────────────────┘         │
│                                                          │
└─────────────────────────────────────────────────────────┘
         │                           │
         ▼                           ▼
┌──────────────────┐       ┌──────────────────┐
│   CLI Client     │       │  Telegram Bot    │
│   (Gateway Call) │       │   (Messages)     │
└──────────────────┘       └──────────────────┘
```

---

## Gateway Client Implementation

### Overview

The Gateway Client (`src/gateway/client.ts`) provides a WebSocket client that connects to the gateway daemon and handles bidirectional communication.

### Core Client Class

```typescript
export class GatewayClient {
  private ws: WebSocket | null = null;
  private opts: GatewayClientOptions;
  private pending = new Map<string, Pending>();  // Track pending requests
  private backoffMs = 1000;                      // Reconnect backoff
  private closed = false;                        // Shutdown flag
  private lastSeq: number | null = null;         // Message sequence tracking
  private connectNonce: string | null = null;    // Connection nonce
  private connectSent = false;                   // Connection state
  private connectTimer: NodeJS.Timeout | null = null;
  private lastTick: number | null = null;        // Heartbeat tracking
  private tickIntervalMs = 30_000;               // 30 second heartbeat
  private tickTimer: NodeJS.Timeout | null = null;

  constructor(opts: GatewayClientOptions) {
    this.opts = {
      ...opts,
      deviceIdentity: opts.deviceIdentity ?? loadOrCreateDeviceIdentity(),
    };
  }

  start() {
    if (this.closed) {
      return;
    }
    const url = this.opts.url ?? "ws://127.0.0.1:18789";
    
    // Configuration: Large payload support (25MB for screenshots)
    const wsOptions: ClientOptions = {
      maxPayload: 25 * 1024 * 1024,
    };
    
    // TLS fingerprint validation (for remote gateways)
    if (url.startsWith("wss://") && this.opts.tlsFingerprint) {
      wsOptions.rejectUnauthorized = false;
      wsOptions.checkServerIdentity = ((_host: string, cert: CertMeta) => {
        const fingerprint = normalizeFingerprint(cert.fingerprint256);
        const expected = normalizeFingerprint(this.opts.tlsFingerprint);
        if (fingerprint !== expected) {
          return new Error("gateway tls fingerprint mismatch");
        }
        return undefined;
      });
    }
    
    this.ws = new WebSocket(url, wsOptions);
    
    // Event handlers
    this.ws.on("open", () => {
      this.queueConnect();  // Send connect frame
    });
    
    this.ws.on("message", (data) => this.handleMessage(rawDataToString(data)));
    
    this.ws.on("close", (code, reason) => {
      this.ws = null;
      this.flushPendingErrors(new Error(`gateway closed (${code}): ${reason}`));
      this.scheduleReconnect();
      this.opts.onClose?.(code, reason);
    });
    
    this.ws.on("error", (err) => {
      if (!this.connectSent) {
        this.opts.onConnectError?.(err);
      }
    });
  }

  stop() {
    this.closed = true;
    if (this.tickTimer) {
      clearInterval(this.tickTimer);
      this.tickTimer = null;
    }
    this.ws?.close();
    this.ws = null;
    this.flushPendingErrors(new Error("gateway client stopped"));
  }
}
```

### Key Connection Pattern: Loopback Binding

**Critical Pattern**: OpenClaw defaults to `ws://127.0.0.1:18789` (loopback only)

```typescript
// Default URL resolution
const url = this.opts.url ?? "ws://127.0.0.1:18789";

// Bind modes (from gateway config)
const bindMode = config.gateway?.bind ?? "loopback";
// Options: "loopback", "lan", "tailnet", "auto", "custom"
```

**Why loopback?**
- Security: Only accessible from local machine
- No network exposure by default
- Fast local communication
- Prevents accidental remote access

### Authentication Flow

```typescript
private sendConnect() {
  const role = this.opts.role ?? "operator";
  
  // Try device token first, fall back to config token
  const storedToken = this.opts.deviceIdentity
    ? loadDeviceAuthToken({ deviceId: this.opts.deviceIdentity.deviceId, role })?.token
    : null;
  const authToken = storedToken ?? this.opts.token ?? undefined;
  
  const auth = authToken || this.opts.password
    ? {
        token: authToken,
        password: this.opts.password,
      }
    : undefined;
  
  // Build connect frame with auth
  const connectFrame: ConnectParams = {
    protocolVersion: PROTOCOL_VERSION,
    clientName: this.opts.clientName ?? "cli",
    clientVersion: this.opts.clientVersion,
    mode: this.opts.mode ?? "operator",
    role,
    auth,
    deviceIdentity: this.opts.deviceIdentity
      ? {
          deviceId: this.opts.deviceIdentity.deviceId,
          publicKey: publicKeyRawBase64UrlFromPem(this.opts.deviceIdentity.publicKeyPem),
        }
      : undefined,
  };
  
  this.send({ type: "connect", params: connectFrame });
}
```

### Request/Response Pattern

```typescript
// Call gateway method with timeout
async call<T>(method: string, params: unknown, expectFinal = true): Promise<T> {
  return new Promise((resolve, reject) => {
    const requestId = randomUUID();
    
    // Register pending request
    this.pending.set(requestId, {
      resolve: resolve as (value: unknown) => void,
      reject,
      expectFinal,
    });
    
    // Send request frame
    this.send({
      type: "request",
      requestId,
      method,
      params,
    });
    
    // Set timeout
    const timeoutMs = 10_000;
    setTimeout(() => {
      if (this.pending.has(requestId)) {
        this.pending.delete(requestId);
        reject(new Error(`gateway call timeout after ${timeoutMs}ms`));
      }
    }, timeoutMs);
  });
}

// Handle response frames
private handleMessage(raw: string) {
  const frame = JSON.parse(raw);
  
  if (frame.type === "response") {
    const pending = this.pending.get(frame.requestId);
    if (!pending) {
      return;  // Orphaned response
    }
    
    if (frame.error) {
      this.pending.delete(frame.requestId);
      pending.reject(new Error(frame.error.message));
    } else if (frame.final || pending.expectFinal) {
      this.pending.delete(frame.requestId);
      pending.resolve(frame.result);
    } else {
      // Streaming response - keep pending
      pending.resolve(frame.result);
    }
  } else if (frame.type === "event") {
    // Handle server-initiated events
    this.opts.onEvent?.(frame);
  }
}
```

### Reconnection Strategy

```typescript
private scheduleReconnect() {
  if (this.closed) {
    return;
  }
  
  // Exponential backoff
  const backoffMs = Math.min(this.backoffMs, 30_000);  // Max 30 seconds
  
  setTimeout(() => {
    if (!this.closed) {
      this.start();
      this.backoffMs = Math.min(this.backoffMs * 2, 30_000);
    }
  }, backoffMs);
}
```

---

## Gateway Daemon Process

### Overview

The Gateway Daemon (`src/macos/gateway-daemon.ts`) is the long-running process that hosts the WebSocket server and channel connectors.

### Main Daemon Entry Point

```typescript
async function main() {
  // 1. Enable structured logging
  enableConsoleCapture();
  setConsoleTimestampPrefix(true);
  setVerbose(hasFlag(args, "--verbose"));
  
  // 2. Load configuration
  const cfg = loadConfig();
  const port = resolvePort(args, cfg);  // Default: 18789
  const bind = resolveBind(args, cfg);  // Default: "loopback"
  
  // 3. Acquire gateway lock (prevent multiple instances)
  let lock: GatewayLockHandle | null = null;
  try {
    lock = await acquireGatewayLock();
  } catch (err) {
    if (err instanceof GatewayLockError) {
      console.error(`Gateway start blocked: ${err.message}`);
      process.exit(1);
    }
    throw err;
  }
  
  // 4. Set up signal handlers
  process.on("SIGTERM", onSigterm);
  process.on("SIGINT", onSigint);
  process.on("SIGUSR1", onSigusr1);  // Restart signal
  
  // 5. Start server in restart loop
  while (true) {
    try {
      server = await startGatewayServer(port, { bind });
    } catch (err) {
      console.error(`Gateway failed to start: ${err}`);
      process.exit(1);
    }
    
    // Wait for restart signal
    await new Promise<void>((resolve) => {
      restartResolver = resolve;
    });
  }
}
```

### Graceful Shutdown Pattern

```typescript
const request = (action: "stop" | "restart", signal: string) => {
  if (shuttingDown) {
    return;  // Ignore duplicate signals
  }
  shuttingDown = true;
  const isRestart = action === "restart";
  
  console.log(`Gateway: received ${signal}; ${isRestart ? "restarting" : "shutting down"}`);
  
  // Force exit after 5 seconds if shutdown hangs
  forceExitTimer = setTimeout(() => {
    console.error("Gateway: shutdown timed out; exiting without full cleanup");
    process.exit(0);
  }, 5000);
  
  void (async () => {
    try {
      // Close server gracefully
      await server?.close({
        reason: isRestart ? "gateway restarting" : "gateway stopping",
        restartExpectedMs: isRestart ? 1500 : null,  // Tell clients to wait
      });
    } catch (err) {
      console.error(`Gateway: shutdown error: ${err}`);
    } finally {
      if (forceExitTimer) {
        clearTimeout(forceExitTimer);
      }
      server = null;
      
      if (isRestart) {
        shuttingDown = false;
        restartResolver?.();  // Trigger restart loop
      } else {
        process.exit(0);
      }
    }
  })();
};

// Signal handlers
const onSigterm = () => request("stop", "SIGTERM");
const onSigint = () => request("stop", "SIGINT");
const onSigusr1 = () => {
  // Restart signal (requires authorization)
  const authorized = consumeGatewaySigusr1RestartAuthorization();
  if (!authorized) {
    console.log("Gateway: SIGUSR1 restart ignored (not authorized)");
    return;
  }
  request("restart", "SIGUSR1");
};
```

### Port & Bind Resolution

```typescript
// Port priority: CLI arg > env var > config > default
const portRaw = 
  argValue(args, "--port") ??
  process.env.OPENCLAW_GATEWAY_PORT ??
  (typeof cfg.gateway?.port === "number" ? String(cfg.gateway.port) : "") ??
  "18789";
const port = Number.parseInt(portRaw, 10);

// Bind mode: Controls network interface
// - "loopback": 127.0.0.1 only (default)
// - "lan": All local network interfaces
// - "tailnet": Tailscale VPN interface
// - "custom": User-specified interface
const bindRaw =
  argValue(args, "--bind") ??
  process.env.OPENCLAW_GATEWAY_BIND ??
  cfg.gateway?.bind ??
  "loopback";
```

---

## Gateway Lock Mechanism

### Purpose

The Gateway Lock (`src/infra/gateway-lock.ts`) ensures **only one gateway daemon runs per configuration** to prevent:
- Port conflicts (multiple daemons trying to bind to 18789)
- Resource exhaustion (duplicate channel connections)
- State corruption (multiple writers to same files)

### Lock Implementation

```typescript
export async function acquireGatewayLock(
  opts: GatewayLockOptions = {},
): Promise<GatewayLockHandle | null> {
  const env = opts.env ?? process.env;
  
  // Skip lock in tests
  if (env.OPENCLAW_ALLOW_MULTI_GATEWAY === "1" || env.NODE_ENV === "test") {
    return null;
  }
  
  const timeoutMs = opts.timeoutMs ?? 5000;
  const pollIntervalMs = opts.pollIntervalMs ?? 100;
  const staleMs = opts.staleMs ?? 30_000;  // 30 seconds
  const platform = opts.platform ?? process.platform;
  
  // Lock path is hash of config path (one lock per config)
  const { lockPath, configPath } = resolveGatewayLockPath(env);
  await fs.mkdir(path.dirname(lockPath), { recursive: true });
  
  const startedAt = Date.now();
  let lastPayload: LockPayload | null = null;
  
  // Poll for lock availability
  while (Date.now() - startedAt < timeoutMs) {
    try {
      // Try to create lock file exclusively
      const handle = await fs.open(lockPath, "wx");  // "wx" = write exclusive
      
      // Write lock payload
      const startTime = platform === "linux" ? readLinuxStartTime(process.pid) : null;
      const payload: LockPayload = {
        pid: process.pid,
        createdAt: new Date().toISOString(),
        configPath,
        startTime,  // For PID reuse detection on Linux
      };
      await handle.writeFile(JSON.stringify(payload), "utf8");
      
      // Return lock handle with release function
      return {
        lockPath,
        configPath,
        release: async () => {
          await handle.close().catch(() => undefined);
          await fs.rm(lockPath, { force: true });
        },
      };
    } catch (err) {
      const code = (err as { code?: unknown }).code;
      if (code !== "EEXIST") {
        throw new GatewayLockError(`failed to acquire gateway lock at ${lockPath}`, err);
      }
      
      // Lock file exists - check if owner is alive
      lastPayload = await readLockPayload(lockPath);
      const ownerPid = lastPayload?.pid;
      const ownerStatus = ownerPid
        ? resolveGatewayOwnerStatus(ownerPid, lastPayload, platform)
        : "unknown";
      
      // Remove stale lock
      if (ownerStatus === "dead") {
        await fs.rm(lockPath, { force: true });
        continue;  // Retry immediately
      }
      
      // Check for stale lock (30s old but can't verify process)
      if (ownerStatus !== "alive") {
        const createdAt = Date.parse(lastPayload?.createdAt ?? "");
        const stale = Number.isFinite(createdAt) && (Date.now() - createdAt > staleMs);
        if (stale) {
          await fs.rm(lockPath, { force: true });
          continue;
        }
      }
      
      // Lock is held by active process - wait and retry
      await new Promise((r) => setTimeout(r, pollIntervalMs));
    }
  }
  
  // Timeout - lock still held
  const owner = lastPayload?.pid ? ` (pid ${lastPayload.pid})` : "";
  throw new GatewayLockError(
    `gateway already running${owner}; lock timeout after ${timeoutMs}ms`
  );
}
```

### PID Reuse Detection (Linux)

```typescript
// On Linux, detect if PID was reused by a different process
function resolveGatewayOwnerStatus(
  pid: number,
  payload: LockPayload | null,
  platform: NodeJS.Platform,
): LockOwnerStatus {
  if (!isAlive(pid)) {
    return "dead";
  }
  
  if (platform !== "linux") {
    return "alive";  // No reliable PID reuse detection
  }
  
  // Compare process start time
  const payloadStartTime = payload?.startTime;
  if (Number.isFinite(payloadStartTime)) {
    const currentStartTime = readLinuxStartTime(pid);  // From /proc/PID/stat
    if (currentStartTime == null) {
      return "unknown";
    }
    return currentStartTime === payloadStartTime ? "alive" : "dead";
  }
  
  // Fallback: Check if PID's cmdline looks like gateway
  const args = readLinuxCmdline(pid);  // From /proc/PID/cmdline
  if (!args) {
    return "unknown";
  }
  return isGatewayArgv(args) ? "alive" : "dead";
}

function readLinuxStartTime(pid: number): number | null {
  try {
    const raw = fs.readFileSync(`/proc/${pid}/stat`, "utf8").trim();
    const closeParen = raw.lastIndexOf(")");
    const rest = raw.slice(closeParen + 1).trim();
    const fields = rest.split(/\s+/);
    const startTime = Number.parseInt(fields[19] ?? "", 10);  // Field 22 (starttime)
    return Number.isFinite(startTime) ? startTime : null;
  } catch {
    return null;
  }
}
```

### Lock Path Resolution

```typescript
function resolveGatewayLockPath(env: NodeJS.ProcessEnv) {
  const stateDir = resolveStateDir(env);
  const configPath = resolveConfigPath(env, stateDir);
  
  // Hash config path to generate unique lock file
  const hash = createHash("sha1")
    .update(configPath)
    .digest("hex")
    .slice(0, 8);
  
  const lockDir = resolveGatewayLockDir();  // ~/.openclaw/locks/
  const lockPath = path.join(lockDir, `gateway.${hash}.lock`);
  
  return { lockPath, configPath };
}
```

---

## Service Management

### Overview

The Service Manager (`src/daemon/service.ts`) provides cross-platform daemon installation using native system services:
- **macOS**: LaunchAgent (launchd)
- **Linux**: systemd service
- **Windows**: Scheduled Task (Task Scheduler)

### Service Interface

```typescript
export type GatewayService = {
  label: string;                   // "LaunchAgent", "systemd", "Scheduled Task"
  loadedText: string;              // "loaded", "enabled", "registered"
  notLoadedText: string;           // "not loaded", "disabled", "missing"
  
  install: (args: GatewayServiceInstallArgs) => Promise<void>;
  uninstall: (args: { env: Record<string, string>; stdout: WritableStream }) => Promise<void>;
  stop: (args: { env: Record<string, string>; stdout: WritableStream }) => Promise<void>;
  restart: (args: { env: Record<string, string>; stdout: WritableStream }) => Promise<void>;
  isLoaded: (args: { env?: Record<string, string> }) => Promise<boolean>;
  
  readCommand: (env: Record<string, string>) => Promise<{
    programArguments: string[];
    workingDirectory?: string;
    environment?: Record<string, string>;
    sourcePath?: string;
  } | null>;
  
  readRuntime: (env: Record<string, string>) => Promise<GatewayServiceRuntime>;
};
```

### Platform Selection

```typescript
export function resolveGatewayService(): GatewayService {
  if (process.platform === "darwin") {
    // macOS: LaunchAgent
    return {
      label: "LaunchAgent",
      loadedText: "loaded",
      notLoadedText: "not loaded",
      install: async (args) => {
        await installLaunchAgent(args);
      },
      uninstall: async (args) => {
        await uninstallLaunchAgent(args);
      },
      stop: async (args) => {
        await stopLaunchAgent(args);
      },
      restart: async (args) => {
        await restartLaunchAgent(args);
      },
      isLoaded: async (args) => isLaunchAgentLoaded(args),
      readCommand: readLaunchAgentProgramArguments,
      readRuntime: readLaunchAgentRuntime,
    };
  }
  
  if (process.platform === "linux") {
    // Linux: systemd service
    return {
      label: "systemd",
      loadedText: "enabled",
      notLoadedText: "disabled",
      install: async (args) => {
        await installSystemdService(args);
      },
      // ... similar to macOS
    };
  }
  
  if (process.platform === "win32") {
    // Windows: Scheduled Task
    return {
      label: "Scheduled Task",
      loadedText: "registered",
      notLoadedText: "missing",
      install: async (args) => {
        await installScheduledTask(args);
      },
      // ... similar to macOS
    };
  }
  
  throw new Error(`Gateway service install not supported on ${process.platform}`);
}
```

### Service Installation Example (systemd)

```typescript
export async function installSystemdService(args: GatewayServiceInstallArgs) {
  const serviceName = "openclaw-gateway";
  const unitFilePath = path.join(
    os.homedir(),
    ".config/systemd/user",
    `${serviceName}.service`
  );
  
  // Create unit file content
  const programArgs = args.programArguments.map(arg => 
    arg.includes(" ") ? `"${arg}"` : arg
  ).join(" ");
  
  const unitContent = `
[Unit]
Description=OpenClaw Gateway
After=network.target

[Service]
Type=simple
ExecStart=${programArgs}
WorkingDirectory=${args.workingDirectory ?? process.cwd()}
Restart=always
RestartSec=10
${Object.entries(args.environment ?? {})
  .map(([key, value]) => `Environment="${key}=${value}"`)
  .join("\n")}

[Install]
WantedBy=default.target
`.trim();
  
  // Write unit file
  await fs.mkdir(path.dirname(unitFilePath), { recursive: true });
  await fs.writeFile(unitFilePath, unitContent, "utf8");
  
  // Reload systemd and enable service
  await execAsync("systemctl --user daemon-reload");
  await execAsync(`systemctl --user enable ${serviceName}`);
  await execAsync(`systemctl --user start ${serviceName}`);
  
  args.stdout.write(`Installed systemd service: ${serviceName}\n`);
}
```

---

## Boot & Initialization

### Overview

The Boot system (`src/gateway/boot.ts`) runs startup checks by executing a `BOOT.md` file if present.

### Boot Flow

```typescript
export async function runBootOnce(params: {
  cfg: OpenClawConfig;
  deps: CliDeps;
  workspaceDir: string;
}): Promise<BootRunResult> {
  // 1. Try to load BOOT.md
  let result: Awaited<ReturnType<typeof loadBootFile>>;
  try {
    result = await loadBootFile(params.workspaceDir);
  } catch (err) {
    return { status: "failed", reason: err.message };
  }
  
  // 2. Skip if missing or empty
  if (result.status === "missing" || result.status === "empty") {
    return { status: "skipped", reason: result.status };
  }
  
  // 3. Build prompt from BOOT.md content
  const sessionKey = resolveMainSessionKey(params.cfg);
  const message = buildBootPrompt(result.content ?? "");
  
  // 4. Execute via agent command (no delivery)
  try {
    await agentCommand(
      {
        message,
        sessionKey,
        deliver: false,  // Don't send responses to channels
      },
      bootRuntime,
      params.deps,
    );
    return { status: "ran" };
  } catch (err) {
    return { status: "failed", reason: err.message };
  }
}
```

### Boot File Loading

```typescript
async function loadBootFile(
  workspaceDir: string,
): Promise<{ content?: string; status: "ok" | "missing" | "empty" }> {
  const bootPath = path.join(workspaceDir, "BOOT.md");
  
  try {
    const content = await fs.readFile(bootPath, "utf-8");
    const trimmed = content.trim();
    
    if (!trimmed) {
      return { status: "empty" };
    }
    
    return { status: "ok", content: trimmed };
  } catch (err) {
    const anyErr = err as { code?: string };
    if (anyErr.code === "ENOENT") {
      return { status: "missing" };
    }
    throw err;
  }
}
```

### Boot Prompt Construction

```typescript
function buildBootPrompt(content: string) {
  return [
    "You are running a boot check. Follow BOOT.md instructions exactly.",
    "",
    "BOOT.md:",
    content,
    "",
    "If BOOT.md asks you to send a message, use the message tool.",
    `After sending with the message tool, reply with ONLY: ${SILENT_REPLY_TOKEN}.`,
    `If nothing needs attention, reply with ONLY: ${SILENT_REPLY_TOKEN}.`,
  ].join("\n");
}
```

**Use Case**: BOOT.md can check system health, send startup notifications, or perform initialization tasks.

---

## Protocol & Communication

### WebSocket Frame Types

```typescript
// Request from client to gateway
type RequestFrame = {
  type: "request";
  requestId: string;      // UUID for tracking responses
  method: string;         // e.g., "agent.chat", "channels.status"
  params?: unknown;       // Method-specific parameters
};

// Response from gateway to client
type ResponseFrame = {
  type: "response";
  requestId: string;      // Matches request
  final: boolean;         // True if last chunk
  result?: unknown;       // Response payload
  error?: ErrorShape;     // If request failed
};

// Event from gateway to client (unsolicited)
type EventFrame = {
  type: "event";
  event: string;          // e.g., "agent.progress", "channel.message"
  params?: unknown;       // Event payload
};

// Connect handshake
type ConnectParams = {
  type: "connect";
  protocolVersion: number;
  clientName: string;
  clientVersion?: string;
  mode: "operator" | "readonly";
  role: string;
  auth?: {
    token?: string;
    password?: string;
  };
  deviceIdentity?: {
    deviceId: string;
    publicKey: string;
  };
};

// Hello response
type HelloOk = {
  type: "hello_ok";
  protocolVersion: number;
  gatewayVersion: string;
  sessionId: string;
};
```

### Connection Lifecycle

```
Client                          Gateway
  │                               │
  │───── WebSocket Connect ───────▶│
  │                               │
  │◀──── TCP Handshake ───────────│
  │                               │
  │───── Connect Frame ───────────▶│
  │      (auth, version)          │
  │                               │
  │◀──── HelloOk Frame ────────────│
  │      (session, version)       │
  │                               │
  │───── Request Frame ───────────▶│
  │      (method, params)         │
  │                               │
  │◀──── Response Frame ───────────│
  │      (result)                 │
  │                               │
  │◀──── Event Frame ──────────────│
  │      (unsolicited)            │
  │                               │
  │───── Close Frame ─────────────▶│
  │                               │
  │◀──── Close Ack ────────────────│
```

### Gateway Call Pattern

```typescript
export async function callGateway<T>(opts: CallGatewayOptions): Promise<T> {
  const timeoutMs = opts.timeoutMs ?? 10_000;
  const config = opts.config ?? loadConfig();
  
  // Resolve gateway URL (local or remote)
  const connectionDetails = buildGatewayConnectionDetails({
    config,
    url: opts.url,
  });
  const url = connectionDetails.url;
  
  // Create client
  const client = new GatewayClient({
    url,
    token: opts.token,
    password: opts.password,
    clientName: opts.clientName ?? "cli",
    mode: opts.mode ?? "operator",
  });
  
  // Connect and call
  return new Promise((resolve, reject) => {
    let response: T | null = null;
    let error: Error | null = null;
    
    client.onConnectError = (err) => {
      error = err;
    };
    
    client.onClose = () => {
      if (error) {
        reject(error);
      } else if (response !== null) {
        resolve(response);
      } else {
        reject(new Error("Gateway connection closed before response"));
      }
    };
    
    client.start();
    
    // Wait for connection, then send request
    setTimeout(async () => {
      try {
        response = await client.call<T>(opts.method, opts.params, opts.expectFinal);
        client.stop();
      } catch (err) {
        error = err instanceof Error ? err : new Error(String(err));
        client.stop();
      }
    }, 100);  // Small delay for connection
    
    // Overall timeout
    setTimeout(() => {
      if (response === null && error === null) {
        error = new Error(`Gateway call timeout after ${timeoutMs}ms`);
        client.stop();
      }
    }, timeoutMs);
  });
}
```

---

## Key Takeaways

### Architecture Insights

1. **Daemon Pattern**: Long-running background process with WebSocket API
2. **Loopback Default**: Security-first with `127.0.0.1:18789` binding
3. **Lock Mechanism**: Prevents multiple instances via filesystem lock
4. **Graceful Shutdown**: 5-second timeout with restart support
5. **Service Integration**: Native OS services (launchd, systemd, Task Scheduler)

### Critical Patterns

1. **Connection Resilience**:
   - Automatic reconnection with exponential backoff
   - Pending request cleanup on disconnect
   - Heartbeat detection (30s intervals)

2. **Security**:
   - TLS fingerprint validation for remote connections
   - Device identity with public key auth
   - Token vs password fallback

3. **Process Management**:
   - PID-based lock with reuse detection (Linux)
   - Stale lock cleanup (30s threshold)
   - Signal-based restart (SIGUSR1)

4. **Error Handling**:
   - Force exit after 5s if shutdown hangs
   - Comprehensive error codes
   - Connection retry with backoff

### Performance Considerations

1. **Large Payloads**: 25MB max for screenshots/media
2. **Heartbeat**: 30s interval to detect stalled connections
3. **Reconnect Backoff**: 1s → 30s max
4. **Lock Polling**: 100ms intervals, 5s timeout

---

## Emonk Adaptations

### What to Keep

1. **Loopback Binding**: Keep `127.0.0.1:18789` default for security
2. **Gateway Lock**: Prevent multiple daemon instances
3. **Graceful Shutdown**: Signal handlers with timeout
4. **Reconnection Logic**: Exponential backoff for resilience

### What to Simplify

1. **No Multi-Platform Service Management**: Focus on Docker/systemd only
2. **No TLS Fingerprint**: Local-only deployment
3. **No Device Pairing**: Simpler token-based auth
4. **No Boot System**: Not needed for social media agent

### Emonk-Specific Changes

1. **TypeScript → Python**:
   ```python
   # Gateway client in Python
   import asyncio
   import websockets
   import json
   
   class GatewayClient:
       def __init__(self, url="ws://127.0.0.1:18789"):
           self.url = url
           self.ws = None
           self.pending = {}
       
       async def connect(self):
           self.ws = await websockets.connect(self.url)
           await self.send_connect()
       
       async def call(self, method, params):
           request_id = str(uuid.uuid4())
           request = {
               "type": "request",
               "requestId": request_id,
               "method": method,
               "params": params
           }
           await self.ws.send(json.dumps(request))
           
           # Wait for response
           response = await self.ws.recv()
           frame = json.loads(response)
           
           if frame.get("error"):
               raise Exception(frame["error"]["message"])
           return frame.get("result")
   ```

2. **Simplified Lock**:
   ```python
   import fcntl
   import os
   
   class GatewayLock:
       def __init__(self, lock_path="/tmp/emonk-gateway.lock"):
           self.lock_path = lock_path
           self.lock_file = None
       
       def acquire(self, timeout=5):
           start = time.time()
           while time.time() - start < timeout:
               try:
                   self.lock_file = open(self.lock_path, "w")
                   fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                   self.lock_file.write(str(os.getpid()))
                   self.lock_file.flush()
                   return True
               except BlockingIOError:
                   time.sleep(0.1)
           raise Exception("Gateway already running")
       
       def release(self):
           if self.lock_file:
               fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
               self.lock_file.close()
               os.remove(self.lock_path)
   ```

3. **Docker Integration**:
   ```dockerfile
   # Run gateway as main container process
   CMD ["python", "-m", "emonk.gateway", "--bind", "loopback", "--port", "18789"]
   ```

4. **Systemd Service** (for production):
   ```ini
   [Unit]
   Description=Emonk Gateway
   After=network.target
   
   [Service]
   Type=simple
   ExecStart=/usr/bin/python -m emonk.gateway
   Restart=always
   RestartSec=10
   
   [Install]
   WantedBy=multi-user.target
   ```

### Key Implementation Priorities

1. **Phase 1**: Basic gateway daemon with WebSocket server
2. **Phase 2**: Gateway lock mechanism
3. **Phase 3**: Graceful shutdown with signal handlers
4. **Phase 4**: Reconnection logic with backoff
5. **Phase 5**: Service management (systemd)

### Testing Strategy

1. **Unit Tests**: Gateway lock, reconnection logic
2. **Integration Tests**: WebSocket communication
3. **Manual Tests**: Multiple instance prevention, graceful shutdown

---

## References

- OpenClaw Gateway Client: `src/gateway/client.ts`
- OpenClaw Gateway Daemon: `src/macos/gateway-daemon.ts`
- OpenClaw Gateway Lock: `src/infra/gateway-lock.ts`
- OpenClaw Service Manager: `src/daemon/service.ts`
- OpenClaw Boot System: `src/gateway/boot.ts`

**Next Document**: [02_telegram_integration.md](02_telegram_integration.md)
