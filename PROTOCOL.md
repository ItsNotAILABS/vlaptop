# SCREEN-KERNEL/1.0

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
POST /v1/screen/see     { which: desktop|tv|anti }
POST /v1/screen/touch   { kind, nx, ny, target, hwnd? }
POST /v1/screen/type    { text, nx, ny, click_first, submit }
POST /v1/screen/click   { name }
POST /v1/vcomp/open     agent personal laptop
POST /v1/vcomp/act      { action: see|tap|type_into|click_name }
```

`kind` for touch: `hover` | `tap` | `hold` | `down` | `up` | `drag` | `scroll` | `right` | `key`.

## Rules

1. The green cursor is the real mouse. Hover moves it; tap clicks there.
2. Type always targets the field last selected (`nx,ny`), not a hidden window.
3. Named click is UI Automation / accessibility name, not OCR-only.
4. TV → phone streams the TV display (second monitor or TV snapshot). Phone taps that screen.
5. Agents do not get extra chrome. They call the same verbs.
6. Tunnel hostname is not authority. LAN, signed-in, or a bound session cookie.
