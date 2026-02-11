# Telegram Integration - OpenClaw Code Extraction

**Source**: OpenClaw Telegram Bot implementation  
**Purpose**: Reference for building Emonk's Telegram integration  
**Extraction Date**: 2026-02-11

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Bot Handlers](#bot-handlers)
3. [Message Dispatch System](#message-dispatch-system)
4. [Message Context Building](#message-context-building)
5. [Native Commands](#native-commands)
6. [Account Management](#account-management)
7. [Access Control](#access-control)
8. [Media Handling](#media-handling)
9. [Key Takeaways](#key-takeaways)
10. [Emonk Adaptations](#emonk-adaptations)

---

## Architecture Overview

### Core Components

OpenClaw's Telegram integration consists of several key layers:

```
┌─────────────────────────────────────────────────────────┐
│             Telegram Bot (Grammy Framework)              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────┐         │
│  │           Bot Handlers                      │         │
│  │   - Message events                         │         │
│  │   - Callback queries (inline buttons)      │         │
│  │   - Media groups                           │         │
│  │   - Text fragments                         │         │
│  └─────────────┬──────────────────────────────┘         │
│                │                                          │
│                ▼                                          │
│  ┌────────────────────────────────────────────┐         │
│  │       Message Context Builder               │         │
│  │   - Extract sender info                    │         │
│  │   - Check access control                   │         │
│  │   - Resolve routing                        │         │
│  │   - Build history context                  │         │
│  └─────────────┬──────────────────────────────┘         │
│                │                                          │
│                ▼                                          │
│  ┌────────────────────────────────────────────┐         │
│  │       Message Dispatcher                    │         │
│  │   - Route to agent                         │         │
│  │   - Handle streaming                       │         │
│  │   - Send typing indicators                 │         │
│  │   - Deliver responses                      │         │
│  └────────────────────────────────────────────┘         │
│                                                          │
└─────────────────────────────────────────────────────────┘
         │                           │
         ▼                           ▼
┌──────────────────┐       ┌──────────────────┐
│   Agent Core     │       │  Telegram API    │
│   (LLM)          │       │   (Responses)    │
└──────────────────┘       └──────────────────┘
```

### Grammy Framework

OpenClaw uses Grammy (TypeScript Telegram bot framework):

```typescript
import { Bot } from "grammy";

// Create bot with token
const bot = new Bot(token, {
  // Client options
  client: {
    timeoutSeconds: 600,  // 10 minute timeout for long-polling
  },
});

// Register handlers
bot.on("message", async (ctx) => {
  // Handle incoming messages
});

bot.on("callback_query", async (ctx) => {
  // Handle inline button clicks
});

// Start bot
await bot.start();
```

### Key Design Patterns

1. **Event-Driven**: React to Telegram updates (messages, callbacks)
2. **Debouncing**: Combine rapid messages into single request
3. **Media Grouping**: Batch media albums for processing
4. **Text Fragmenting**: Merge sequential text messages
5. **Access Control**: Multi-layer allow/block lists
6. **Routing**: Map chats to specific agents/sessions

---

## Bot Handlers

### Overview

Bot handlers (`src/telegram/bot-handlers.ts`) register event listeners and process incoming updates.

### Handler Registration Pattern

```typescript
export const registerTelegramHandlers = ({
  cfg,
  accountId,
  bot,
  opts,
  runtime,
  mediaMaxBytes,
  telegramCfg,
  groupAllowFrom,
  resolveGroupPolicy,
  resolveTelegramGroupConfig,
  shouldSkipUpdate,
  processMessage,
  logger,
}: RegisterTelegramHandlerParams) => {
  // Configuration constants
  const TELEGRAM_TEXT_FRAGMENT_START_THRESHOLD_CHARS = 4000;
  const TELEGRAM_TEXT_FRAGMENT_MAX_GAP_MS = 1500;
  const TELEGRAM_TEXT_FRAGMENT_MAX_ID_GAP = 1;
  const TELEGRAM_TEXT_FRAGMENT_MAX_PARTS = 12;
  const TELEGRAM_TEXT_FRAGMENT_MAX_TOTAL_CHARS = 50_000;
  const MEDIA_GROUP_TIMEOUT_MS = 1000;
  
  // Buffers for batching
  const mediaGroupBuffer = new Map<string, MediaGroupEntry>();
  const textFragmentBuffer = new Map<string, TextFragmentEntry>();
  
  // Debouncer for rapid messages
  const debounceMs = resolveInboundDebounceMs({ cfg, channel: "telegram" });
  const inboundDebouncer = createInboundDebouncer<TelegramDebounceEntry>({
    debounceMs,
    buildKey: (entry) => entry.debounceKey,
    shouldDebounce: (entry) => {
      // Don't debounce media messages
      if (entry.allMedia.length > 0) {
        return false;
      }
      // Don't debounce control commands
      const text = entry.msg.text ?? entry.msg.caption ?? "";
      return !hasControlCommand(text, cfg, { botUsername: entry.botUsername });
    },
    onFlush: async (entries) => {
      // Combine debounced messages into single request
      const combinedText = entries
        .map((entry) => entry.msg.text ?? entry.msg.caption ?? "")
        .filter(Boolean)
        .join("\n");
      // Process combined message
      await processMessage(lastCtx, [], storeAllowFrom);
    },
  });
  
  // Register message handler
  bot.on("message", async (ctx) => {
    // Skip if update should be ignored
    if (shouldSkipUpdate(ctx)) {
      return;
    }
    
    // Process message
    await handleMessage(ctx);
  });
  
  // Register callback query handler (inline buttons)
  bot.on("callback_query", async (ctx) => {
    // Answer immediately to prevent retry
    await bot.api.answerCallbackQuery(ctx.callbackQuery.id);
    
    // Handle button click
    await handleCallbackQuery(ctx);
  });
};
```

### Media Group Handling

Media groups (albums) are batched and processed together:

```typescript
const processMediaGroup = async (entry: MediaGroupEntry) => {
  // Sort messages by ID
  entry.messages.sort((a, b) => a.msg.message_id - b.msg.message_id);
  
  // Find message with caption
  const captionMsg = entry.messages.find((m) => m.msg.caption || m.msg.text);
  const primaryEntry = captionMsg ?? entry.messages[0];
  
  // Collect all media
  const allMedia: TelegramMediaRef[] = [];
  for (const { ctx } of entry.messages) {
    const media = await resolveMedia(ctx, mediaMaxBytes, opts.token, opts.proxyFetch);
    if (media) {
      allMedia.push({
        path: media.path,
        contentType: media.contentType,
        stickerMetadata: media.stickerMetadata,
      });
    }
  }
  
  // Process as single message with multiple attachments
  const storeAllowFrom = await readChannelAllowFromStore("telegram").catch(() => []);
  await processMessage(primaryEntry.ctx, allMedia, storeAllowFrom);
};

// Schedule media group flush
const scheduleMediaGroupFlush = (entry: MediaGroupEntry) => {
  clearTimeout(entry.timer);
  entry.timer = setTimeout(async () => {
    mediaGroupBuffer.delete(entry.key);
    await processMediaGroup(entry);
  }, MEDIA_GROUP_TIMEOUT_MS);
};
```

### Text Fragment Handling

Sequential text messages are merged:

```typescript
const flushTextFragments = async (entry: TextFragmentEntry) => {
  // Sort by message ID
  entry.messages.sort((a, b) => a.msg.message_id - b.msg.message_id);
  
  const first = entry.messages[0];
  const last = entry.messages.at(-1);
  
  // Combine text
  const combinedText = entry.messages
    .map((m) => m.msg.text ?? "")
    .join("");
  
  if (!combinedText.trim()) {
    return;
  }
  
  // Create synthetic message
  const syntheticMessage: Message = {
    ...first.msg,
    text: combinedText,
    caption: undefined,
    entities: undefined,
    date: last.msg.date ?? first.msg.date,
  };
  
  // Process as single message
  await processMessage(
    { message: syntheticMessage, me: first.ctx.me, getFile: first.ctx.getFile },
    [],
    storeAllowFrom,
    { messageIdOverride: String(last.msg.message_id) }
  );
};
```

**Use Case**: When user sends multiple short messages in rapid succession, merge them before sending to agent.

### Callback Query Handler (Inline Buttons)

```typescript
bot.on("callback_query", async (ctx) => {
  const callback = ctx.callbackQuery;
  
  // Answer immediately to prevent Telegram from retrying
  await bot.api.answerCallbackQuery(callback.id).catch(() => {});
  
  const data = (callback.data ?? "").trim();
  const callbackMessage = callback.message;
  
  if (!data || !callbackMessage) {
    return;
  }
  
  // Parse callback data
  if (data.startsWith("model:")) {
    // Handle model selection button
    const parsed = parseModelCallbackData(data);
    await handleModelSelection(ctx, parsed);
  } else if (data.startsWith("cmd:")) {
    // Handle command button
    await handleCommandButton(ctx, data);
  }
});
```

---

## Message Dispatch System

### Overview

The Message Dispatcher (`src/telegram/bot-message-dispatch.ts`) routes messages to the agent and handles responses.

### Dispatch Flow

```typescript
export const dispatchTelegramMessage = async ({
  context,
  bot,
  cfg,
  runtime,
  replyToMode,
  streamMode,
  textLimit,
  telegramCfg,
  opts,
  resolveBotTopicsEnabled,
}: DispatchTelegramMessageParams) => {
  const {
    ctxPayload,
    primaryCtx,
    msg,
    chatId,
    isGroup,
    threadSpec,
    historyKey,
    historyLimit,
    groupHistories,
    route,
    skillFilter,
    sendTyping,
    sendRecordVoice,
    ackReactionPromise,
    reactionApi,
    removeAckAfterReply,
  } = context;
  
  // 1. Set up draft streaming (for private chats with topics)
  const isPrivateChat = msg.chat.type === "private";
  const draftThreadId = threadSpec.id;
  const canStreamDraft =
    streamMode !== "off" &&
    isPrivateChat &&
    typeof draftThreadId === "number" &&
    (await resolveBotTopicsEnabled(primaryCtx));
  
  const draftStream = canStreamDraft
    ? createTelegramDraftStream({
        api: bot.api,
        chatId,
        draftId: msg.message_id || Date.now(),
        maxChars: Math.min(textLimit, 4096),
        thread: threadSpec,
      })
    : undefined;
  
  // 2. Build reply prefix (shows model name)
  const { onModelSelected, ...prefixOptions } = createReplyPrefixOptions({
    cfg,
    agentId: route.agentId,
    channel: "telegram",
    accountId: route.accountId,
  });
  
  // 3. Set up typing indicators
  const typingCallbacks = createTypingCallbacks({
    send: sendTyping,
    clear: () => {},  // Telegram auto-clears typing
  });
  
  // 4. Dispatch to agent with buffered block streaming
  await dispatchReplyWithBufferedBlockDispatcher({
    cfg,
    agentId: route.agentId,
    context: ctxPayload,
    channel: "telegram",
    accountId: route.accountId,
    replyPrefixOptions: prefixOptions,
    tableMode: resolveMarkdownTableMode({ cfg, channel: "telegram", accountId: route.accountId }),
    chunkMode: resolveChunkMode(cfg, "telegram", route.accountId),
    typingCallbacks,
    onPartial: updateDraftFromPartial,
    onComplete: async (replies) => {
      // 5. Flush draft stream
      await flushDraft();
      
      // 6. Deliver responses to Telegram
      await deliverReplies({
        replies,
        bot,
        chatId,
        threadId: threadSpec.id,
        replyToMode,
        replyToMessageId: msg.message_id,
        historyKey,
        historyLimit,
        groupHistories,
      });
      
      // 7. Remove ack reaction
      if (removeAckAfterReply && reactionApi) {
        await removeAckReactionAfterReply(reactionApi);
      }
    },
  });
};
```

### Draft Streaming

Draft streaming shows partial responses in real-time:

```typescript
const createTelegramDraftStream = ({
  api,
  chatId,
  draftId,
  maxChars,
  thread,
}: CreateTelegramDraftStreamParams) => {
  let currentText = "";
  let lastUpdateMs = 0;
  const UPDATE_THROTTLE_MS = 500;  // Max 2 updates per second
  
  return {
    update: (text: string) => {
      if (text === currentText) {
        return;  // No change
      }
      
      const now = Date.now();
      if (now - lastUpdateMs < UPDATE_THROTTLE_MS) {
        return;  // Throttle updates
      }
      
      currentText = text.slice(0, maxChars);
      lastUpdateMs = now;
      
      // Edit draft message
      api.editMessageText(chatId, draftId, currentText, {
        message_thread_id: thread.id,
        parse_mode: "Markdown",
      }).catch(() => {});
    },
    
    flush: async () => {
      // Final update
      if (currentText) {
        await api.editMessageText(chatId, draftId, currentText, {
          message_thread_id: thread.id,
          parse_mode: "Markdown",
        }).catch(() => {});
      }
    },
  };
};
```

### Typing Indicators

```typescript
const sendTyping = async (ctx: TelegramContext, action: "typing" | "recording") => {
  const chatId = ctx.message.chat.id;
  const threadParams = buildTypingThreadParams(ctx);
  
  if (action === "recording") {
    await bot.api.sendChatAction(chatId, "record_voice", threadParams).catch(() => {});
  } else {
    await bot.api.sendChatAction(chatId, "typing", threadParams).catch(() => {});
  }
};
```

---

## Message Context Building

### Overview

The Message Context Builder (`src/telegram/bot-message-context.ts`) extracts all relevant information from a message for processing.

### Context Building Flow

```typescript
export const buildTelegramMessageContext = async ({
  primaryCtx,
  allMedia,
  storeAllowFrom,
  options,
  bot,
  cfg,
  account,
  historyLimit,
  groupHistories,
  dmPolicy,
  allowFrom,
  groupAllowFrom,
  ackReactionScope,
  logger,
  resolveGroupActivation,
  resolveGroupRequireMention,
  resolveTelegramGroupConfig,
}: BuildTelegramMessageContextParams) => {
  const msg = primaryCtx.message;
  
  // 1. Extract basic info
  const chatId = msg.chat.id;
  const isGroup = msg.chat.type === "group" || msg.chat.type === "supergroup";
  const messageThreadId = (msg as { message_thread_id?: number }).message_thread_id;
  const isForum = (msg.chat as { is_forum?: boolean }).is_forum === true;
  
  // 2. Resolve thread spec
  const threadSpec = resolveTelegramThreadSpec({
    isGroup,
    isForum,
    messageThreadId,
  });
  const resolvedThreadId = threadSpec.scope === "forum" ? threadSpec.id : undefined;
  
  // 3. Get group/topic config
  const { groupConfig, topicConfig } = resolveTelegramGroupConfig(chatId, resolvedThreadId);
  
  // 4. Build peer ID
  const peerId = isGroup 
    ? buildTelegramGroupPeerId(chatId, resolvedThreadId) 
    : String(chatId);
  const parentPeer = buildTelegramParentPeer({ isGroup, resolvedThreadId, chatId });
  
  // 5. Resolve routing
  const route = resolveAgentRoute({
    cfg: loadConfig(),
    channel: "telegram",
    accountId: account.accountId,
    peer: {
      kind: isGroup ? "group" : "direct",
      id: peerId,
    },
    parentPeer,
  });
  
  // 6. Build session key
  const baseSessionKey = route.sessionKey;
  const dmThreadId = threadSpec.scope === "dm" ? threadSpec.id : undefined;
  const threadKeys = dmThreadId != null
    ? resolveThreadSessionKeys({ baseSessionKey, threadId: String(dmThreadId) })
    : null;
  const sessionKey = threadKeys?.sessionKey ?? baseSessionKey;
  
  // 7. Check access control
  if (isGroup && groupConfig?.enabled === false) {
    logger.info({}, "Blocked telegram group (group disabled)");
    return null;
  }
  
  const effectiveDmAllow = normalizeAllowFromWithStore({ allowFrom, storeAllowFrom });
  const groupAllowOverride = firstDefined(topicConfig?.allowFrom, groupConfig?.allowFrom);
  const effectiveGroupAllow = normalizeAllowFromWithStore({
    allowFrom: groupAllowOverride ?? groupAllowFrom,
    storeAllowFrom,
  });
  
  // 8. Check sender authorization
  const senderId = msg.from?.id ? String(msg.from.id) : "";
  const senderUsername = msg.from?.username ?? "";
  
  if (!isGroup) {
    // Direct message: check DM allow list
    if (dmPolicy === "allowlist" && !isSenderAllowed({
      allow: effectiveDmAllow,
      senderId,
      senderUsername,
    })) {
      logger.info({ senderId, senderUsername }, "Blocked telegram DM (not in allowlist)");
      return null;
    }
  } else {
    // Group message: check group allow list
    if (!isSenderAllowed({
      allow: effectiveGroupAllow,
      senderId,
      senderUsername,
    })) {
      logger.info({ senderId, senderUsername }, "Blocked telegram group message (sender not allowed)");
      return null;
    }
  }
  
  // 9. Build message text
  const text = msg.text ?? msg.caption ?? "";
  const expandedText = expandTextLinks(text, msg.entities ?? []);
  
  // 10. Check mention requirements
  const mentionRegexes = buildMentionRegexes(cfg, route.agentId);
  const wasMentioned = options?.forceWasMentioned || 
    hasBotMention(msg, bot.botInfo.username) ||
    matchesMentionWithExplicit(expandedText, mentionRegexes);
  
  const requireMention = isGroup && resolveGroupRequireMention(chatId);
  if (requireMention && !wasMentioned) {
    logger.info({}, "Skipped telegram group message (mention required)");
    return null;
  }
  
  // 11. Build full context payload
  const ctxPayload = await finalizeInboundContext({
    cfg,
    agentId: route.agentId,
    sessionKey,
    text: expandedText,
    attachments: allMedia,
    envelope: formatInboundEnvelope({
      channel: "telegram",
      sender: buildSenderLabel(msg),
      chatName: buildGroupLabel(msg.chat),
      wasMentioned,
    }),
    historyKey: sessionKey,
    historyLimit,
    groupHistories,
  });
  
  // 12. Return complete context
  return {
    ctxPayload,
    primaryCtx,
    msg,
    chatId,
    isGroup,
    threadSpec,
    route,
    sessionKey,
    wasMentioned,
    sendTyping: () => sendTyping(primaryCtx, "typing"),
    sendRecordVoice: () => sendTyping(primaryCtx, "recording"),
  };
};
```

### Peer ID Building

```typescript
// Group peer ID includes thread ID for forum topics
export function buildTelegramGroupPeerId(
  chatId: string | number,
  resolvedThreadId?: number,
): string {
  const base = `tg:group:${chatId}`;
  return resolvedThreadId ? `${base}:${resolvedThreadId}` : base;
}

// Parent peer (for routing)
export function buildTelegramParentPeer(params: {
  isGroup: boolean;
  resolvedThreadId?: number;
  chatId: string | number;
}) {
  if (!params.isGroup || !params.resolvedThreadId) {
    return undefined;
  }
  return {
    kind: "group" as const,
    id: `tg:group:${params.chatId}`,
  };
}
```

### Thread Spec Resolution

```typescript
export function resolveTelegramThreadSpec(params: {
  isGroup: boolean;
  isForum: boolean;
  messageThreadId?: number;
}) {
  if (!params.isGroup) {
    // DM: use messageThreadId if present
    return params.messageThreadId
      ? { scope: "dm" as const, id: params.messageThreadId }
      : { scope: "dm" as const, id: undefined };
  }
  
  if (params.isForum && params.messageThreadId) {
    // Forum: use messageThreadId as topic ID
    return { scope: "forum" as const, id: params.messageThreadId };
  }
  
  // Regular group: no thread
  return { scope: "group" as const, id: undefined };
}
```

---

## Native Commands

### Overview

Native Commands (`src/telegram/bot-native-commands.ts`) handle built-in bot commands like `/start`, `/help`, `/models`, etc.

### Command Registration

```typescript
export const registerTelegramNativeCommands = ({
  bot,
  cfg,
  runtime,
  accountId,
  telegramCfg,
  allowFrom,
  groupAllowFrom,
  replyToMode,
  textLimit,
  useAccessGroups,
  nativeEnabled,
  nativeSkillsEnabled,
  nativeDisabledExplicit,
  resolveGroupPolicy,
  resolveTelegramGroupConfig,
  shouldSkipUpdate,
  opts,
}: RegisterTelegramNativeCommandsParams) => {
  if (!nativeEnabled) {
    return;
  }
  
  // List of native commands
  const commandSpecs = listNativeCommandSpecsForConfig(cfg);
  const customCommands = resolveTelegramCustomCommands(cfg, accountId);
  
  // Register each command
  for (const spec of commandSpecs) {
    const commandName = spec.nativeName ?? spec.name;
    
    bot.command(commandName, async (ctx) => {
      if (shouldSkipUpdate(ctx)) {
        return;
      }
      
      // Check authorization
      const authResult = await resolveTelegramCommandAuth({
        msg: ctx.message,
        bot,
        cfg,
        telegramCfg,
        allowFrom,
        groupAllowFrom,
        useAccessGroups,
        resolveGroupPolicy,
        resolveTelegramGroupConfig,
        requireAuth: spec.requireAuth !== false,
      });
      
      if (!authResult || !authResult.commandAuthorized) {
        return;
      }
      
      // Parse command arguments
      const commandText = ctx.match ?? "";
      const args = parseCommandArgs(commandText);
      
      // Execute command
      await executeCommand(ctx, spec, args);
    });
  }
};
```

### Command Authorization

```typescript
async function resolveTelegramCommandAuth(params: {
  msg: Message;
  bot: Bot;
  cfg: OpenClawConfig;
  telegramCfg: TelegramAccountConfig;
  allowFrom?: Array<string | number>;
  groupAllowFrom?: Array<string | number>;
  useAccessGroups: boolean;
  resolveGroupPolicy: (chatId: string | number) => ChannelGroupPolicy;
  resolveTelegramGroupConfig: (
    chatId: string | number,
    messageThreadId?: number,
  ) => { groupConfig?: TelegramGroupConfig; topicConfig?: TelegramTopicConfig };
  requireAuth: boolean;
}): Promise<TelegramCommandAuthResult | null> {
  const { msg, bot, cfg, requireAuth } = params;
  const chatId = msg.chat.id;
  const isGroup = msg.chat.type === "group" || msg.chat.type === "supergroup";
  const senderId = msg.from?.id ? String(msg.from.id) : "";
  const senderUsername = msg.from?.username ?? "";
  
  // Check group enabled
  const { groupConfig, topicConfig } = params.resolveTelegramGroupConfig(chatId);
  if (isGroup && groupConfig?.enabled === false) {
    await bot.api.sendMessage(chatId, "This group is disabled.");
    return null;
  }
  
  // Check sender in allow list
  if (requireAuth && isGroup) {
    const effectiveGroupAllow = normalizeAllowFromWithStore({
      allowFrom: groupConfig?.allowFrom ?? params.groupAllowFrom,
      storeAllowFrom: await readChannelAllowFromStore("telegram"),
    });
    
    if (!isSenderAllowed({
      allow: effectiveGroupAllow,
      senderId,
      senderUsername,
    })) {
      await bot.api.sendMessage(chatId, "You are not authorized to use this command.");
      return null;
    }
  }
  
  return {
    chatId,
    isGroup,
    senderId,
    senderUsername,
    groupConfig,
    topicConfig,
    commandAuthorized: true,
  };
}
```

### Built-in Commands

#### /start Command

```typescript
bot.command("start", async (ctx) => {
  const authResult = await resolveTelegramCommandAuth({...});
  if (!authResult) return;
  
  await ctx.reply(
    "Welcome! I'm an AI assistant. Send me a message to get started.",
    { parse_mode: "Markdown" }
  );
});
```

#### /help Command

```typescript
bot.command("help", async (ctx) => {
  const authResult = await resolveTelegramCommandAuth({...});
  if (!authResult) return;
  
  // List available commands
  const commandsList = [
    "/start - Start conversation",
    "/help - Show this help",
    "/models - List available models",
    "/clear - Clear conversation history",
  ].join("\n");
  
  await ctx.reply(`Available commands:\n\n${commandsList}`);
});
```

#### /models Command

```typescript
bot.command("models", async (ctx) => {
  const authResult = await resolveTelegramCommandAuth({...});
  if (!authResult) return;
  
  // Load model catalog
  const catalog = await loadModelCatalog({ config: cfg });
  
  // Build keyboard with model selection
  const keyboard = buildModelsKeyboard(catalog, 0);
  
  await ctx.reply(
    "Select a model:",
    {
      reply_markup: buildInlineKeyboard(keyboard),
    }
  );
});
```

---

## Account Management

### Overview

Account Management (`src/telegram/accounts.ts`) handles multiple Telegram bot accounts.

### Account Resolution

```typescript
export type ResolvedTelegramAccount = {
  accountId: string;
  enabled: boolean;
  name?: string;
  token: string;
  tokenSource: "env" | "tokenFile" | "config" | "none";
  config: TelegramAccountConfig;
};

export function resolveTelegramAccount(params: {
  cfg: OpenClawConfig;
  accountId?: string | null;
}): ResolvedTelegramAccount {
  const baseEnabled = params.cfg.channels?.telegram?.enabled !== false;
  
  const resolve = (accountId: string) => {
    // Merge base config with account-specific config
    const merged = mergeTelegramAccountConfig(params.cfg, accountId);
    const accountEnabled = merged.enabled !== false;
    const enabled = baseEnabled && accountEnabled;
    
    // Resolve token (env > tokenFile > config)
    const tokenResolution = resolveTelegramToken(params.cfg, { accountId });
    
    return {
      accountId,
      enabled,
      name: merged.name,
      token: tokenResolution.token,
      tokenSource: tokenResolution.source,
      config: merged,
    };
  };
  
  // Use explicit account ID or resolve default
  const accountId = params.accountId?.trim() || resolveDefaultTelegramAccountId(params.cfg);
  return resolve(accountId);
}
```

### Multi-Account Support

```typescript
export function listTelegramAccountIds(cfg: OpenClawConfig): string[] {
  // Combine configured accounts and bound accounts
  const ids = Array.from(
    new Set([
      ...listConfiguredAccountIds(cfg),
      ...listBoundAccountIds(cfg, "telegram"),
    ])
  );
  
  if (ids.length === 0) {
    return [DEFAULT_ACCOUNT_ID];
  }
  
  return ids.toSorted((a, b) => a.localeCompare(b));
}

function mergeTelegramAccountConfig(
  cfg: OpenClawConfig,
  accountId: string
): TelegramAccountConfig {
  // Base config (shared by all accounts)
  const { accounts: _ignored, ...base } = (cfg.channels?.telegram ?? {});
  
  // Account-specific config
  const account = resolveAccountConfig(cfg, accountId) ?? {};
  
  // Merge with account overriding base
  return { ...base, ...account };
}
```

---

## Access Control

### Overview

Access control determines who can interact with the bot.

### Allow List Pattern

```typescript
export function isSenderAllowed(params: {
  allow: Array<string | number>;
  senderId: string;
  senderUsername: string;
}): boolean {
  if (params.allow.length === 0) {
    return true;  // Empty allow list = allow all
  }
  
  for (const entry of params.allow) {
    if (typeof entry === "number") {
      // Numeric user ID
      if (String(entry) === params.senderId) {
        return true;
      }
    } else {
      // Username (with or without @)
      const normalized = entry.toLowerCase().replace(/^@/, "");
      if (normalized === params.senderUsername.toLowerCase()) {
        return true;
      }
      // Check for "tg:username" format
      if (entry.toLowerCase().startsWith("tg:")) {
        const username = entry.slice(3).toLowerCase();
        if (username === params.senderUsername.toLowerCase()) {
          return true;
        }
      }
    }
  }
  
  return false;
}
```

### Merge Allow Lists

```typescript
export function normalizeAllowFromWithStore(params: {
  allowFrom?: Array<string | number>;
  storeAllowFrom: string[];
}): Array<string | number> {
  const config = params.allowFrom ?? [];
  const store = params.storeAllowFrom ?? [];
  
  // Combine and deduplicate
  const merged = new Set<string | number>();
  
  for (const entry of config) {
    merged.add(entry);
  }
  
  for (const entry of store) {
    if (typeof entry === "string") {
      merged.add(entry);
    }
  }
  
  return Array.from(merged);
}
```

### Group-Specific Access Control

```typescript
// Resolve allow list with group/topic overrides
const groupAllowOverride = firstDefined(
  topicConfig?.allowFrom,   // Topic-specific
  groupConfig?.allowFrom    // Group-specific
);

const effectiveGroupAllow = normalizeAllowFromWithStore({
  allowFrom: groupAllowOverride ?? groupAllowFrom,  // Fallback to global
  storeAllowFrom,
});
```

---

## Media Handling

### Media Download

```typescript
export async function resolveMedia(
  ctx: TelegramContext,
  maxBytes: number,
  token: string,
  proxyFetch?: typeof fetch,
): Promise<{ path: string; contentType?: string; stickerMetadata?: StickerMetadata } | null> {
  const msg = ctx.message;
  
  // Determine media type
  let fileId: string | undefined;
  let contentType: string | undefined;
  let stickerMetadata: StickerMetadata | undefined;
  
  if (msg.photo) {
    // Photo: use largest size
    const photos = msg.photo.sort((a, b) => b.file_size ?? 0 - (a.file_size ?? 0));
    fileId = photos[0]?.file_id;
    contentType = "image/jpeg";
  } else if (msg.document) {
    fileId = msg.document.file_id;
    contentType = msg.document.mime_type;
  } else if (msg.video) {
    fileId = msg.video.file_id;
    contentType = "video/mp4";
  } else if (msg.audio) {
    fileId = msg.audio.file_id;
    contentType = msg.audio.mime_type;
  } else if (msg.voice) {
    fileId = msg.voice.file_id;
    contentType = "audio/ogg";
  } else if (msg.sticker) {
    fileId = msg.sticker.file_id;
    contentType = "image/webp";
    stickerMetadata = {
      emoji: msg.sticker.emoji,
      setName: msg.sticker.set_name,
      fileUniqueId: msg.sticker.file_unique_id,
    };
  }
  
  if (!fileId) {
    return null;
  }
  
  // Get file info
  const file = await ctx.getFile();
  if (!file.file_path) {
    return null;
  }
  
  // Check size limit
  if (file.file_size && file.file_size > maxBytes) {
    throw new Error(`Media file too large: ${file.file_size} bytes (max: ${maxBytes})`);
  }
  
  // Download file
  const url = `https://api.telegram.org/file/bot${token}/${file.file_path}`;
  const fetcher = proxyFetch ?? fetch;
  const response = await fetcher(url);
  
  if (!response.ok) {
    throw new Error(`Failed to download media: ${response.status}`);
  }
  
  // Save to temp file
  const tempPath = path.join(os.tmpdir(), `telegram-${fileId}`);
  const buffer = await response.arrayBuffer();
  await fs.writeFile(tempPath, Buffer.from(buffer));
  
  return {
    path: tempPath,
    contentType,
    stickerMetadata,
  };
}
```

### Media Group Detection

```typescript
// Messages with media_group_id should be batched
const mediaGroupId = (msg as { media_group_id?: string }).media_group_id;

if (mediaGroupId) {
  // Add to buffer
  let entry = mediaGroupBuffer.get(mediaGroupId);
  if (!entry) {
    entry = {
      key: mediaGroupId,
      messages: [],
      timer: null,
    };
    mediaGroupBuffer.set(mediaGroupId, entry);
  }
  
  entry.messages.push({ ctx, msg, receivedAtMs: Date.now() });
  
  // Schedule flush after 1 second of no new messages
  scheduleMediaGroupFlush(entry);
  return;
}
```

---

## Key Takeaways

### Architecture Insights

1. **Grammy Framework**: Modern TypeScript bot framework with good ergonomics
2. **Event-Driven**: React to updates, don't poll continuously
3. **Batching**: Media groups, text fragments, debouncing for efficiency
4. **Multi-Account**: Support multiple bot instances with shared config
5. **Access Control**: Multi-layer allow lists (global, group, topic)

### Critical Patterns

1. **Message Buffering**:
   - Media groups: 1 second timeout
   - Text fragments: 1.5 second gap threshold
   - Debouncing: Configurable delay (default 300ms)

2. **Context Building**:
   - Extract sender, chat, thread info
   - Check access control at multiple levels
   - Resolve routing to correct agent/session
   - Build history context

3. **Command Handling**:
   - Separate native commands from regular messages
   - Authorization checks before execution
   - Inline keyboards for interactive commands

4. **Streaming**:
   - Draft messages for real-time updates (private chats only)
   - Throttle updates (max 2/second)
   - Flush on completion

### Performance Considerations

1. **API Rate Limits**: Telegram has strict rate limits
2. **Debouncing**: Reduces API calls for rapid messages
3. **Media Download**: Async, with size limits
4. **Typing Indicators**: Auto-clear after 5 seconds

---

## Emonk Adaptations

### What to Keep

1. **Grammy Framework**: Excellent TypeScript bot library
2. **Access Control**: Allow list pattern for security
3. **Media Handling**: Download and attach to messages
4. **Typing Indicators**: UX improvement

### What to Simplify

1. **No Multi-Account**: Single bot instance
2. **No Text Fragments**: Simpler message handling
3. **No Draft Streaming**: Not needed for social media agent
4. **Simpler Routing**: No complex group/topic routing

### Emonk-Specific Implementation

#### 1. Bot Setup (Python with python-telegram-bot)

```python
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters

class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.app = Application.builder().token(token).build()
        
        # Register handlers
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_message
        ))
        self.app.add_handler(CommandHandler("start", self.handle_start))
        self.app.add_handler(CommandHandler("help", self.handle_help))
    
    async def handle_message(self, update: Update, context):
        """Handle incoming text message"""
        message = update.message
        chat_id = message.chat_id
        user_id = message.from_user.id
        text = message.text
        
        # Check access
        if not self.is_allowed(user_id):
            await message.reply_text("Access denied")
            return
        
        # Send typing indicator
        await context.bot.send_chat_action(chat_id, "typing")
        
        # Process message
        response = await self.process_message(text, chat_id, user_id)
        
        # Send response
        await message.reply_text(response, parse_mode="Markdown")
    
    async def handle_start(self, update: Update, context):
        """Handle /start command"""
        await update.message.reply_text(
            "Welcome! Send me a message to create social media content."
        )
    
    async def handle_help(self, update: Update, context):
        """Handle /help command"""
        help_text = """
Available commands:
/start - Start conversation
/help - Show this help
/generate - Generate a social media post
        """
        await update.message.reply_text(help_text)
    
    def is_allowed(self, user_id: int) -> bool:
        """Check if user is in allow list"""
        allowed_users = [123456789, 987654321]  # From config
        return user_id in allowed_users
    
    async def process_message(self, text: str, chat_id: int, user_id: int) -> str:
        """Process message with agent"""
        # Call agent via gateway
        response = await self.gateway_client.call("agent.chat", {
            "sessionKey": f"telegram:{chat_id}:{user_id}",
            "message": text,
        })
        return response.get("text", "No response")
    
    def start(self):
        """Start bot"""
        self.app.run_polling()
```

#### 2. Simplified Access Control

```python
class AccessControl:
    def __init__(self, config: dict):
        self.allowed_users = config.get("allowFrom", [])
    
    def is_allowed(self, user_id: int, username: str = None) -> bool:
        """Check if user is allowed"""
        if not self.allowed_users:
            return True  # Empty list = allow all
        
        # Check user ID
        if user_id in self.allowed_users:
            return True
        
        # Check username
        if username:
            username_lower = username.lower()
            for entry in self.allowed_users:
                if isinstance(entry, str):
                    entry_lower = entry.lower().lstrip("@")
                    if entry_lower == username_lower:
                        return True
        
        return False
```

#### 3. Media Download

```python
import os
import tempfile
from telegram import Update

async def download_media(update: Update, context) -> str | None:
    """Download media attachment and return file path"""
    message = update.message
    
    # Determine media type
    if message.photo:
        file = await message.photo[-1].get_file()  # Largest size
    elif message.document:
        file = await message.document.get_file()
    elif message.video:
        file = await message.video.get_file()
    else:
        return None
    
    # Check size limit (25MB)
    if file.file_size > 25 * 1024 * 1024:
        raise ValueError("File too large")
    
    # Download to temp file
    temp_path = os.path.join(tempfile.gettempdir(), f"telegram-{file.file_id}")
    await file.download_to_drive(temp_path)
    
    return temp_path
```

#### 4. Configuration

```yaml
# config.yaml
telegram:
  enabled: true
  token: "BOT_TOKEN_HERE"
  allowFrom:
    - 123456789       # User ID
    - "@username"     # Username
  replyTo: "always"   # Always quote original message
  parseMode: "Markdown"
```

### Key Implementation Priorities

1. **Phase 1**: Basic bot with message handling
2. **Phase 2**: Access control (allow list)
3. **Phase 3**: Media download
4. **Phase 4**: Typing indicators
5. **Phase 5**: Command handling

### Testing Strategy

1. **Unit Tests**: Access control, message parsing
2. **Integration Tests**: Full message flow with mock Telegram API
3. **Manual Tests**: Real Telegram bot with test account

---

## References

- OpenClaw Bot Handlers: `src/telegram/bot-handlers.ts`
- OpenClaw Message Dispatch: `src/telegram/bot-message-dispatch.ts`
- OpenClaw Message Context: `src/telegram/bot-message-context.ts`
- OpenClaw Native Commands: `src/telegram/bot-native-commands.ts`
- OpenClaw Account Management: `src/telegram/accounts.ts`

**Next Document**: [03_memory_system.md](03_memory_system.md)
