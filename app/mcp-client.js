/**
 * MCPClient - Standalone MCP transport wrapper
 * 
 * Manages the connection to a remote MCP server (Streamable HTTP).
 * Handles: connect, lazy reconnect on failure, callTool, listTools, readResource.
 * 
 * No knowledge of SQL, LLMs, or the DOM — pure transport.
 */

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';

export class MCPClient {
    constructor(serverUrl, headers = {}) {
        this.serverUrl = serverUrl;
        this.headers = headers;
        this.client = null;
        this.connected = false;
        this.tools = [];
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 3;
        // The attempt budget caps a single burst of failures, but it must not
        // latch forever — after this much quiet time, the next attempt gets a
        // fresh budget so a transient outage can't permanently disable MCP.
        this.reconnectResetMs = 30000;
        this.lastReconnectTime = 0;
        this._connectPromise = null;
        this._onReconnect = null;
        // StreamableHTTP sessions are invalidated server-side after an idle
        // timeout. Track when we last connected and rebuild the client when
        // the session exceeds a conservative max age, instead of trusting a
        // stale `connected` flag on long-lived pages.
        this.sessionMaxAgeMs = 5 * 60 * 1000;
        this._lastConnectedAt = 0;
    }

    /**
     * Register a callback that fires after a successful reconnect (not on
     * initial connect). Receives the freshly-listed tools array so the
     * consumer can refresh its registry.
     *
     * @param {(tools: Array) => void | Promise<void>} cb
     */
    setOnReconnect(cb) {
        this._onReconnect = cb;
    }

    /**
     * Connect to the MCP server. Safe to call multiple times.
     */
    async connect() {
        if (this.connected && this.client) return;

        // Deduplicate parallel connect calls
        if (this._connectPromise) return this._connectPromise;
        this._connectPromise = this._doConnect();
        try {
            await this._connectPromise;
        } finally {
            this._connectPromise = null;
        }
    }

    async _doConnect() {
        try {
            console.log('[MCP] Auth header present:', !!this.headers['Authorization'], 'URL:', this.serverUrl);
            const transport = new StreamableHTTPClientTransport(new URL(this.serverUrl), {
                requestInit: { headers: this.headers }
            });
            this.client = new Client(
                { name: 'geo-chat-client', version: '2.0.0' },
                { capabilities: {} }
            );
            await this.client.connect(transport);

            // Cache available tools BEFORE flipping `connected`. The flag is the
            // short-circuit for connect()/ensureConnected(); if it went true here
            // (transport up) but the tool list were still empty, a concurrent
            // connect() would short-circuit and a getTools() reader would see []
            // — registering zero remote tools with no error, no fallback, and no
            // reconnect to recover (the silent MCP-tools-missing boot). Populate
            // the cache first so `connected === true` always implies tools ready.
            const response = await this.client.listTools();
            this.tools = response.tools || [];
            this.connected = true;
            this.reconnectAttempts = 0;
            this._lastConnectedAt = Date.now();
            console.log('[MCP] Connected. Tools:', this.tools.map(t => t.name));
        } catch (error) {
            this.connected = false;
            this.client = null;
            console.error('[MCP] Connection failed:', error.message);
            throw error;
        }
    }

    /**
     * Ensure connection is alive; reconnect if needed.
     * Called lazily before any operation.
     */
    async ensureConnected() {
        // Trust the `connected` flag rather than probing with a listTools()
        // round trip on every operation — that probe added a full request to
        // each callTool/listPrompts/getPrompt, multiplying boot latency. A
        // genuinely stale connection is caught by callTool's reconnect-and-retry
        // branch (the only frequent, long-lived op); boot-time prompt reads run
        // right after a fresh connect, so they're never stale.
        //
        // However, on a long-lived page a StreamableHTTP session can be
        // invalidated server-side after an idle timeout while the local
        // `connected` flag stays true. Detect that staleness here and rebuild
        // the client proactively so the next call starts on a fresh session
        // instead of throwing.
        if (this.connected && this.client) {
            const stale = this._lastConnectedAt > 0 && (Date.now() - this._lastConnectedAt) > this.sessionMaxAgeMs;
            if (!stale) return;
            console.warn('[MCP] Session idle-exceeded, rebuilding connection...');
            this.connected = false;
            try { await this.client.close(); } catch { /* ignore */ }
            this.client = null;
        }
        await this.reconnect();
    }

    /**
     * Reconnect with exponential backoff.
     */
    async reconnect() {
        const now = Date.now();
        // A fresh attempt after a quiet period gets a clean budget. Rapid
        // retries within one burst still hit the cap (no hammering), but a
        // user action after the outage clears retries instead of failing.
        if (now - this.lastReconnectTime > this.reconnectResetMs) {
            this.reconnectAttempts = 0;
        }
        this.lastReconnectTime = now;

        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            // Budget exhausted within a burst. Rather than failing hard (which
            // latches a long-lived page into "unavailable" until the quiet
            // window passes), wait longer and try again — a transient server
            // hiccup usually clears. The delay grows so we don't hammer.
            const backoff = Math.min(this.reconnectAttempts * 3000, 15000);
            console.warn(`[MCP] Reconnect budget exhausted; backing off ${backoff}ms and retrying...`);
            await new Promise(r => setTimeout(r, backoff));
            this.reconnectAttempts = 0;
        }

