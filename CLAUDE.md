# The Last Bell — project rules

First-person atmospheric survival horror, UE 5.8.3, C++ + Blueprint hybrid. 20–30 minutes of polished gameplay.

## Non-negotiable process
- Work **phase by phase** (see `Docs/IMPLEMENTATION_PLAN.md`). **Never start the next phase without explicit user approval.** Silence, passing tests and subagent success are not approval.
- Each phase ends with the "PHASE X READY FOR YOUR REVIEW" report and then stops.
- Never claim something works, is fixed or is tested unless it was actually validated. Say what needs human testing.
- No scope expansion (firearms, combat, inventory, multiplayer, extra monsters, etc.) without approval.

## Where things are
- Design docs: `Docs/` (TECHNICAL_DESIGN is the architecture source of truth; DECISIONS and RISKS are logs).
- Agents: `.claude/agents/`. The lead (Opus) plans, delegates, reviews and approves; Sonnet agents implement.
- C++: `Source/LastBell/` (prefix `LB`). Content: `Content/LastBell/` — never dump assets in the Content root.
- Raw downloads: `ExternalAssets/Incoming/` (git-ignored). Every external asset goes in `Docs/ASSET_REGISTRY.md`.

## Engineering rules
- Never edit `.uasset` or `.umap` binaries outside Unreal. Use the editor or MCP only.
- Unreal MCP (`unreal-mcp`, http://127.0.0.1:8000/mcp): check every tool result; serialize mutations to the same asset.
- Compile after C++ changes, compile the affected Blueprints, validate materials, and check the logs. Don't pile up unvalidated work.
- Composition over inheritance; subsystems over manager actors; Gameplay Tags for state; no hard asset refs in C++.
- Architecture drift: if the implementation differs from TECHNICAL_DESIGN, either fix the code or update TECHNICAL_DESIGN, DECISIONS and IMPLEMENTATION_PLAN.
- Naming: BP_, BPC_, BPI_, WBP_, SM_, SK_, M_, MI_, MF_, T_, NS_, NE_, DA_, DT_, ABP_, SFX_, MUS_, LS_, ST_, L_ (maps).
- Git with LFS. Commit at meaningful checkpoints.

## Git branch rule (owner's instruction, non-negotiable)
- **Never commit to, merge into or push `main`.** Never push phase tags. `main` belongs to the project owner.
- All work (lead and every sub-agent) happens on a `claude/<phase-or-topic>` branch, created from the latest `main`.
- Sub-agents commit only to the currently checked-out `claude/*` branch, never switch branches, and never push.
- At a milestone (a phase ready for review, or a fix set done), STOP and ask the owner to review, merge into `main` and push. Don't push the `claude/*` branch either unless the owner asks.
