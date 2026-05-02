"""Indian tax constants keyed by Financial Year (FY).

FY = April-March. AY (Assessment Year) = FY + 1. So FY 2024-25 -> AY 2025-26.
All amounts in INR.
"""
from typing import List, Tuple, Optional

# A slab is (lower_bound_inclusive, upper_bound_exclusive, rate_percent).
# upper_bound = None means "no upper bound" (catch-all top slab).
Slab = Tuple[int, Optional[int], float]

# Source: Finance Act 2024, applicable for AY 2025-26 (FY 2024-25).
NEW_REGIME_SLABS_FY_2024_25: List[Slab] = [
    (0,         300_000,  0.0),
    (300_000,   700_000,  5.0),
    (700_000,   1_000_000, 10.0),
    (1_000_000, 1_200_000, 15.0),
    (1_200_000, 1_500_000, 20.0),
    (1_500_000, None,      30.0),
]

OLD_REGIME_SLABS_FY_2024_25: List[Slab] = [
    (0,         250_000,  0.0),
    (250_000,   500_000,  5.0),
    (500_000,   1_000_000, 20.0),
    (1_000_000, None,      30.0),
]

# Standard deduction (salary income only).
STANDARD_DEDUCTION_NEW_FY_2024_25 = 75_000
STANDARD_DEDUCTION_OLD_FY_2024_25 = 50_000

# Section 87A rebate.
REBATE_87A_NEW_FY_2024_25 = {"income_threshold": 700_000, "max_rebate": 25_000}
REBATE_87A_OLD_FY_2024_25 = {"income_threshold": 500_000, "max_rebate": 12_500}

# Health & Education Cess.
CESS_RATE = 0.04  # 4% on (tax + surcharge)

# Surcharge thresholds (income -> rate). Old regime has 4 bands.
SURCHARGE_BANDS_FY_2024_25 = [
    (5_000_000,  10_000_000, 0.10),
    (10_000_000, 20_000_000, 0.15),
    (20_000_000, 50_000_000, 0.25),
    (50_000_000, None,       0.37),
]
# New regime caps surcharge at 25% (no 37% top band).
SURCHARGE_BANDS_NEW_FY_2024_25 = [
    (5_000_000,  10_000_000, 0.10),
    (10_000_000, 20_000_000, 0.15),
    (20_000_000, None,       0.25),
]

# Section 80C / 80D limits (old regime only).
LIMIT_80C = 150_000
LIMIT_80D_SELF_BELOW_60 = 25_000
LIMIT_80D_SELF_60_PLUS = 50_000

SUPPORTED_FYS = ("2024-25",)