        this.reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 5000);
        console.log(`[MCP] Reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} (delay: ${delay}ms)...`);

        // Close stale client
        if (this.client) {
            try { await this.client.close(); } catch { /* ignore */ }
            this.client = null;
        }

        await new Promise(r => setTimeout(r, delay));
        await this.connect();

        if (this._onReconnect) {
            try {
                await this._onReconnect(this.tools);
            } catch (err) {
                console.warn('[MCP] onReconnect callback threw:', err.message);
            }
        }
    }

    /**
     * Get the list of tools from the MCP server (synchronous, from cache).
     * @returns {Array} Tool definitions with name, description, inputSchema
     */
    getTools() {
        return this.tools;
    }

    /**
     * Fetch the list of tools from the MCP server (async).
     * Ensures connection and refreshes cache.
     * @returns {Promise<Array>} Tool definitions
     */
    async listTools() {
        await this.ensureConnected();
        const response = await this.client.listTools();
        this.tools = response.tools || [];
        return this.tools;
    }

    /**
     * Call an MCP tool by name with arguments.
     * Handles reconnection transparently.
     * 
     * @param {string} name - Tool name (e.g., 'query')
     * @param {Object} args - Tool arguments (e.g., { sql_query: '...' })
     * @returns {string} Text result from the tool
     */
    async callTool(name, args) {
        await this.ensureConnected();

        try {
            const result = await this.client.callTool({ name, arguments: args }, undefined, { timeout: 600000 });
            this.reconnectAttempts = 0;

            if (result.content && result.content.length > 0) {
                const text = result.content[0].text;
                if (!text || text.trim() === '') {
                    return 'Query executed successfully but returned no data.';
                }
                return text;
            }

            throw new Error('No content in MCP response');
        } catch (error) {
            // If it's a connection error, try once more after reconnect.
            // We widen the match beyond plain network errors: a long-lived
            // StreamableHTTP session can be invalidated server-side (timeout /
            // restart), after which the SDK throws protocol-level errors that
            // don't mention fetch/network. Any exception here is almost always
            // transport/session related (business errors arrive as normal
            // results), so reconnect-and-retry once before giving up.
            const isConnectionError =
                error.name === 'TypeError' ||
                error.message?.includes('fetch') ||
                error.message?.includes('network') ||
                error.message?.includes('timeout') ||
                error.message?.includes('session') ||
                error.message?.includes('Bad Request') ||
                error.message?.includes('Unauthorized') ||
                /MCP|McpError|Protocol|streamable/i.test(error.message || '');

            if (isConnectionError) {
                console.warn('[MCP] Connection error during callTool, reconnecting...', error.message);
                this.connected = false;
                this.client = null;
                this.reconnectAttempts = 0;
                await this.ensureConnected();
                // Retry once
                const result = await this.client.callTool({ name, arguments: args }, undefined, { timeout: 600000 });
                if (result.content?.[0]?.text) return result.content[0].text;
                throw new Error('No content in MCP response after retry');
            }

            throw error;
        }
    }

    /**
     * Read an MCP resource by URI.
     * @param {string} uri - Resource URI (e.g., 'catalog://list')
     * @returns {string} Resource content
     */
    async readResource(uri) {
        await this.ensureConnected();
        const result = await this.client.readResource({ uri });
        return result?.contents?.[0]?.text || '';
    }

    /**
     * List available MCP resources.
     * @returns {Array} Resource definitions
     */
    async listResources() {
        await this.ensureConnected();
        const result = await this.client.listResources();
        return result?.resources || [];
    }

    /**
     * List available MCP prompts.
     * @returns {Array} Prompt definitions
     */
    async listPrompts() {
        await this.ensureConnected();
        const result = await this.client.listPrompts();
        return result?.prompts || [];
    }

    /**
     * Get an MCP prompt by name.
     * @param {string} name - Prompt name (e.g., 'geospatial-analyst')
     * @param {Object} [args] - Optional prompt arguments
     * @returns {string} Prompt content (concatenated message text)
     */
    async getPrompt(name, args = {}) {
        await this.ensureConnected();
        const result = await this.client.getPrompt({ name, arguments: args });
        const messages = result?.messages || [];
        return messages.map(m => m.content?.text || '').join('\n\n');
    }

    /**
     * Disconnect and clean up.
     */
    async disconnect() {
        if (this.client) {
            try { await this.client.close(); } catch { /* ignore */ }
        }
        this.client = null;
        this.connected = false;
    }

    /**
     * Check if currently connected.
     */
    get isConnected() {
        return this.connected;
    }
}
