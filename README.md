# BoneBET

CS2 match analysis API with statistical modeling and AI predictions.

## Features

- Fetches live and upcoming CS2 matches from CS2 Analytics API.
- Calculates True Win Rate weighted by opponent strength (HLTV ranking).
- Computes team Firepower based on individual player ratings.
- AI match analysis via Groq (Llama 3.3 70B) or OpenRouter.
- Redis caching with 5-hour TTL for fast repeated requests.
- Telegram bot integration with `/bet` command.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/bet` | Match predictions |

### Query Parameters for `/api/v1/bet`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 10 | Number of matches to analyze |
| `tier_filter` | string | `all` | `all` or `tier1` |
| `use_ai` | bool | `true` | Enable AI analysis |
| `force_refresh` | bool | `false` | Skip cache |

## Quick Start

### Docker

```bash
docker-compose up -d --build