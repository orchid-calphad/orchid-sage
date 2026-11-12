#!/bin/bash
# Copy finished results from spark1 to the Studio (read-only pull; nothing deleted on either side).
R=<home>/ScientificRuns/crni-phaseforge-20261105
mkdir -p $R/collected_solids $R/collected_liquid
rsync -a --exclude '*.traj' spark1:runs/crni-phaseforge-20261105/runs/solids/ $R/collected_solids/
rsync -a spark1:runs/crni-phaseforge-20261105/runs/liquid/ $R/collected_liquid/
rsync -a spark1:runs/crni-phaseforge-20261105/logs/ $R/logs/spark1/
