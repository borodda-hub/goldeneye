# Goldeneye Web

Next.js 14 App Router frontend for the Goldeneye research terminal.

## Dev loop

```
pnpm dev        # starts Next.js on :3000
pnpm typecheck  # tsc --noEmit
pnpm lint       # biome check .
pnpm test       # vitest run
```

## Contracts

After any backend model change, regenerate TypeScript types:

```
# With backend running on :8000:
pnpm contracts:gen

# Offline (uses vendored openapi.json):
pnpm contracts:gen:local
```

## Environment

Copy `.env.example` to `.env.local` and set:

```
NEXT_PUBLIC_API_BASE=http://localhost:8000
NEXT_PUBLIC_WS_BASE=ws://localhost:8000
```
