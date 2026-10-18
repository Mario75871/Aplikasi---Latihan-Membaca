# Design — BacaLaras (Frontend)

Locked design system. Future Hallmark runs read this file first; pages defer
to it. Amend intentionally — the file is the rule.

## System
- Genre · editorial
- Macrostructure · Narrative Workflow (landing) · Workbench/ledger (app)
- Theme · custom (vibe: "buku catatan guru yang dicetak hangat")
- Axes · oat-paper / serif-display (Newsreader) / terracotta-accent (~42°)

## Tokens (canonical · `tokens.css` is the source of truth)
```css
:root {
  /* Surfaces — oat paper, never #fff */
  --color-paper:       oklch(96.9% 0.010 73);  /* #F9F4EE */
  --color-paper-card:  oklch(98.6% 0.009 85);  /* #FDFAF4 */
  --color-paper-2:     oklch(94.8% 0.015 81);  /* #F3EDE3 */
  --color-rule:        oklch(90.9% 0.019 83);  /* #E7E0D3 */

  /* Warm ink — never #000 */
  --color-ink:         oklch(20.1% 0.014 62);  /* #1B1510 */
  --color-ink-2:       oklch(27.0% 0.016 67);  /* #2C251E */
  --color-muted:       oklch(44.1% 0.020 70);  /* #5A5147 */
  --color-neutral:     oklch(54.0% 0.020 73);  /* #766D62 */

  /* One accent — terracotta (highlighter only, ≤5% viewport) */
  --color-accent:        oklch(57.9% 0.142 42);  /* #BD582E */
  --color-accent-strong: oklch(49.9% 0.138 41);  /* #A14118 */
  --color-accent-warm:   oklch(64.0% 0.164 31);  /* #DE5E4A */
  --color-focus:         oklch(57.9% 0.142 42 / 0.35);

  /* Status family (always icon + label; never colour alone) */
  --color-intervene: oklch(48.0% 0.125 18);   /* #973A42 oxblood  */
  --color-stay:      oklch(66.0% 0.125 70);   /* #C2832D ochre    */
  --color-candidate: oklch(47.1% 0.093 310);  /* #6B4B82 violet   */
  --color-promote:   oklch(47.0% 0.084 150);  /* #346841 pine     */
  --color-unassessed:oklch(62.4% 0.018 74);   /* #8E867C neutral  */

  /* Words — incorrect stays warm-neutral, NOT red (non-punitive) */
  --color-word-correct:   oklch(47.0% 0.084 150);  /* #346841 */
  --color-word-incorrect: oklch(57.1% 0.115 68);   /* #A3691B ochre */
  --color-word-neutral:   oklch(44.1% 0.020 70);   /* #5A5147 */
  --color-word-active:    oklch(57.9% 0.142 42);   /* #BD582E */

  /* Comprehension competencies */
  --color-comp-retrieve:  oklch(47.1% 0.070 231);  /* #2C627B */
  --color-comp-interpret: oklch(47.1% 0.093 310);  /* #6B4B82 */
  --color-comp-reflect:   oklch(46.9% 0.075 170);  /* #266854 */

  --font-display: var(--font-newsreader), "Newsreader", ui-serif, Georgia, serif;
  --font-body:    var(--font-geist), "Geist", ui-sans-serif, system-ui, sans-serif;
  /* Two families only — no third face, no mono (Geist Mono reserved, ≤2 slots, unused). */

  /* 4-pt spacing scale, named: --space-3xs … --space-4xl. See tokens.css.   */
  /* Type scale, 1.25 (major-third) ratio: --text-xs … --text-display.       */

  --ease-out: cubic-bezier(0.22, 1, 0.36, 1);
  --ease-in:  cubic-bezier(0.55, 0, 1, 0.45);
  --dur-micro: 120ms;  --dur-minor: 220ms;  --dur-major: 360ms;

  --radius-chip: 4px;  --radius-input: 6px;  --radius-card: 10px;  --radius-sheet: 14px;
}
```

## CTA voice
- Primary · ink-strong fill (`--color-ink-2`) or accent edge/text · radius 6px · tight padding rhythm.
- Secondary · outline (1px `--color-rule`) · same radius · hover → rule darkens, no fill.
- Accent is a highlighter, never a full button fill. Nav active = dark text + accent rule, not a block.

## Motion stance
- Silent by default · 1–2 reveal primitives (opacity/transform only) · page/row transitions via framer-motion.
- Orchestrate one moment (e.g. table rows reveal on filter change) rather than many hover-lifts.
- Reduced-motion fallback · ≤150 ms opacity crossfade (`prefers-reduced-motion` kills spatial motion).

## Copy rule
- User-visible text carries **no PRD codes** (`BR-xx`, `§nn`, `D-ID`, raw engine names). State the rule in plain Indonesian instead.
- `BR-xx` trace allowed only inside a collapsed "Detail untuk juri" affordance (e.g. `StatusExplainer`).
- Status labels, disclaimers, and domain terms (WCPM, Akurasi, Pemahaman) are fixed.

## Exports
`tokens.css` (in this project) is the source of truth. For Tailwind v4
`@theme`, DTCG `tokens.json`, or shadcn/ui CSS variables, ask *"extend
design.md with Tailwind exports"* (or the format you want) — Hallmark will
append them per `export-formats.md`.

## Notes
- Student Mode (`components/student/**`, `app/assess/**`) is frozen: `.passage` / `.passage-record` rules, touch targets ≥44px, large reading type.
- Shared Tailwind scales (`slate/rose/amber/violet/emerald/sky/teal/red/white`) are overridden with warm-earth hex, so legacy class names auto-recolour.
