# SCREEN-KERNEL/1.2

Family spec (host): https://github.com/ItsNotAILABS/pocket/blob/main/docs/POCKET_SCREEN_FAMILY_PROTOCOL.md

Live: `GET /v1/protocols/screen-kernel` · `GET /v1/protocols/stream` · `GET /v1/protocols/screen-body`

```
see → touch → type → click
nx, ny ∈ [0, 1] of the visible frame
```

## Objects

| Schema | Meaning |
|--------|---------|
| `pocket.screen.kernel.v1` | This protocol |
| `pocket.agent.arch.v1` | Agent turn plane that *uses* the kernel |
| `pocket.node.view.v1` | TV / phone / glasses seat |

## HTTP (host)

```
GET  /v1/screen/kernel
POST /v1/screen/see     { which: desktop|tv|anti, max_w?, region?: {nx, ny, nw, nh} }
POST /v1/screen/touch   { kind, nx, ny, target, hwnd? }
POST /v1/screen/type    { text, nx, ny, click_first, submit }
POST /v1/screen/click   { name }
POST /v1/vcomp/open     agent personal laptop (pro seat)
GET  /v1/vcomp          status, tier=pro, latest memory
POST /v1/vcomp/sense    fusion perception; a new brief is remembered
POST /v1/vcomp/act      { action: see|tap|type_into|click_name|scroll }
POST /v1/vcomp/shell    { command }
POST /v1/vcomp/term     terminal
POST /v1/vcomp/memory   { text, kind, tags }   remember
GET  /v1/vcomp/memory   ?q=&limit=             recall
POST /v1/vcomp/close
POST /v1/screen/embody  { agent, which }
POST /v1/screen/body    { verb, nx, ny, text, name }
WS   /v1/phoneai/portal/ws   pocket.stream.v1  (JSON envelope then JPEG)
```

`kind` for touch: `hover` | `tap` | `hold` | `down` | `up` | `drag` | `scroll` | `right` | `key`.

## Rules

1. The green cursor is the real mouse. Hover moves it; tap clicks there.
2. Type always targets the field last selected (`nx,ny`), not a hidden window.
3. Named click is UI Automation / accessibility name, not OCR-only.
4. TV → phone streams the TV display (second monitor or TV snapshot). Phone taps that screen.
5. Agents do not get extra chrome. They call the same verbs, or **inhabit** the screen (`embody`) so see/touch/type *are* their body.
6. Tunnel hostname is not authority. LAN, signed-in, device-pair+passkey, or a bound session cookie.
7. Stream frames are `pocket.stream.v1`: a JSON envelope `{seq, geom, matrix}` then a binary JPEG. The 3×3 matrix maps `nx,ny` of the contained image onto desktop pixels. `see` returns that same matrix, plus `jpeg_b64` (also mirrored as `base64`) and `frame` `{w, h}`. A region zooms that rectangle to `max_w`. `nx` or `ny` outside 0..1 is refused.

## Hardware `vlaptop.hardware.v1`

The standalone host boots one machine on every operating system.

| Device | Kind | Behavior |
|--------|------|----------|
| display | framebuffer | 320×184 RGB, JPEG from `see` with `which=machine` |
| pointer | pointer | `touch` moves it and focuses the control under it |
| keyboard | keyboard | `type` writes the focused field |
| console | shell | `Run`, `POST /v1/vcomp/shell`, and `type` with `submit` run on this computer |

`which=desktop` uses the physical Windows monitor when the host is Windows. Every other device uses the framebuffer, so the picture and the controls stay the same. `GET /v1/screen/hardware` and `GET /v1/screen/kernel` both carry the hardware object. `click` on the framebuffer returns `match`, `role`, and `rect`.
