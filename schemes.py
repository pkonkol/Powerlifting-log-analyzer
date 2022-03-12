import re
from enum import Enum

RPE_SCHEME = (r"(?P<rpe>(?:[1-9](?:,|\.)[5])|(?:[1-9]|10)|(?:9\.3|9\.6))")
RPE_MULTISET_SCHEME = fr"(?P<multi_rpe>(?:@{RPE_SCHEME}){{2,}})"
WEIGHT_SCHEME = (r"(?:(?P<weight>[0-9]+(?:[.,][0-9]{1,3})?)"
                 r"(?i)(?P<unit>kg|lbs|bw)?|(?P<bw>BW))")
WEIGHT_NO_GUESS_SCHEME = (
    r"(?:(?P<weight>[0-9]+(?:\.[0-9]{1,3})?)"
    r"(?i)(?P<unit>kg|lbs|bw)|(?P<bw>BW))"
)    # TODO check where this specific one is needed (to avoid conflicts)
PERCENTAGE_SCHEME = r"(?P<percentage>[1-9][0-9]?|100)"
REPS_SCHEME = r"(?P<reps>[0-9]+)"
SETS_SCHEME = r"(?P<sets>[0-9]+)"


class SetType(Enum):    # Likely TODO split this into planned and done
    NONE = -1    # Placehodler for unimplemented
    RPE = 0
    WEIGHT = 1    # KGs
    PERCENT_1RM = 2    # self explanatory
    LOAD_DROP = 3   # repeats at given percentage of previous set,
    # better named RELATIVE_WEIGHT or smth
    FATIGUE_PERCENT = 4    # repeats until reaching RPE of the top set (previous set)
    RPE_RAMP = 5    # to remove?
    DONE = 6    # Boolean - just done one set with no additional info
    DONE_ALL = 7    # Done all sets as planned
    ERROR = 8    # Failed parsing


