# river_pollution

Power BI project (PBIP format) analyzing bacterial water-quality monitoring
data for Israeli rivers/streams. Source rows and location/bacteria names are
in Hebrew.

## Project layout

- `river_pollution.pbip` — entry point, opens in Power BI Desktop.
- `river_pollution.SemanticModel/definition/tables/*.tmdl` — the data model
  (TMDL text format, hand-editable).
- `river_pollution.Report/definition/pages/<pageId>/page.json` — one folder
  per report page; `pages.json` holds page order.
- `river_pollution.Report/definition/pages/<pageId>/visuals/<visualId>/visual.json`
  — one folder per visual on that page. This JSON is verbose and positional
  (query projections, filters, and layout are all hand-rolled) — use the
  `pbir-report-builder` skill to add/edit visuals rather than hand-authoring
  it directly.
- `data/csv/` — raw source extracts feeding the Power Query partitions.

## Data model (star schema)

- `FactRiverPollution` — grain: one row per LocationID x DateID x BacterialID
  sample. Key columns:
  - `Result CFU/100 ml` (text, as reported by the lab)
  - `Result_Qualifier` — derived: `"="` (exact numeric), `"<"` (below
    detection limit), `">"` (above range), `"TNTC"` (too numerous to count —
    source text is Hebrew `פלטה מכוסה`, literally "plate covered/overgrown").
  - `Result_Numeric` — the numeric reading, **null when Result_Qualifier is
    TNTC** (there is no number to record). Any chart plotting this column
    directly will show a gap wherever a sample came back TNTC — this is
    expected, not a data bug; TNTC needs to be handled explicitly (a
    substituted ceiling value + a flag for conditional formatting), not left
    to interpolate or render as zero.
- `DimDate` — one row per calendar day in the observed range, `DateID` is a
  surrogate key (not a real date serial) sorted by actual date; use `DimDate`
  fields/hierarchy for any date axis rather than the raw `DateID` on the fact
  table.
- `DimLocation` — `LocationID`, `Location Point`, `Location Name`, `Site`
  (the river/stream name, e.g. `נחל צפורי`).
- `DimBacterialIndex` — `BacterialID`, `Bacterial index` (bacteria type name,
  e.g. `קוליפורם צואתי` / `E.coli MUG`).
