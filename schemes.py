import re
from enum import Enum

RPE_SCHEME = (
    "(?P<rpe>(?:[1-9](?:,|\.)[5])|(?:[1-9]|10)|(?:9\.3|9\.6))"
)
RPE_MULTISET_SCHEME = f"(?P<multi_rpe>(?:@{RPE_SCHEME}){{2,}})"
WEIGHT_SCHEME = (
    "(?:(?P<weight>[0-9]+(?:\.[0-9]{1,3})?)" "(?i)(?P<unit>kg|lbs|bw)?|(?P<bw>BW))"
)
PERCENTAGE_SCHEME = "(?P<percentage>[1-9][0-9]?|100)"
REPS_SCHEME = "(?P<reps>[0-9]+)"
SETS_SCHEME = "(?P<sets>[0-9]+)"


class SetType(Enum):
    NONE = -1
    RPE = 0
    WEIGHT = 1
    PERCENT_1RM = 2
    LOAD_DROP = 3
    FATIGUE_PERCENT = 4
    RPE_RAMP = 5


SCHEMES_PLANNED = (
    (re.compile(f"^x{REPS_SCHEME}@{RPE_SCHEME}$"), SetType.RPE),  # x5@9 REPS at RPE
    (
        re.compile(f"^{SETS_SCHEME}x{REPS_SCHEME}@{PERCENTAGE_SCHEME}%$"),
        SetType.PERCENT_1RM,
    ),  # 5x5@90% SETS of REPS at PERCENTAGE
    (
        re.compile(f"^{PERCENTAGE_SCHEME}%@{RPE_SCHEME}$"),  # 80%@8 PERCENTAGE at RPE
        SetType.PERCENT_1RM,
    ),
    (
        re.compile(
            f"^x{REPS_SCHEME}{RPE_MULTISET_SCHEME}$"
        ),  # x5@8@9 REPS at RPE multiple #needs furhter processing
        SetType.RPE,
    ),
    (
        re.compile(
            f"^{SETS_SCHEME}x{REPS_SCHEME}\^@{RPE_SCHEME}$"
        ),  # 4x4^@7 SETS of REPS starting at RPE
        SetType.RPE,
    ),
    (
        re.compile(f"^{SETS_SCHEME}x@{RPE_SCHEME}$"),  #  3x@9 number of SETS at RPE
        SetType.RPE,
    ),
    (
        re.compile(f"^{PERCENTAGE_SCHEME}%x{REPS_SCHEME}$"),  # 80%x5 REPS at %1RM
        SetType.PERCENT_1RM,
    ),
    (
        re.compile(
            f"^{SETS_SCHEME}x{REPS_SCHEME}V{PERCENTAGE_SCHEME}%$"
        ),  # 3x3V90% SETS of REPS at PERCENTAGE
        SetType.LOAD_DROP,
    ),
    (
        re.compile(f"^x{REPS_SCHEME}\$@{RPE_SCHEME}$"),  # 3x3$@9 SETS x WEIGHT at RPE
        SetType.RPE_RAMP,
    ),
    (
        re.compile(
            f"^{SETS_SCHEME}x{REPS_SCHEME}$"
        ),  # 3x8 SETS of REPS starting at RPE
        SetType.NONE,
    ),
    (
        re.compile(
            f"^x{REPS_SCHEME}@{RPE_SCHEME}\-{PERCENTAGE_SCHEME}%$"
        ),  # x4@9-7% SETS of REPS starting at RPE
        SetType.FATIGUE_PERCENT,
    ),
    (
        re.compile(
            f"^{WEIGHT_SCHEME}@{RPE_SCHEME}$"
        ),  # 160lbs@9 SETS of REPS starting at RPE
        SetType.RPE,
    ),
    (
        re.compile(
            f"^{WEIGHT_SCHEME}/{REPS_SCHEME}$"
        ),  # 150x5 SETS of REPS starting at RPE
        SetType.WEIGHT,
    ),
    (
        re.compile(
            f"^{SETS_SCHEME}[xX]$"
        ),  # Just number of sets, eg. '5x'. For low priority exercises
        SetType.NONE,
    ),
)
SCHEMES_DONE = (
    (
        re.compile(
            f"^{WEIGHT_SCHEME}x{REPS_SCHEME}@{RPE_SCHEME}$"
        ),  # weightXreps at RPE
        SetType.WEIGHT,
    ),
    (
        re.compile(
            f"^{WEIGHT_SCHEME}@{RPE_SCHEME}$"
        ),  #'weight at RPE (presumed same set number as planned)',
        SetType.WEIGHT,
    ),
    (
        re.compile(
            f"^{WEIGHT_SCHEME}{RPE_MULTISET_SCHEME}$"
        ),  # Multiple Weight@Rpe sets written in one string
        SetType.WEIGHT,
    ),
    (
        re.compile(
            f"^{WEIGHT_SCHEME}x{REPS_SCHEME}" f"{RPE_MULTISET_SCHEME}$"
        ),  # Multiple WeightXReps@Rpe sets written in one string
        SetType.WEIGHT,
    ),
    (
        re.compile(f"^{SETS_SCHEME}x{REPS_SCHEME}" f"(?:\/|x|@){WEIGHT_SCHEME}$"),
        SetType.WEIGHT,
    ),
    (re.compile("^ *(?P<undone>[Xx]?) *$"), SetType.NONE),  # exercise not done
    # (re.compile("^(?P<undone> ?)$"), SetType.NONE),  # exercise not done
    (re.compile("^ *(?P<done>[Vv]+) *$"), SetType.NONE),  # Done, V for each set
    (
        re.compile(f"^{WEIGHT_SCHEME}[Xx][Vv]+$"),
        SetType.WEIGHT,
    ),  # Kilograms done for as many sets as "v's" after weight
    # eg. 40kgxVVVVV, reps presumed as planned
    # TODO legit support for this and related in matched set parser
    (
        re.compile(
            f"^(?P<multi_reps>(?:{REPS_SCHEME}(?:,|@))+){WEIGHT_SCHEME}$"
        ),  # Multiple sets at given weight
        SetType.WEIGHT,
    ),
    (
        re.compile(f"^{REPS_SCHEME}x{WEIGHT_SCHEME}$"),  # Reps at weight
        SetType.WEIGHT,
    ),
)
