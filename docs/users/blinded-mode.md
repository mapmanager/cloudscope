# Blinded analysis mode

Blinded analysis mode reduces **experimenter bias** during analysis by hiding
file and condition identity in the CloudScope GUI. Combined with a
[randomized file subset](../notebooks/generating-randomized-file-for-analysis.ipynb),
it lets you analyze a large dataset without bias in either the **choice of files**
or the **scoring of each file**.

## Turning it on

Open the **Config** panel from the left toolbar and toggle **blinded mode**. The
setting is saved immediately and applied across the home page and pool plots.

## What is masked

While blinded mode is on, CloudScope replaces identifying information with stable
`File N` labels:

- File names and file-list / acquisition-tree rows, including parent and
  grandparent folder names.
- Experimental metadata columns (for example condition and genotype), which
  collapse to a fixed `Blinded` value.
- Footer and analysis-panel selection labels.
- Pool-plot grouping columns and point labels; pool selections still map back to
  the correct underlying rows.

The **Experiment Metadata** panel is disabled (and closed) while blinded so that
condition and genotype cannot be read or edited.

## What is not masked

Blinded mode is a **bias-reduction display layer, not a security boundary**. By
design the following remain unblinded:

- Load and save controls, recent paths, native file pickers, and save paths.
- App Info and log output.
- Real file paths and identifiers in backend state, saved files, and logs.

Anyone with disk or log access can still recover file identity. Use blinded mode
to keep the *person doing the analysis* from being influenced by identity, not to
enforce access control.

## Recommended unbiased workflow

1. **Sample without bias.** Use the
   [randomized file subset notebook](../notebooks/generating-randomized-file-for-analysis.ipynb)
   to draw a randomized, per-condition subset from a large folder and write it to
   a manifest CSV.
2. **Load the subset.** In CloudScope, use **Load CSV** from the **history menu** in the [load/save controls](gui.md#top-header-and-loadsave-controls) to
   open the sampled manifest.
3. **Blind the analyst.** Turn on blinded mode in the Config panel before
   scoring or running analyses.
4. **Analyze and save.** Run analyses as usual; results are saved next to each
   source file with true identities intact.
5. **Unblind for interpretation.** Turn blinded mode off (or reload) once
   analysis is complete to group and interpret results by condition.