SCHEMES_PLANNED = (
    (re.compile(fr"^x{REPS_SCHEME}@{RPE_SCHEME}$"), SetType.RPE),    # x5@9 REPS at RPE
    (re.compile(fr"^{SETS_SCHEME}x{REPS_SCHEME}@{PERCENTAGE_SCHEME}%$"),
     SetType.LOAD_DROP),  # That one is used all the time
    # 5x5@90% SETS of REPS at PERCENTAGE of previous set (top set)
    (re.compile(fr"^{SETS_SCHEME}x{REPS_SCHEME}@{PERCENTAGE_SCHEME}%1?RM$"),
     SetType.PERCENT_1RM),    # 5x5@90%RM SETS of REPS at PERCENTAGE of 1RM
    (re.compile(fr"^{PERCENTAGE_SCHEME}%(1RM|RM)?@{RPE_SCHEME}$"),
     SetType.PERCENT_1RM),  # 80%@8 PERCENTAGE at RPE
    (re.compile(fr"^x{REPS_SCHEME}{RPE_MULTISET_SCHEME}$"),
     SetType.RPE),  # x5@8@9 REPS at RPE multiple #needs furhter processing
    (re.compile(fr"^{SETS_SCHEME}x{REPS_SCHEME}\^@{RPE_SCHEME}$"),
     SetType.RPE),  # 8x1^@7
    (re.compile(fr"^{SETS_SCHEME}x@{RPE_SCHEME}$"),
     SetType.RPE),    # 3x@9 number of SETS at RPE
    (re.compile(fr"^{PERCENTAGE_SCHEME}%x{REPS_SCHEME}$"),    # 80%x5 REPS at %1RM
     SetType.PERCENT_1RM,),
    (re.compile(fr"^{SETS_SCHEME}x{REPS_SCHEME}V{PERCENTAGE_SCHEME}%$"),
     SetType.LOAD_DROP),  # 3x3V90% SETS of REPS at PERCENTAGE may TODO remove
    (re.compile(fr"^x{REPS_SCHEME}\$@{RPE_SCHEME}$"),
     SetType.RPE_RAMP),  # 5$@9
    (re.compile(fr"^{SETS_SCHEME}x{REPS_SCHEME}$"),
     SetType.DONE),   # 3x8 SETS of REPS starting at RPE,
    (re.compile(fr"^x{REPS_SCHEME}@{RPE_SCHEME}\-{PERCENTAGE_SCHEME}%$"),
     SetType.FATIGUE_PERCENT),  # x4@9-7% SETS of REPS starting at RPE
    (re.compile(fr"^{WEIGHT_SCHEME}@{RPE_SCHEME}$"),
     SetType.RPE),  # 160lbs@9 SETS of REPS starting at RPE
    (re.compile(fr"^{WEIGHT_SCHEME}/{REPS_SCHEME}$"),
     SetType.WEIGHT),    # 150/5 SETS of REPS starting at RPE
    (re.compile(fr"^{SETS_SCHEME}[xX]$"),
     SetType.DONE),    # Just number of sets, eg. '5x'. For low priority exercises
)
SCHEMES_DONE = (
    (re.compile(fr"^{WEIGHT_SCHEME}x{REPS_SCHEME}@{RPE_SCHEME}$"),
     SetType.WEIGHT),    # weightXreps at RPE
    (re.compile(fr"^{WEIGHT_SCHEME}@{RPE_SCHEME}$"),
     SetType.WEIGHT),    # 'weight at RPE (presumed same set number as planned)',
    (re.compile(fr"^{WEIGHT_SCHEME}{RPE_MULTISET_SCHEME}$"),
     SetType.WEIGHT),    # Multiple Weight@Rpe sets written in one string
    (re.compile(fr"^{WEIGHT_SCHEME}x{REPS_SCHEME}{RPE_MULTISET_SCHEME}$"),
     SetType.WEIGHT),    # Multiple WeightXReps@Rpe sets written in one string
    (re.compile(fr"^{SETS_SCHEME}x{REPS_SCHEME}(?:\/){WEIGHT_SCHEME}@{RPE_SCHEME}$"),
     SetType.WEIGHT,),  # eg. 5x3/120kg@5. TODO remove?
    (re.compile(fr"^{SETS_SCHEME}x{REPS_SCHEME}(?:\/|x){WEIGHT_SCHEME}$"),
     SetType.WEIGHT,),  # eg. 5x3x120kg. TODO remove?
    (re.compile(r"^ *(?P<undone>[Xx]?) *$"), SetType.DONE),    # exercise not done
    (re.compile(r"^\s*(?P<done>[V])\s*$"), SetType.DONE_ALL),    # Done, V for each set
    (re.compile(r"^\s*(?P<done>[v]+|[V]{2,})\s*$"),
     SetType.DONE),    # Done, V for each set, parse by len(?)
    (re.compile(fr"^{WEIGHT_SCHEME}[Xx:](?P<done>[Vv]+)$"),
     SetType.WEIGHT),
    # Kilograms done for as many sets as "v's" after weight
    # eg. 40kgxVVVVV, reps presumed as planned
    # TODO legit support for this and related in matched set parser
    (re.compile(fr"^(?P<multi_reps>(?:{REPS_SCHEME}(?:,|@))+){WEIGHT_SCHEME}$"),
     SetType.WEIGHT),  # 10,10,10,8,6@100kg Multiple sets at given weight
    (re.compile(fr"^{REPS_SCHEME}x{WEIGHT_SCHEME}$"),    # Reps at weight
     SetType.WEIGHT),
    (re.compile(fr"^x{REPS_SCHEME}@{RPE_SCHEME}$"),    # Reps at rpe, relative wegiht
     SetType.LOAD_DROP),
    (re.compile(fr"^x{REPS_SCHEME}{RPE_MULTISET_SCHEME}$"),
     SetType.LOAD_DROP),  # Reps at rpe, relative wegiht, many sets
)
