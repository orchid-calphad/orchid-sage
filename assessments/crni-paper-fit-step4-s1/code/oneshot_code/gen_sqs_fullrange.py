"""PI decision 6 Nov: bcc and fcc SQS over the whole composition range (avoid extrapolating each RK fit over half the range).
Adds bcc x_Ni 0.625, 0.75, 0.875, 0.9375 and fcc x_Ni 0.0625, 0.125, 0.1875, 0.9375; 128 atoms, 2 seeds, same generator
(gen_sqs.make: m_scraps, same objective and cutoffs) and seeds as the existing grid. Run with <home>/.venvs/phaseforge/bin/python."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_sqs
out = sys.argv[1]
for lat, ns in (("BCC_A2", [80, 96, 112, 120]), ("FCC_A1", [8, 16, 24, 120])):
    for n in ns:
        for seed in gen_sqs.SEEDS[lat]:
            gen_sqs.make(lat, n, seed, out)
