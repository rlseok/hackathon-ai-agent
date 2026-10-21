---
title: PCB bare-board defects (open circuit, short, mouse bite, spur, spurious copper, pinhole, missing hole, delamination)
source: https://arshon.com/blog/open-circuits-in-pcbs-how-they-occur-and-how-to-fix-them/ ; https://nextpcb.com/blog/pcb-mouse-bites-fundamental-guide ; https://en.wikipedia.org/wiki/Printed_circuit_board ; UniPCB arXiv:2601.19222 (definitions via search snippets)
license: vendor blogs are copyrighted — only paraphrased facts are kept, with the URL as citation; Wikipedia CC BY-SA 4.0
retrieved: 2026-10-20
domains: [pcb]
tags: [open circuit, short, mouse bite, spur, spurious copper, pinhole, missing hole, etching, drilling]
---

# Open circuit (opencircuit / broken trace)
Aliases: 단선, đứt mạch, hở mạch, broken trace, open
- Manufacturing causes: incomplete etching leaves traces unfinished; poorly plated vias; cracked via-barrel plating from copper thermal expansion. Field causes: bending/twisting, rapid temperature change cracking traces or solder joints, handling damage, cold or insufficient solder joints, design errors (undefined nets, ignored DRC).
- Detection: visual inspection with magnification, continuity test with a multimeter segment by segment, functional test with oscilloscope/logic analyzer; AOI and electrical test in production.
- Fix: bridge a broken trace with a thin wire soldered at both ends (conductive paint only for tiny breaks); reflow or add solder on weak joints; replace faulty components. Recurring: revise placement and routing, keep traces short, avoid sharp bends, run DRC and simulation.

# Short circuit
Aliases: 단락, ngắn mạch, chập mạch, solder bridge, short
- Causes: copper slivers or fragments of copper/solder left from fabrication that connect nets; residual debris or contamination; solder bridging between pads/traces (solder mask dams help prevent it); incomplete etching (under-etch) leaving copper between traces.
- Action [general practice, not stated in the cited pages]: isolate the board, locate the short, remove the sliver or bridge, then review etching and cleaning controls.

# Mouse bite (surface defect, not the panel breakaway perforation)
Aliases: 마우스바이트, khuyết răng chuột, notch
- Definition: tiny irregular notches, pits or saw-tooth marks on conductors, pads or mask openings.
- Causes (usually a chain of weak controls): poor dry-film lamination (bubbles, dust, wrinkles); etchant drift in concentration, temperature, spray pressure or conveyor speed; over-etch near resist edges; exposure/development errors; poor mask leveling, viscosity or pre-clean; plating bubbles leaving pits; aggressive brushing/deburring; incomplete rinsing; too-narrow mask dams.
- Impact: disrupts solder wetting (opens, intermittent contact, voids, bridging in fine pitch), field concentration in HV/HF designs, reduced creepage, corrosion start.
- Inspection: 10–30x magnification, side lighting, compare with a golden sample; IPC-A-600 acceptability by Class 1/2/3 — key questions: is copper/substrate exposed, does it enter the solder area, is trace width below design, is clearance affected.
- Prevention: clean surfaces before wet steps; tune exposure, development, etch parameters, mask viscosity and cure; fillets/teardrops, avoid needle features (DFM); AOI after etching and mask; fishbone (4M+E) root-cause workflow, defect library, Pareto.

# Spur and spurious copper
Aliases: 스퍼, 잔여 동박, gai đồng, đồng thừa, false copper
- Spur: copper projecting from a trace edge, bridging gaps (short risk, signal noise). Spurious copper: isolated copper in unintended areas (short risk, parasitic coupling, EMC). [Definitions from UniPCB snippet; origin and action below are general practice, not stated in the cited pages] Origin: resist defects or incomplete etch. Action: remove only if the customer class allows, then fix imaging/etch controls.

# Pinhole and blowhole
Aliases: 핀홀, lỗ kim, pin-hole
- Pinholes in plated through-holes are linked to moisture and volatiles escaping through voids in copper plating; use adequate copper thickness and baked, higher-quality laminate. Pinholes in copper foil/traces reduce current-carrying area.

# Missing hole
Aliases: 홀 누락, thiếu lỗ, missing hole
- [General practice, not stated in the cited pages] A drilled hole absent or off-position usually comes from drill breakage/wear or a programming/registration error: monitor drill hit count, check the drill file and registration, add an AOI/X-ray check. (Wikipedia only notes that drill bits wear out or break.)

# Delamination and plated-through-hole failure
- Moisture absorbed in the substrate vaporises during soldering ("popcorning") causing cracking and delamination: bake substrates before soldering. Above Tg the resin expands sharply and stresses plated holes; repeated soldering can crack the plating — use high-Tg laminate for thick boards.
