import re
from enum import Enum

RPE_SCHEME = (
    "(?P<rpe>(?:[1-9](?:,|\.)[5])|(?:[1-9]|10)|(?:9\.3|9\.6))"
)
RPE_MULTISET_SCHEME = f"(?P<multi_rpe>(?:@{RPE_SCHEME}){{2,}})"
WEIGHT_SCHEME = (
    "(?:(?P<weight>[0-9]+(?:\.[0-9]{1,3})?)" "(?i)(?P<unit>kg|lbs|bw)?|(?P<bw>BW))"
)
WEIGHT_NO_GUESS_SCHEME = (
    "(?:(?P<weight>[0-9]+(?:\.[0-9]{1,3})?)" "(?i)(?P<unit>kg|lbs|bw)|(?P<bw>BW))"
) # TODO check where this specific one is needed (to avoid conflicts)
PERCENTAGE_SCHEME = "(?P<percentage>[1-9][0-9]?|100)"
REPS_SCHEME = "(?P<reps>[0-9]+)"
SETS_SCHEME = "(?P<sets>[0-9]+)"


class SetType(Enum): # Likely TODO split this into planned and done
    NONE = -1 # Placehodler for unimplemented
    RPE = 0
    WEIGHT = 1 # KGs 
    PERCENT_1RM = 2 # self explanatory
    LOAD_DROP = 3 # repeats at given percentage of previous set, better named RELATIVE_WEIGHT or smth
    FATIGUE_PERCENT = 4 # repeats until reaching RPE of the top set (previous set)
    RPE_RAMP = 5 # to remove?
    DONE = 6 # Boolean - just done one set with no additional info
    DONE_ALL = 7 # Done all sets as planned


SCHEMES_PLANNED = (
    (re.compile(f"^x{REPS_SCHEME}@{RPE_SCHEME}$"), SetType.RPE),  # x5@9 REPS at RPE
    (re.compile(f"^{SETS_SCHEME}x{REPS_SCHEME}@{PERCENTAGE_SCHEME}%$"),
     SetType.LOAD_DROP, # That one is used all the time
    ),  # 5x5@90% SETS of REPS at PERCENTAGE of previous set (top set)
    (re.compile(f"^{SETS_SCHEME}x{REPS_SCHEME}@{PERCENTAGE_SCHEME}%RM$"),
     SetType.PERCENT_1RM,
    ),  # 5x5@90%RM SETS of REPS at PERCENTAGE of 1RM
    (re.compile(f"^{PERCENTAGE_SCHEME}%@{RPE_SCHEME}$"),  # 80%@8 PERCENTAGE at RPE
     SetType.PERCENT_1RM,
    ),
    (re.compile( f"^x{REPS_SCHEME}{RPE_MULTISET_SCHEME}$"),  # x5@8@9 REPS at RPE multiple #needs furhter processing
     SetType.RPE,
    ),
    (re.compile( f"^{SETS_SCHEME}x{REPS_SCHEME}\^@{RPE_SCHEME}$"),  # 4x4^@7 SETS of REPS starting at RPE
     SetType.RPE,
    ),
    (re.compile(f"^{SETS_SCHEME}x@{RPE_SCHEME}$"),  #  3x@9 number of SETS at RPE
     SetType.RPE,
    ),
    (re.compile(f"^{PERCENTAGE_SCHEME}%x{REPS_SCHEME}$"),  # 80%x5 REPS at %1RM
     SetType.PERCENT_1RM,
    ),
    (re.compile( f"^{SETS_SCHEME}x{REPS_SCHEME}V{PERCENTAGE_SCHEME}%$"),  # 3x3V90% SETS of REPS at PERCENTAGE
     SetType.LOAD_DROP, # Unused tbh, maybe just TODO remove
    ),
    (re.compile(f"^x{REPS_SCHEME}\$@{RPE_SCHEME}$"),  # 3x3$@9 SETS x WEIGHT at RPE
     SetType.RPE_RAMP,
    ),
    (re.compile( f"^{SETS_SCHEME}x{REPS_SCHEME}$"),  # 3x8 SETS of REPS starting at RPE
     SetType.DONE,
    ),
    (re.compile( f"^x{REPS_SCHEME}@{RPE_SCHEME}\-{PERCENTAGE_SCHEME}%$"),  # x4@9-7% SETS of REPS starting at RPE
     SetType.FATIGUE_PERCENT,
    ),
    (re.compile( f"^{WEIGHT_SCHEME}@{RPE_SCHEME}$"),  # 160lbs@9 SETS of REPS starting at RPE
     SetType.RPE,
    ),
    (re.compile( f"^{WEIGHT_SCHEME}/{REPS_SCHEME}$"),  # 150/5 SETS of REPS starting at RPE
     SetType.WEIGHT,
    ),
    (re.compile( f"^{SETS_SCHEME}[xX]$"),  # Just number of sets, eg. '5x'. For low priority exercises
     SetType.DONE,
    ),
)
SCHEMES_DONE = (
    (re.compile( f"^{WEIGHT_SCHEME}x{REPS_SCHEME}@{RPE_SCHEME}$"),  # weightXreps at RPE
     SetType.WEIGHT,
    ),
    (re.compile( f"^{WEIGHT_SCHEME}@{RPE_SCHEME}$"),  #'weight at RPE (presumed same set number as planned)',
     SetType.WEIGHT,
    ),
    (re.compile( f"^{WEIGHT_SCHEME}{RPE_MULTISET_SCHEME}$"),  # Multiple Weight@Rpe sets written in one string
     SetType.WEIGHT,
    ),
    (re.compile( f"^{WEIGHT_SCHEME}x{REPS_SCHEME}" f"{RPE_MULTISET_SCHEME}$"),  # Multiple WeightXReps@Rpe sets written in one string
     SetType.WEIGHT,
    ),
    (re.compile(f"^{SETS_SCHEME}x{REPS_SCHEME}" f"(?:\/|x|@){WEIGHT_SCHEME}$"),
     SetType.WEIGHT,
    ),
    (re.compile("^ *(?P<undone>[Xx]?) *$"), SetType.DONE),  # exercise not done
    # (re.compile("^(?P<undone> ?)$"), SetType.NONE),  # exercise not done
    (re.compile("^\s*(?P<done>[V])\s*$"), SetType.DONE_ALL),  # Done, V for each set
    (re.compile("^\s*(?P<done>[v]+|[V]{2,})\s*$"), SetType.DONE),  # Done, V for each set, parse by len(?)
    (re.compile(f"^{WEIGHT_SCHEME}[Xx](?P<done>[Vv]+)$"), SetType.WEIGHT,
    ),  # Kilograms done for as many sets as "v's" after weight
    # eg. 40kgxVVVVV, reps presumed as planned
    # TODO legit support for this and related in matched set parser
    (re.compile( f"^(?P<multi_reps>(?:{REPS_SCHEME}(?:,|@))+){WEIGHT_SCHEME}$"),  # Multiple sets at given weight
     SetType.WEIGHT, # 10,10,10,8,6@100kg
    ),
    (re.compile(f"^{REPS_SCHEME}x{WEIGHT_SCHEME}$"),  # Reps at weight
     SetType.WEIGHT,
    ),
    (re.compile(f"^x{REPS_SCHEME}@{RPE_SCHEME}$"),  # Reps at rpe, relative wegiht
     SetType.LOAD_DROP,
    ),
    (re.compile(f"^x{REPS_SCHEME}{RPE_MULTISET_SCHEME}$"),
     SetType.LOAD_DROP,  # Reps at rpe, relative wegiht, many sets
    ),
)
