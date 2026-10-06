# vLaptop

**See. Touch. Type. Click the button.**  
A screen kernel for people and for agents.

vLaptop is a standalone screen system. `python -m vlaptop` serves SCREEN-KERNEL on `127.0.0.1:8788` and drives this desktop. Pocket can host the same contract. The client talks to either one.

[![GitHub](https://img.shields.io/badge/org-ItsNotAILABS-00ff86)](https://github.com/ItsNotAILABS)
Protocol: `SCREEN-KERNEL/1.2` · stream `pocket.stream.v1` · seat `pro`

## Verbs

| Verb | What it does | People | Agents |
|------|----------------|--------|--------|
| **see** | JPEG of a screen (laptop, TV, a window) | Phone / glasses / TV | `POST /v1/screen/see` |
| **touch** | Tap, hold, drag, scroll at `nx,ny` in 0..1 | Green cursor is the real mouse | `POST /v1/screen/touch` |
| **type** | Click the field you selected, then type | Small box on the phone | `POST /v1/screen/type` |
| **click** | Press a named on-screen button | HUD chrome | `POST /v1/screen/click` |
| **cursor** | Where the mouse actually is | Green circle | `GET /v1/screen/kernel` |
| **embody** | Agent *is* the pointer on that screen | Phone is a human body | `POST /v1/screen/embody` |

Coordinates are always **0..1 of the pixels you see**. Not of the last window tab. `see(nx, ny, nw, nh)` zooms that region. The reply includes the JPEG bytes and the 3×3 matrix from the spec. Values outside 0..1 are refused.

## Why this is its own repo

POCKET is the operator OS. PhoneAI is the phone kernel. **vLaptop is the screen contract** — so a developer can:

1. Drive a real PC from a phone or glasses.
2. Give an agent a personal laptop (workspace + terminals + see/touch/type).
3. Ship a product that is not locked to one chat UI.

This repo is the spec, the client, and the standalone host (`vlaptop.host`). Pocket’s `screen_kernel` is a second host.

## Quick start

```powershell
python -m vlaptop
```

That listens on `127.0.0.1:8788`. Point the client at it, or at Pocket on `8787`.

```python
from vlaptop import Screen

screen = Screen("http://127.0.0.1:8788")
frame = screen.see(nx=0.25, ny=0.25, nw=0.5, nh=0.5)
open("frame.jpg", "wb").write(frame["jpeg"])
```

```python
from vlaptop import Laptop

pc = Laptop("http://127.0.0.1:8787")
pc.boot("main")                   # pro virtual computer, Pocket host
pc.see()                          # JPEG of the laptop
pc.touch("tap", nx=0.42, ny=0.31) # exact mouse
pc.type("search this", nx=0.5, ny=0.12, submit=True)
pc.click("Deploy")
pc.sense()                        # fusion symbols; the brief is stored
pc.remember("Deploy is the ship button")
pc.recall("deploy")
pc.embody("coder")                # this agent wears the live PC
pc.body("see")
```

Auth: same-origin cookie, LAN, or a Pocket session. Hostname is not authority.

## Product seats

- **Human** — PhoneAI Portal, TV → phone, Meta glasses HUD
- **Agent** — vLaptop (`POST /v1/vcomp/open`) plus the same kernel
- **TV** — watch the TV on the phone; taps control that display

## License

MIT. Inventor: Alfredo Medina / ItsNotAI Labs.
