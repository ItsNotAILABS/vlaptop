# vLaptop

**See. Touch. Type. Click the button.**  
A screen kernel for people and for agents.

vLaptop is the public protocol and SDK. The host that actually owns a laptop (POCKET) implements it. Agents get a personal computer seat. Humans get a phone, glasses, or TV that is the same verbs.

[![GitHub](https://img.shields.io/badge/org-ItsNotAILABS-00ff86)](https://github.com/ItsNotAILABS)
Protocol: `SCREEN-KERNEL/1.0`

## Verbs

| Verb | What it does | People | Agents |
|------|----------------|--------|--------|
| **see** | JPEG of a screen (laptop, TV, a window) | Phone / glasses / TV | `POST /v1/screen/see` |
| **touch** | Tap, hold, drag, scroll at `nx,ny` in 0..1 | Green cursor is the real mouse | `POST /v1/screen/touch` |
| **type** | Click the field you selected, then type | Small box on the phone | `POST /v1/screen/type` |
| **click** | Press a named on-screen button | HUD chrome | `POST /v1/screen/click` |
| **cursor** | Where the mouse actually is | Green circle | `GET /v1/screen/kernel` |

Coordinates are always **0..1 of the pixels you see**. Not of the last window tab.

## Why this is its own repo

POCKET is the operator OS. PhoneAI is the phone kernel. **vLaptop is the screen contract** — so a developer can:

1. Drive a real PC from a phone or glasses.
2. Give an agent a personal laptop (workspace + terminals + see/touch/type).
3. Ship a product that is not locked to one chat UI.

Host implementation lives in POCKET (`pocket.screen_kernel`). This repo is the spec + Python client.

## Quick start

```python
from vlaptop import Screen

pc = Screen("http://127.0.0.1:8787")
pc.see()                          # JPEG of the laptop
pc.touch("tap", nx=0.42, ny=0.31) # exact mouse
pc.type("search this", nx=0.5, ny=0.12, submit=True)
pc.click("Deploy")
```

Auth: same-origin cookie, LAN, or a Pocket session. Hostname is not authority.

## Product seats

- **Human** — PhoneAI Portal, TV → phone, Meta glasses HUD
- **Agent** — vLaptop (`POST /v1/vcomp/open`) plus the same kernel
- **TV** — watch the TV on the phone; taps control that display

## License

MIT. Inventor: Alfredo Medina / ItsNotAI Labs.
