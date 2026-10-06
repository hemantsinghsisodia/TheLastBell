# THE LAST BELL — Decision Log

| ID | Date | Context | Decision | Alternatives | Reasoning | Implications |
|---|---|---|---|---|---|---|
| D-001 | 2026-10-06 | The project lived in OneDrive | Move the project to `C:\Hemant\Prj\Learning\TheLastBell`; keep the OneDrive copy as a backup | Keep it in OneDrive | OneDrive sync locks and uploads large generated folders, which corrupts or slows Unreal projects | Always open the project from the new path |
| D-002 | 2026-10-06 | No source control | Git with LFS for binary assets (`.uasset`, `.umap`, source art and audio) | Perforce, Git without LFS | Solo project; Git is already installed; LFS keeps the repo history small | Needs `git lfs` on any clone; a remote has to support LFS |
| D-003 | 2026-10-06 | No live editor access | Enable UE 5.8 `ModelContextProtocol` and `AllToolsets` (Editor only), auto-start server on port 8000 | Remote Control API, manual only | Built-in, officially supported, broad toolsets | Editor-only plugins don't affect packaged builds |
| D-004 | 2026-10-06 | Where planning docs go | `Docs/` folder; `CLAUDE.md` at the root | Repo root | Keeps the root clean | Agents reference `Docs/...` |
| D-005 | 2026-10-06 | C++ module timing | Add the `LastBell` module in Phase 1, not Phase 0 | Phase 0 | Phase 0 has no implementation; adding the module means compiling and is the first Phase 1 task | Phase 1 starts with CORE-001 |
| D-006 | 2026-10-06 | Global state | One `ULBWorldStateSubsystem` tag container is the progression source of truth | Per-system state, GameState actor | Tags are serializable, debuggable and decouple systems | All progression is expressed as `State.*` tags |
| D-007 | 2026-10-06 | AI framework | State Tree plus AI Perception; no BT or EQS initially | Behavior Tree, EQS, custom FSM | Fits a single enemy, is the modern UE path and the simplest that meets the design | Revisit EQS if search quality is poor |
| D-008 | 2026-10-06 | Escalation stages 1–2 | Scripted events and a silhouette actor, not AI | AI throughout | Full control of early reveals and cheaper | The AI pawn only exists from stage 3 |
| D-009 | 2026-10-06 | Inventory | No inventory; key items are world-state tags | Small inventory | Scope rule; no puzzle needs combining items | Revisit only if a puzzle requires it |
| D-010 | 2026-10-06 | Subagent models | Implementers: `model: sonnet`, `effort: high`. Reviewers: sonnet, read-only tools | Opus everywhere | Directive §1–2; keeps lead context for review | Lead must independently inspect agent output |
