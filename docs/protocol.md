# Ditoo Pro serial protocol, as observed

Sources: Divoom's ShowDoc API docs (`docin.divoom-gz.com`, POST
`api/page/info` with `page_id`), the futpib `divoom-ditoo-pro-controller` and
`hass-divoom` projects, and testing against a real Ditoo Pro. Anything marked
*unconfirmed* was sent but its effect couldn't be observed.

## Transport

RFCOMM **channel 2** (the Serial Port record in SDP). Channel 1 is HFP.

## Framing

```
0x01 | len LE16 | cmd | args… | checksum LE16 | 0x02
```

`len` = len(args) + 3. The checksum is the sum of every byte from `len` through
the last arg. No byte escaping is needed on this model.

Replies: `01 len 04 cmd 55 data… csum 02`. A raw `0x01` can appear inside a
payload, so a parser has to check that the candidate frame ends in `0x02` with
`0x04` in the type position before trusting it.

## Commands used

| Cmd | Args | Effect |
| --- | --- | --- |
| `0x44` | `00 0A 0A 04` + frame | Show a still image |
| `0x49` | total LE16, chunk index, ≤200 bytes | Show an animation, sent in chunks |
| `0x45` | view, … | Set view: 0 clock, 1 light, 3 VJ effect n, 4 music EQ n, 5 user-define (gallery). Clock: `00 24h style 01 0 0 0 R G B`; light: `01 R G B brightness effect power 0 0 0` |
| `0x46` | | Get view |
| `0x74` | 0–100 | Brightness |
| `0x18` | yy, cc, mm, dd, h, m, s, weekday | Set date and time |
| `0x2d` | 0/1 | 12/24-hour clock |
| `0x8c` | see below | Save frames into a user-define slot |
| `0xbd 0x17` | slot | Show user-define slot |
| `0xbd 0x16` | slot | Clear user-define page, stock pictures included |
| `0x52` | on, total LE16, chunk index, ≤200 bytes | Boot animation, chunked like `0x49` with an on/off byte in front |
| `0x8a` | `01` channel | Power-on channel: 0 clock, 1 light, 2 cloud, 3 VJ, 4 EQ, 5 gallery (`00` reads it) |
| `0xbd 0x15` | | Get user-define cycle time (reports 30 s) |
| `0x8e` | slot | Get user-define info: no useful reply from this firmware |

## Frame encoding

```
0xAA | len LE16 (= 7 + colours×3 + pixel bytes) | time LE16 (ms) | 0x00 |
colour count | palette RGB… | pixel indices, packed LSB-first
```

Bits per index = ceil(log2(colour count)), minimum 1. Up to 60 frames is safe.

## Saving to the speaker's memory (`0x8c`)

1. `0x8c 00 | size LE32 | slot`: start. The speaker replies with an `0xb1` ack
   and an `0x8c [1, 0, 0]` meaning "send from chunk 0".
2. `0x8c 01 | size LE32 | chunk index LE16 | ≤256 bytes` for every chunk of the
   concatenated frames. The speaker may ask for a chunk again with
   `0x8c [1, idx LE16]`.
3. `0x8c 02`: end.

Then `0x45 05` and `0xbd 17 slot` to show it. Stored art survives power-off.

A "slot" is really a gallery page holding a list of files: each upload to the
same index adds a file, and the page cycles through them (30 s each by default,
`0xbd 0x15`). Open a single connection for a batch of uploads; reconnecting
immediately after closing fails with EBUSY.
