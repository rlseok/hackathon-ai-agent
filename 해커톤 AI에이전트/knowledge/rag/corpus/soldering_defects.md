---
title: Soldering defects (cold joint, dry joint, insufficient/excess solder, flux residue, oxidation, bridging, blowholes)
source: https://en.wikipedia.org/wiki/Soldering ; NASA workmanship guidance for SMT (as reported by search, https://workmanship.nasa.gov/ — page not reachable from this machine, re-verify before citing)
license: CC BY-SA 4.0 (Wikipedia) — summarised; NASA material is US-government public domain
retrieved: 2026-10-20
domains: [pcb]
tags: [short, solder bridge, cold joint, open circuit, solder]
---

# Cold joint
- Cause: the parts never exceeded the solder melting point (iron melts the solder instead of heating the parts). Risk: no conduction, intermittent conduction, or failure after years in service.
- Look: dull, may be cracked or pock-marked. Prevention: heat the parts so that they melt the solder. NASA SMT guidance treats cold joints as unacceptable and a sign of inadequate heat.

# Dry (disturbed) joint
- Cause: the joint moved while solder cooled (non-eutectic alloys have a plastic range). Mechanically weak and poor electrically. Look: dull, grainy, matte grey.

# Insufficient and excess solder
- Insufficient solder gives a dry, unreliable joint with a too-small fillet (weak mechanically, can fail in thermal cycling).
- Excess solder is not always unsound but usually signals poor wetting and extra heating of sensitive parts. A good joint has a low-angle concave fillet, smooth, bright and shiny with the lead outline visible; lumps or balls suggest poor wetting.

# Oxidation and flux residue
- Oxides and dirt block wetting and heat accelerates re-oxidation: clean the surfaces and use flux.
- Acid-based fluxes leave conductive residue; activated rosin (RA) residue is corrosive and must be cleaned; no-clean residue is non-conductive but may hinder inspection. Clean with water, alcohol or acetone as compatible.

# Bridging (solder short) and blowholes
- Bridging connects adjacent pads or traces. NASA guidance ties it to excess solder, smeared paste, improper placement or wrong heat, and rejects it. Wave soldering uses surface tension and solder mask to avoid bridging.
- Blowholes are typically trapped gas or flux during fillet formation and are rejected. Adhesive inside a solder joint is grounds for rejection. Uneven reflow is acceptable if wetting is good.

# Rework and inspection
- Remove old solder first (braid or solder sucker): old solder holds dissolved base metal and can form brittle joints. Overheating can delaminate the PCB or damage components; use heat sinks on heat-sensitive parts.
- Inspect under magnification; compare against IPC-A-610 / J-STD-001 class (1 general, 2 dedicated service, 3 high reliability).
