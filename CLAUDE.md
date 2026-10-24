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
- Model/effort rule (owner, D-048): the lead plans in Opus 5.5 at xhigh effort; every implementation agent is spawned with `model: "sonnet", effort: "high"`. Plans live in `Docs/plans/` and are explicit enough that an implementer never guesses (exact assets, paths, values, coordinates, acceptance checks).
- C++: `Source/LastBell/` (prefix `LB`). Content: `Content/LastBell/` — never dump assets in the Content root.
- Raw downloads: `ExternalAssets/Incoming/` (git-ignored). Every external asset goes in `Docs/ASSET_REGISTRY.md`.

## Engineering rules
- Never edit `.uasset` or `.umap` binaries outside Unreal. Use the editor or MCP only.
- Unreal MCP (`unreal-mcp`, http://127.0.0.1:8000/mcp): check every tool result; serialize mutations to the same asset. Agents without native MCP tools use `Tools/mcp/ue.py`; read `Tools/mcp/MCP_NOTES.md` first.
- Compile after C++ changes, compile the affected Blueprints, validate materials, and check the logs. Don't pile up unvalidated work.
- Composition over inheritance; subsystems over manager actors; Gameplay Tags for state; no hard asset refs in C++.
- Architecture drift: if the implementation differs from TECHNICAL_DESIGN, either fix the code or update TECHNICAL_DESIGN, DECISIONS and IMPLEMENTATION_PLAN.
- Naming: BP_, BPC_, BPI_, WBP_, SM_, SK_, M_, MI_, MF_, T_, NS_, NE_, DA_, DT_, ABP_, SFX_, MUS_, LS_, ST_, L_ (maps).
- Git with LFS. Commit at meaningful checkpoints.

## Git branch rule (owner's instruction, non-negotiable)
- **Never commit directly on `main`.** All work (lead and every sub-agent) happens on a `claude/<phase-or-topic>` branch, created from the latest `main`.
- Sub-agents commit only to the currently checked-out `claude/*` branch, never switch branches, never merge, and never push.
- At a milestone (a phase ready for review, or a fix set done), STOP and ask the owner for review and approval.
- Only after the owner **explicitly approves and says to merge** does the lead:
  1. fast-forward or merge the branch into `main`;
  2. push `main`;
  3. delete the branch locally and on the remote, after checking `git log main..<branch>` is empty.
- Don't push work branches or phase tags unless asked.
- While Unreal has the project open, never check out an older commit: it swaps .umap/.uasset files under the editor. Fast-forward with `git fetch . <branch>:main`, then switch.
