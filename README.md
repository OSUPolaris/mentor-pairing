# polaris-pbj
Mentor and mentee pairing and meeting algorithms based on ranking surveys. Designed with Polaris (physics.osu.edu/polaris) mentorship program in mind and includes specific parsers for polaris surveys to obtain preferences.

Features a python module `stablepairing` which features:
 * `.parser` implmenting two parser for polaris like sureveys
 * `.pairing` implmenting a stable pairing algorithm as a class `StablePairing` based on McVitie and Wilson 1970
 * `.util` featuring utility functions for the above features and used in some scripts

 Also found in this repository are jupyter notebook examples (found in `jupyter/`), scripts executing two proceedures for polaris (found in `bin/`) and some example input data (found in `data/`)

 The best way to get started with the `StablePairing` class is to open up the `StablePairing_intro.ipynb` notebook which walks through applying the algorithm to McVitie and Wilson 1970's Table 1 example.
