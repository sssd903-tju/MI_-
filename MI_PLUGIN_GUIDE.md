# MI Plugin Integration Guide

This project is now designed as a pluggable MI game paradigm.

## Goal

Game side only handles:

- websocket connection
- MI packet parsing
- state machine (charge/jump)

Signal processing and model inference stay in your MetaBCI project.

## Connection

- Offline input websocket: `ws://127.0.0.1:8766`
- Online input websocket: `ws://127.0.0.1:8767`

You can override URLs via settings file `user://settings.json` keys:

- `mi_offline_ws_url`
- `mi_online_ws_url`

## Packet protocol

The game accepts flexible packet schemas.

### Sequence fields (any one)

- `seq`
- `sequence`
- `id`

### Timestamp fields (any one)

- `timestamp_ms`
- `ts_ms`
- `timestamp`
- `ts`
- `time`

If timestamp is in seconds, game auto converts to milliseconds.

### Label fields (any one)

- `label`
- `mi_label`
- `command`
- `state`

Accepted semantic labels after normalization:

- `hand`
- `foot`
- `rest`

Alias mapping included:

- hand: `right_hand`, `right`, `rh`
- foot: `feet`, `left_hand`, `left`, `lh`
- rest: `idle`, `none`, `neutral`

### Class id fallback

If no label field exists, game checks class id fields:

- `class_id`
- `label_id`
- `class`

Class id mapping defaults to:

- `0 -> rest`
- `1 -> hand`
- `2 -> foot`

Override in `user://settings.json`:

- `mi_class_id_to_label`

Example:

```json
{
  "mi_class_id_to_label": {
    "0": "rest",
    "1": "hand",
    "2": "foot"
  }
}
```

### Confidence fields (any one)

- `confidence`
- `conf`
- `prob`
- `score`

Value is clamped to `[0, 1]`.

## Minimal packet example

```json
{
  "seq": 128,
  "timestamp_ms": 1760000123456,
  "label": "hand",
  "confidence": 0.87
}
```

## Notes

- Keep packet frequency stable (for example 10 Hz).
- Keep clock source consistent to avoid stale packet drops.
- If your sender restarts and `seq` resets to `1`, game handles it.