- `_Measures` — hidden measures-only table: `Sample Count`, `Average/Median/
  Max/Min CFU`, `TNTC Count`/`TNTC %`, `Below Detection Count`/`%`, `Above
  Range Count`, `Exceedance Count`/`%` (exceedance threshold is
  `Result_Numeric > 400`, scoped to `קוליפורם צואתי` / `E.coli MUG` /
  `סטרפטוקוק/אנטרוקוק ממוצא צואתי` — the third bacteria was added to this
  scope once `Enterococcus EU Standard (Good)` established 400 as its
  threshold too, since no Israeli standard exists; see that measure's doc
  comment and the home page's textbox for why).

## Report

### Control panel page (global slicers)

`523dd6b3bcc91715f8ee` (displayName "לוח בקרה", second in `pageOrder` right
after the intro page) is the single place all four report-wide slicers live
and are visible:
- Year (`8d5622d9447fa738a55b`, `advancedSlicerVisual`, `DimDate.Date
  Hierarchy.Year` — Year level only, no Quarter/Month/Day)
- Bacteria filter (`c653faec3e94d4edbba5`, `advancedSlicerVisual`,
  "between"-style on `DimBacterialIndex.BacterialID`)
- Region/Site/Location tree (`29de3e23663d73249774`, `slicer`, all three
  `DimLocation` columns — `Region`, `Site`, `Location Name` — active so any
  level can be picked directly)
- Exceedance Bucket (`9b2861e8d793f201c9a8`, `slicer`, checkbox list on
  `FactRiverPollution[Exceedance Bucket]`, a calculated column scoped to the
  same three fecal-indicator bacteria as `Exceedance Count`/`%`; values are
  the literal English strings `"Above 400"`/`"Below 400"` baked into that
  column's DAX, not translated)

Every other regular report page **except** `3d8bb27ccc65fca72a29` (see
exception below) keeps its own hidden instance of all four slicers
(`"isHidden": true` on the visual container) so the
selections actually reach that page — synced slicers in PBIR are wired via a
`syncGroup: { groupName, fieldChanges: true, filterChanges: true }` object
that's a sibling of `visualType` inside `visual`, one matching `groupName`
per control (`SyncYear`, `SyncBacterialID`, `SyncLocationTree`,
`SyncExceedanceBucket`) across every page's instance — **this is not the
same as deleting the visual outright**: a page with zero instances of a
group doesn't get filtered by it, so every synced page needs its own
(hidden) copy. This mirrors what Desktop's own View pane > Sync slicers
does when you check "Sync" but leave "Visible" unchecked. Note `syncGroup`
is **not** in the publicly published PBIR schema versions — same
standing-quirk category as `axisScale` below — but hand-authoring it this
way is **confirmed working end-to-end**: in the same session this page was
built, Desktop was reopened and a region + exceedance-bucket selection made
on the control page came back, on the next hand-edit, baked identically
into all 7 hidden per-page copies' `objects.general.properties.filter`. If
slicers ever stop staying in sync after a future Desktop resave, that's
still the first thing to check (Selection pane on the affected page, hidden
instances still present with `isHidden: true` and their `syncGroup`).

Four measures in `_Measures` back a "current selection" summary of the four
control-panel slicers, shown as four stacked `cardVisual`s on the control
page itself (`שנים נבחרות` → `Selected Years Text`, `חיידקים נבחרים` →
`Selected Bacteria Text`, `קטגוריית חריגה נבחרת` → `Selected Exceedance
Bucket Text`, `מיקום נבחר` → `Selected Location Text`). Each returns `"הכל"`
(All) when nothing is effectively filtered, a comma-joined Hebrew list when
a handful of values are picked, or a plain count once a slicer has more
than 6 selections (only Year and Location can realistically hit that;
Bacteria only ever has 3 values and Exceedance Bucket only 2, so neither
needs the count fallback). **Deliberately built as `cardVisual`s, not
Power BI's native dynamic-text-box "Insert data value" feature** — that
feature is a confirmed Power BI limitation for **text-returning** measures
(it works fine for numbers, silently renders nothing for text), and all
four of these measures return text; a plain card visual has no such
limitation. If a literal in-textbox sentence is wanted again later, don't
retry the dynamic-value textbox route for a text measure — it doesn't work
in current Desktop versions.

The user has since added four more plain `cardVisual`s to this page directly
in Desktop (not measure-summary cards — ordinary numeric ones, copies of the
same cards used on the map page): `מספר דגימות` (`Sample Count`), `דגימות
תקינות (עד 400)` (`Positive Sample Count`), `דגימות חורגות (מעל 400)`
(`Exceedance Count`) — same "reacts to the four global filters" behavior as
everything else on this page, no special wiring needed since they're plain
measure cards, not slicers. The page's header textbox (whatever its current
visual id is — the user has already replaced/repositioned it at least once
by hand since this page was first built, so don't assume a fixed id here)
explains both the four filters and what these stat cards mean; if more
cards are added later, extend that same textbox rather than leaving new
controls unexplained.

The fourth card originally showed `Positive:Negative Ratio` (`יחס תקין :
חורג`) but was swapped to **`אחוז דגימות תקינות`** bound to `_Measures[Cleanliness
Score]` (already an existing measure — `1 - [Exceedance %]`, i.e. the
compliant fraction, BLANK-guarded) — a raw ratio like "0.98" isn't
intuitively readable (which side is numerator? what counts as "good"?)
where a percentage is. Its `value.fontColor` is bound to a new
`'Cleanliness Score Color'` measure (green `#1a9850` at ≥50% compliant or
blank/no-data, red `#d03b3b` below), mirroring the exact same pattern
`Positive:Negative Ratio Color` already used — this card is the first
confirmed-working example in this project of `cardVisual`'s
`objects.value[].properties.fontColor.solid.color.expr.Measure` shape,
worth copying verbatim if another card needs measure-driven text color.

A `gauge` visual (`מד תקינות`, next to the stat cards) shows the same
`Cleanliness Score` against a fixed 0%–100% range with a target line —
native Power BI gauges only support a single fill color plus a target
marker, not red/yellow/green banded zones, so it reads as "distance from
the goal" rather than a stoplight; the card carries the good/bad color
signal instead. Its `MinValue`/`MaxValue`/`TargetValue` query wells are
bound to three trivial constant measures (`'Gauge Min (0)'` = 0, `'Gauge
Max (100%)'` = 1, `'Gauge Target (85%)'` = .85) rather than literals typed
into the format pane, since those wells need an actual measure to bind to
— same "constant measure as a fixed reference value" pattern as `[Min
Allowed value]`. The target was originally 100% but moved to 85%: a target
marker sitting exactly at the axis ceiling was visually indistinguishable
from the end of the arc itself. **85% is not a regulatory or
research-backed figure** like the 400 CFU threshold elsewhere in this
report — it's an internal goalpost chosen mainly to sit somewhere visible
on the dial. Don't extend `Gauge Max` past 100% to "make room" for a
100% target instead — `Cleanliness Score` can never exceed 100%, so
anything past that mark would be permanently dead, unreachable arc space,
which is a worse outcome than a target sitting below the ceiling.

Two deliberate standardizations made when consolidating (the 6-7 per-page
copies that existed before this page had drifted from each other):
- The Region/Site/Location tree now has **all three levels active**
  everywhere (some pages previously had only `Region` active, restricting
  what could be picked directly in that control).
- The old `5625a156face4bed9907` (river data) copy of the tree slicer had a
  hard-coded `Region = 'גולן'` self-filter baked into its `general.properties.filter`
  — **removed**, since a shared control can't silently restrict every page
  to one region. If that page-specific restriction was actually load-bearing
  for some downstream visual, it needs to be re-added as an explicit
  page-level filter on that page instead of living inside the shared slicer.

If a new page is added that should respond to these global filters, give it
its own hidden instance of all four (same query/objects as the visible
control-panel copies, `isHidden: true`, matching `syncGroup.groupName`) —
don't just leave it unfiltered. Tooltip pages and the intro page are
intentionally excluded (a tooltip page inherits filter context from the
visual that triggers it, not from page-level slicers).

**Exception: `3d8bb27ccc65fca72a29` ("השוואת אתרים נבחרים") has no hidden
sync instances at all — deliberately excluded from the control panel.**
Its chart (`125b6e9e39967a86bf8f`) carries its own visual-level
`filterConfig` hardcoding a fixed set of 8 specific `DimLocation[Location
Name]` values spread across several different regions (see
[[project-location-comparison-page]] memory) — the whole point of the page
is comparing those specific sites to each other regardless of what's
selected elsewhere. A synced Region/Site/Location tree selection on the
control panel intersects against that hardcoded list; since the 8 sites
aren't all in any one region, a narrow region selection can (and did)
zero out the chart entirely — it isn't a bug in the chart, it's two
different location filters fighting each other. Originally this page did
get hidden synced instances of all four controls like every other page,
but after that exact breakage was hit in practice (a leftover Region
selection on the hidden tree slicer emptied the chart even after sync
itself had been turned off — **an unsynced hidden slicer still applies
whatever filter state it was last left in**, hidden only means not
rendered) the 4 hidden control visuals were removed from this page
entirely rather than merely left unsynced. Don't re-add them without
reconsidering the hardcoded-location design first.

The home page (`34ceb3914f929e522deb`, displayName "מבוא") is the first page
in `pageOrder` and the `activePageName`, so it's what opens by default. It
holds a single large textbox visual (`f9d9aacb89d1951ffc17`) with Hebrew,
right-aligned (`horizontalTextAlignment: "right"` per paragraph — Power BI
textboxes have no paragraph-level RTL/direction property, so this is the
practical way to get an RTL-reading layout) explanatory copy: what each of
the three `Bacterial index` values means and why elevated readings matter
health-wise (קוליפורם צואתי, E.coli MUG, סטרפטוקוק/אנטרוקוק ממקור צואתי), plus
a section on what TNTC means and why it's plotted above the real max rather
than as a gap or zero. Purely descriptive — no query/measures bound to it.
If a new bacteria type is added to the source data, this page's copy (not
just `CFU Bar Color`'s SWITCH branches) should get a new paragraph too.

Page 2 (`5625a156face4bed9907`) no longer shows its slicers directly — Year,
the Region/Site/Location tree, and `BacterialID`/`Bacterial index` are now
hidden instances synced from the control panel page (see above); the page
also carries a hidden instance of the Exceedance Bucket slicer it never had
visibly before. It still holds one line-and-clustered-column combo chart
(`da6f90a4debc44eb57d0`, "Bacterial Counts by Month",
`visualType: lineClusteredColumnComboChart`): category =
`DimDate[YearMonth]`, legend = `DimBacterialIndex[Bacterial index]`
(3 values: `קוליפורם צואתי`, `E.coli MUG`,
`סטרפטוקוק/אנטרוקוק ממוצא צואתי`), column values (`Y`) =
`_Measures[CFU Plot Value]` (the monthly max), line values (`Y2`) =
`_Measures[Average CFU]` (a genuine per-month, per-bacteria average —
distinct from the flat page-wide line described below that reuses the same
measure name for a different purpose). `valueAxis.secShow` is set to
`false` so the line renders against the same primary axis as the columns
rather than getting its own secondary scale, which would make the two
visually incomparable. Added so a single-spike month (tall bar, flat line)
reads differently from a genuinely-bad month (bar and line both high) —
plotting only the max was otherwise silently hiding that distinction.

Five measures in `_Measures` exist specifically to make TNTC chartable
without gaps or fabricated-looking numbers:
- `TNTC Ceiling` — `1.15 × MAX(Result_Numeric)` over the currently
  filtered slicers (site/year/bacteria), ignoring the chart's own axis and
  legend fields (`ALLSELECTED(DimDate)`, `ALLSELECTED(DimBacterialIndex)`),
  falling back to a fixed `6000` only when a filtered selection has no real
  numeric reading at all to anchor to. **Deliberately dynamic, not a fixed
  literal** — `Result_Numeric` in this dataset legitimately ranges from
  single digits to 100,000+ (real pollution spikes), so a fixed sentinel
  (an earlier version used a flat 6000) gets dwarfed by real spikes at some
  sites and looks absurd at others; this measure keeps the TNTC bar
  meaningfully "above the real max" for whatever site/year/bacteria is
  currently in view.
- `CFU Plot Value` — `Result_Numeric` **max** (the worst reading in the
  month, not the average — deliberate, so a single bad sample isn't
  diluted by a calmer one in the same bucket), substituted with
  `[TNTC Ceiling]` when every row in context is TNTC (so the bar still
  renders instead of leaving a gap).
- `Is TNTC Cell` — 1 when the current context is TNTC-only, else 0.
- `CFU Bar Color` — hex string per data point: muted gray (`#898781`) when
  `Is TNTC Cell` = 1, else a fixed color per bacteria type; bound directly
  to the chart's `dataPoint.fill` so TNTC bars read as visually distinct
  from measured ones.
- `TNTC Flag` — human-readable tooltip text ("TNTC — off-scale..." vs
  "Measured").

If a new bacteria type is added to the source data, update `CFU Bar
Color`'s SWITCH branches to keep every category assigned a distinct color
(unmatched values currently fall back to `#52514e`).

The chart's value axis is set to log scale (`axisScale: 'log'`) since CFU
counts span orders of magnitude within a single site — this property name
is not in any published schema (Power BI's per-visual format objects
aren't schema-typed), so if it doesn't visibly take effect after reopening,
toggle it manually: Format visual > Y axis > Type > Log. Confirmed more
than once now that this property doesn't just fail to apply on the first
hand-edit — Desktop's own resave drops it again even after it was working,
so treat "missing `axisScale`" as a standing quirk of this property rather
than a one-off mistake to chase down each time.

Four `y1AxisReferenceLine` entries mark the chart: TNTC ceiling (dashed
gray, `_Measures[TNTC Ceiling]`), a solid red line at the recommended
minimum (literal `400`, matching the `Exceedance Count`/`%` threshold),
a dashed blue `_Measures[Average CFU]` line, and a dotted green
`_Measures[Median CFU]` line. A small textbox visual
(`abc6c232f43b5fdd8b71`, top-left of the page) explains in plain language
why the TNTC ceiling line is there and what "1.15× real max" means — it
doesn't yet describe the other three lines.

Note: as of this session, opening the file in Desktop and saving added a
`filterConfig` block to the chart's visual.json (Desktop's own filter-pane
bookkeeping for the fields in use) — that's expected/harmless, not
something to revert. More generally, if Desktop has this report open,
edits made directly to these JSON files will be silently overwritten the
next time Desktop itself saves — close Desktop before hand-editing PBIR
files, then reopen to see the changes.

Sites/date ranges with many years of dense monthly sampling will render a
crowded x-axis when no Year slicer value is selected — that's expected;
use the existing Year slicer on the page to narrow the window rather than
treating it as a chart bug.

A scatter plot showing every individual sample (real date on X, raw
`Result_Numeric` on Y, colored via `CFU Bar Color`) was tried directly on
this page, positioned above the combo chart, to expose the within-month
spread that a monthly-max bar necessarily hides. It was removed after
review as visually too messy — abandoned, not paused, so don't re-add it
without discussing layout first. If per-sample detail is wanted again, a
drillthrough page (click a bar/month to see that period's raw samples) is
probably a better fit than a second always-visible chart competing for
space on an already-dense page. Two real PBIR/Power BI gotchas surfaced
while building it, worth knowing before trying again: (1) a scatter chart
with a `Category`/"Details" field present requires **both** `X` and `Y` to
carry an explicit aggregation — an unaggregated column paired with a
Details field throws `Remove Values to display x- and y-axis pairs`; (2)
even then, the `X` axis specifically only accepts `None`/`Count`/`Count
Distinct` as its aggregation (not `Max`/`Sum`/etc., at least for a date
column) — using `Max` on `X` throws
`DataViewMappingError_ScatterXIncorrectAggregate`. The working combination
ended up being: no `Category`/Details field at all, `X` unaggregated,
`Y` aggregated as `Max`.
