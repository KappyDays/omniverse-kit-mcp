# Stage Annotator — Manual QA Checklist

## Activation

- [ ] `Window → Extensions` lists "Stage Annotator" v0.1.0.
- [ ] Toggle on → "Stage Annotator" window appears.
- [ ] Toggle off → window disappears, no zombie warnings, the
      `/Annotations` scope keeps its existing pins (data preservation).

## CRUD

- [ ] Selecting a prim and pressing **+ New for Selection** creates a
      new card and a red pin sphere in the viewport.
- [ ] Title / body edits persist after focus loss; verifying via
      **Refresh** shows the saved values.
- [ ] Status combo cycle through all four states updates the pin colour
      immediately (Red → Amber → Green → Grey).
- [ ] Reply add → appears in thread with `[author]` + relative time.
- [ ] Reply delete (`x`) removes the entry without reordering siblings.
- [ ] Note delete removes both the card and the sphere pin.

## Filtering

- [ ] **Status: All** shows every note; switching to a single status
      narrows the list.
- [ ] **Search** field substring-matches title / body / prim path.
- [ ] Empty filter results show the "(no notes match…)" placeholder.

## Persistence

- [ ] Save USD → reopen → notes still listed with correct status,
      title, body, replies, author, timestamps.
- [ ] **Export JSON** writes a file under
      `~/.stage_annotator_exports/`. The JSON parses; `notes` array has
      one entry per visible card.

## Pin positioning

- [ ] Note on a Mesh prim → pin sits above the mesh bbox.
- [ ] Note on an Xform with no children → pin uses the xform's
      translate fallback (does not throw).
- [ ] Note on a SkelRoot character → pin sits above the head, not the
      origin.

## Cross-app

- [ ] USD Composer 2026.x: full feature set works.
- [ ] Isaac Sim 5.1: full feature set works (validation_api unaffected).

## Self-test (programmatic)

```
extension_activate(omni.mycompany.stage_annotator, reload=False)
# wait ~2 s
stage_assert_prim_exists(/Annotator/SelfTestResult)
stage_assert_property(
    /Annotator/SelfTestResult.crud_ok,   equals true
)
stage_assert_property(
    /Annotator/SelfTestResult.pin_ok,    equals true
)
stage_assert_property(
    /Annotator/SelfTestResult.export_ok, equals true
)
```
