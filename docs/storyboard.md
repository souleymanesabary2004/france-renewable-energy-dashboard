# Storyboard

Soumahoro Souleymane, French regions and the renewable electricity transition

Audience: citizens and students, and regional analysts. In four minutes they should know how much renewable electricity France adds, what it replaces, and why regions have to be compared on progress and not only on level.
Pattern: before/after over time plus a comparison of regions (map, small multiples), and a what-if at the end.
Arc: hook, context, key insights, implications and next steps.

## Screen by screen

| # | Where | Headline | What the user sees and does | What they keep |
|---|---|---|---|---|
| 0 | Header and sidebar | Every number follows the filters | 6 KPI tiles; sliders and multiselect | The order of magnitude first |
| 1 | Tab 1, Why it matters | A national number hides the real question | why I chose the topic, audience, 5 questions, how to read level, progress and weighted share | The vocabulary of the story |
| 2 | Tab 2, France | Renewable output rose, and wind and solar did most of the work | stacked bars by source and a share line, hover on a year | Growth is new sources, hydro is flat |
| 3 | Tab 2 | What replaced what in the mix | change of each source's share; lines of renewables, nuclear and thermal in TWh | Nuclear gave way more than fossil fuel (the surprise) |
| 4 | Tab 2 | Which source grows fastest | table and insight box, expander on the denominator effect | Solar fastest in rate, wind biggest in volume |
| 5 | Tab 3, Regions | Level and progress tell different stories | map and ranking, with the indicator switched in the sidebar | The top of the level ranking is not the top of the progress ranking |
| 6 | Tab 3 | Four profiles of regions | quadrant (level against progress), profiles, volume check in TWh | No systematic catch-up |
| 7 | Tab 3 | When did each region move, and my region | heatmap, then a selectbox with KPIs, mix and rank over time | Each viewer finds their own region |
| 8 | Tab 4, Seasons | Renewable electricity has a season | monthly bars and share line, relative profile of each source, decomposition in an expander | Wind and solar complement each other |
| 9 | Tab 4 | Are the gaps closing | dispersion lines, with and without nuclear | They are not closing, and they widen for new sources |
| 10 | Tab 5, What if | Does my ranking depend on my weights | four weight sliders and a rank table; growth sliders and a scenario line | The ranking is robust; the scenario is arithmetic, not a forecast |
| 11 | Tab 6, Conclusions | What the data says | insights that follow the filters, implications, next steps, limits | Compare on progress, look at sources, gaps are a policy question |
| 12 | Tab 7, Data and quality | How far can I trust this | validation checks, missing values, duplicates, method, dictionary, licence | Transparency on structural zeros, negatives, extremes |

## Interaction choices

- The sidebar is always visible and every chart and KPI reads it, so no control is decoration.
- Every chart has a hover with year, source and value with its unit. The map and the ranking use the same indicator.
- Details (dumbbell, decomposition, scenario assumptions, dictionary) sit in expanders.

## Annotations and cautions

An insight box after each group of charts, a warning box when the selection is a subset or too small, medians on the quadrant, peak and weakest month in the seasonal headline. I explain level against progress, weighted against average share, and the denominator effect once each, at the place where a reader could misread.

## Accessibility

Colour-blind safe palette, the same colour for a source on every page, units on every axis, a text alternative under every chart, help text on every control.

## Video

The script is in `docs/video_script.md`: hook, France, regions, seasons and gaps, what-if, data quality and conclusion.
