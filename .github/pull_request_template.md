## Summary

## Protocol Compatibility Checklist

- [ ] Version, ruleset, and descriptor metadata are updated when wire contracts change.
- [ ] Generated descriptor, Go manifest, and C++ manifest are regenerated.
- [ ] Client-authored inputs do not gain authoritative result, reward, hit, graze, or boss HP fields.
- [ ] Battle ticket, input, snapshot, event, replay, and result fields remain auditable.
- [ ] `tools/check_protocol.py` was run locally or is covered by CI.
