# THE LAST BELL — Risk Log

Likelihood and impact are rated L, M or H.

| ID | Category | Risk | L | I | Mitigation | Status |
|---|---|---|---|---|---|---|
| R-01 | Performance | The dev GPU (RTX 4050 Laptop, 6 GB VRAM) is below the high-end target, so quality can't be validated at High/Epic and VRAM pressure is likely | H | H | Two-tier budget (PERFORMANCE_BUDGET.md); measure on the dev floor every milestone; 2K default textures; ask the user for reference hardware tests in Phase 20 | Open |
| R-02 | Tooling | UE 5.8 MCP and toolsets are experimental plugins: tools may fail silently or change | M | M | Check every tool result; fall back to Python or manual steps; never chain unchecked mutations | Open |
| R-03 | Tooling | Converting a Blueprint-only project to C++ (first compile, VS toolchain selection with both VS 18 and VS 2022 installed) | M | M | CORE-001 is isolated and its own task; verify the toolchain before writing gameplay code | Open |
| R-04 | Tooling | The 3d.shep.bot MCP is remote and may not be able to download files locally | H | L | Treat it as discovery only; download manually through a verified workflow; check the files exist before claiming success | Open |
| R-05 | Asset | Fab assets need a human to acquire them; the art pipeline can stall | M | M | Batch acquisition requests in Phase 6 with alternatives listed | Open |
| R-06 | Licensing | Mixed-license assets (CC-BY, Fab Standard and Personal licenses) | M | H | ASSET_REGISTRY entry before use; prefer CC0 or Fab Standard; never use unknown licenses | Open |
| R-07 | Art | The game looks like disconnected marketplace packs | M | H | A coherent kit per area, custom hero assets, a material layer over kits, the quality check every visual phase | Open |
| R-08 | AI | The Warden feels unfair or gets stuck (narrow crypt navigation) | M | H | 180 cm corridor minimum, debug draw, unreachable-player handling, repeated playtests in Phase 5 | Open |
| R-09 | Rendering | Lumen noise or light leaking in dark interiors, VSM cost with many candles | M | M | Non-shadow-casting candles, measured HWRT vs software decision, Phase 14 tuning | Open |
| R-10 | Packaging | Experimental editor plugins or template content leaking into Shipping | L | M | MCP plugins restricted to the Editor target; the template is removed in Phase 1; a packaging test in Phase 22 plus an early smoke package in Phase 2 | Open |
| R-11 | Process | The repo has no remote, so all history lives on one disk | M | H | Recommend adding a private LFS-capable remote (GitHub or Azure DevOps) at the Phase 0 sign-off | Open |
| R-12 | Scope | Feature creep beyond 20–30 minutes | M | M | Scope rule (directive §71); every addition goes through DECISIONS.md | Open |
