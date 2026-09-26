# Eyeball capabilities

`capabilities.py` is the profile-scoped boundary between conversation and external
evidence. Eyeball is assigned only `public_world_lookup`; protected capabilities
are denied. Capability implementations are trusted server code, receive a bounded
text request, and return bounded `CapabilityResult` evidence from public HTTPS
sources. The model cannot supply a URL or command for the registry to execute.

Retrieved content is untrusted data. It cannot become OES policy, a verified OES
corporate fact, a permission, tool authority, private data, or evidence that an
action occurred. Generated public-evidence answers are buffered and checked at the
hard authority boundary before release.

The public lookup implementation uses Tavily's supported Python SDK with the fixed
`https://api.tavily.com` service root. Production authentication comes only from the
server-side `TAVILY_API_KEY` environment variable. Missing credentials fail closed.
Each request sends only a bounded query derived from the current user turn; conversation
history, system prompts, browser context, and OES context never leave OES for Tavily.
