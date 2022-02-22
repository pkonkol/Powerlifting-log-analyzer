import gspread
import re
from collections import namedtuple
from enum import Enum
from pprint import pprint
from typing import List
from utils import calculate_e1RM
import logging

logging.basicConfig(
    filename="pla.log",
    format="%(levelname)s:%(name)s:%(lineno)s  %(message)s",
    level=logging.DEBUG,
    filemode="w",
)
logger = logging.getLogger(__name__)


RPE_SCHEME = (
    "(?P<rpe>(?:[1-9](?:,|\.)[5])|(?:[1-9]|10)|(?:9\.\(3\)|9\.3|9\.\(6\)|9\.6))"
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


class WeightUnit(Enum):
    KG = 1
    LBS = 2
    BW = 3
    PERCENT_1RM = 4
    PERCENT_TOPSET = 5


class Exercise:

    DefaultUnit = WeightUnit.KG
    Weight = namedtuple(
        "Weight",
        (
            "value",
            "unit",
        ),
    )
    Set = namedtuple("Set", ("type", "reps", "weight", "rpe"))

    def __init__(self, planned_str, done_str, notes):
        logger.debug(SetType.RPE)
        logger.debug(SetType)

        self.done = True
        self.is_superset = False # TODO remove this if _next_parallel keeps the info
        self._next_parallel_exercise = None
        self.workout_from_string(planned_str, done_str)
        self.notes = notes

        if self.done:
            self.e1RM = self.get_e1RM()
        else:
            self.e1RM = 0

    def get_e1RM(self):
        logger.debug(self.name)
        logger.debug(self.sets_done)
        logger.debug((ws for ws in self.sets_done))
        if (self.is_superset 
#TMP fix, TODO if done there are always sets (fails on superset)
# "vvvvv" done pattern not matched correctly
# may jus throw this away for supersets anyway, i do just easy supplemental work
# on supersets anyway
            or self.sets_done == []): 
            return 0
            x = [
                max([calculate_e1RM(ws.weight.value, ws.reps, ws.rpe) for ws in e])
                for e in self.sets_done
            ]
            return x
        x = max(
            [calculate_e1RM(ws.weight.value, ws.reps, ws.rpe) for ws in self.sets_done]
        )
        return x

    def workout_from_string(self, first_col_str, second_col_str):
        # First column contains exercise with modifiers and planned sets,
        # second column contains done sets
        logger.debug("PARSING WORKOUT" + "-" * 20)
        logger.debug(
            f"first_col_str: {first_col_str}; second_col_str: {second_col_str}"
        )
        exercise_str, planned_str = first_col_str.split(":")
        if "&" in exercise_str:
            logger.debug(f"Found superset sign in {exercise_str}")
            self.is_superset = True
            exercise_strs = exercise_str.split("&", 1)
            # Maybe just reduce code by acknowledging the superset and
            # letting the normal workflow take over
            if "&" in planned_str:
                planned_strs = planned_str.split("&", 1)
            else:
                planned_strs = [planned_str, planned_str] #this idiocy twice...
            if "&" in second_col_str:
                second_col_strs = second_col_str.split("&", 1)
                second_col_strs = [s.strip() for s in second_col_strs]
            else:
                # Retarded but it integrates with less if's with split on & (^^^)
                # TODO write it well
                second_col_strs = [second_col_str, second_col_str]

            if self._next_parallel_exercise == None:
                logger.debug(f"No _next_parallel_exercise for {exercise_strs}"
                             f";; {planned_strs};; {second_col_strs}")
                name, modifiers = self.exercise_from_string(exercise_strs[0])
                self.name = name
                self.modifiers = modifiers
                self.sets_planned = self.sets_planned_from_string(planned_strs[0])
                self.sets_done = self.sets_done_from_string(second_col_strs[0])

            # Create new Exercise object with strings stripped from data leftmost of &
            self._next_parallel_exercise = Exercise(
                f"{exercise_strs[1]}:{planned_strs[1]}",
                second_col_strs[1],
                "",
            )
            return

        self.name, self.modifiers = self.exercise_from_string(exercise_str)
        self.sets_planned = self.sets_planned_from_string(planned_str)
        self.sets_done = self.sets_done_from_string(second_col_str)

    def exercise_from_string(self, exercise_str):
        logger.debug(f"Parsing exercise from {exercise_str}")
        modifier_schemes = (
            re.compile(" w/(?P<with>[a-zA-Z0-9]+)"),  #'with x',
            re.compile(" t/(?P<tempo>\d{4})"),  #'tempo XXXX',
            re.compile(" wo/(?P<without>[a-zA-Z0-9]+)"),  #'without x',
            re.compile(" p/(?P<pattern>[a-zA-z0-9]+)"),
        )  #'movement patter mod'

        name = exercise_str
        modifiers = [pattern.findall(name) for pattern in modifier_schemes]
        logging.debug(f"Modifiers: {modifiers}")

        for m in modifiers:
            for k in m:
                name = re.sub(f" \w+/{k}(?: |$)", " ", name)

        # why was there rstrip instead of strip()? It should work
        return (name.strip(), modifiers)

    def sets_done_from_string(self, sets_str):
        logger.debug(f"-----------Parsing sets done from {sets_str}")
        start_time, sets_str, end_time = (
            lambda m: (
                m["start"],
                m["sets"],
                m["end"],
            )
        )(re.match("^(?P<start>[^)]*\))?(?P<sets>[^(]*)(?P<end>\(.*)?$", sets_str))
        logger.debug(
            f"Splitting time from sets done: {start_time};; {sets_str};; {end_time}"
        )
        sets_str = re.split(" |;", sets_str.strip())
        for set_str in sets_str:
            while True:
                logger.debug(f'Parsing while round for "{set_str}"')
                try:
                    match = [
                        (pattern[0].match(set_str), index + 1, pattern[1])
                        for index, pattern in enumerate(SCHEMES_DONE)
                        if pattern[0].match(set_str)
                    ][0]
                except IndexError as e:
                    logger.exception(e)
                    logger.info(f"Failed to match set {set_str} with any of schemes")
                    break
                break
            logging.debug(
                f"Done: {sets_str}, {set_str}, "
                f"match={match}, groups={match[0].groups()}"
            )

        sets_done = self.parse_matched_set(match)
        if sets_done == (0,):
            self.done = False
            sets_done = []
        elif sets_done == (1,):
            self.done = True
            sets_done = []

        logger.debug("Finish sets_done_from_string-----------")
        return sets_done

    def sets_planned_from_string(self, sets_planned_str):
        logger.debug(f"----------- Parsing sets planned from {sets_planned_str}")

        sets_planned_str = sets_planned_str.strip()
        if sets_planned_str == "":
            return []
        logging.debug("sets planned str:" + sets_planned_str + "/")
        sets_str = re.split(" |;", sets_planned_str.strip())
        logging.debug(sets_str)
        for set_str in sets_str:
            while True:
                logger.debug(f"Parsing while round for {set_str}")
                try:
                    match = [
                        (pattern[0].match(set_str), index + 1, pattern[1])
                        for index, pattern in enumerate(SCHEMES_PLANNED)
                        if pattern[0].match(set_str)
                    ][0]
                except IndexError as e:
                    logger.exception(e)
                    logger.debug(f"Failed to match set {set_str} with any of schemes")
                    break
                break
            logger.info(
                f"Planned: {sets_str}, {set_str}, "
                f"match={match}, groups={match[0].groups()}"
            )

        sets_planned = self.parse_matched_set(match)
        logger.debug("Finish sets_planned_from_string-----------")
        return sets_planned

    def parse_matched_set(self, match):
        groupdict = match[0].groupdict()
        if "undone" in groupdict:
            return (0,)
        if "done" in groupdict:
            return (1,)

        logger.debug(f"groupdict: {groupdict}")  # wtf is this even,dont remember
        sets = []

        getdict = {
            "set_type": match[2],
            "reps": int(match[0].group("reps").replace(",", "."))
            if "reps" in groupdict
            else None,
            "sets": int(match[0].group("sets").replace(",", "."))
            if "sets" in groupdict
            else None,
            "rpe": (
                float(
                    match[0]
                    .group("rpe")
                    .replace(",", ".")
                    .replace("(", "")
                    .replace(")", "")
                )
                if "rpe" in groupdict
                else None
            ),
            "weight": (
                float(match[0].group("weight").replace(",", "."))
                if "weight" in groupdict and groupdict["weight"] != None
                else None
            ),
            "percentage": (
                float(match[0].group("percentage").replace(",", ".")) / 100.0
                if "percentage" in groupdict
                else None
            ),
            "multi_rpe": match[0].group("multi_rpe").split("@")[1:]
            if "multi_rpe" in groupdict
            else None,
            "multi_reps": match[0].group("multi_reps").strip("@").split(",")
            if "multi_reps" in groupdict
            else None,
        }
        logger.debug(getdict)

        if getdict["weight"]:
            matched_unit = match[0].group("unit")
            if matched_unit == "kg":
                getdict["unit"] = WeightUnit.KG
            elif matched_unit == "lbs":
                getdict["unit"] = WeightUnit.LBS
            else:
                getdict["unit"] = self.DefaultUnit
        elif "bw" in groupdict and groupdict["bw"] == "BW":
            getdict["unit"] = WeightUnit.BW
        elif getdict["percentage"]:
            if getdict["set_type"] == SetType.PERCENT_1RM:
                getdict["unit"] = WeightUnit.PERCENT_1RM
            elif getdict["set_type"] == SetType.LOAD_DROP:
                getdict["unit"] = -1
            elif getdict["set_type"] == SetType.FATIGUE_PERCENT:
                getdict["unit"] = None
            else:
                raise StandardError("Unsupported Set Type for percentage")

        if "sets" in groupdict:
            for i in range(0, getdict["sets"]):
                _set = self.create_set_object(**getdict)
                sets.append(_set)

                if getdict["set_type"] == SetType.RPE:
                    if "unit" in getdict and getdict["unit"] == WeightUnit.BW:
                        continue
                    getdict.update(
                        {
                            "percentage": 1.0,
                            "unit": -1,
                            "rpe": None,
                            "set_type": SetType.LOAD_DROP,
                        }
                    )
                    continue

                if getdict["set_type"] == SetType.LOAD_DROP:
                    getdict["unit"] -= 1
        elif "multi_rpe" in groupdict:
            for rpe in getdict["multi_rpe"]:
                getdict["rpe"] = float(
                    rpe.replace(",", ".").replace("(", "").replace(")", "")
                )
                _set = self.create_set_object(**getdict)
                sets.append(_set)
        elif "multi_reps" in groupdict:
            for reps in getdict["multi_reps"]:
                getdict["reps"] = int(reps)
                _set = self.create_set_object(**getdict)
                sets.append(_set)
        else:
            _set = self.create_set_object(**getdict)
            sets.append(_set)

        return sets

    def create_set_object(
        self,
        set_type=None,
        reps=None,
        rpe=None,
        weight=None,
        percentage=None,
        unit=None,
        **kwargs,
    ):
        w = self.Weight(weight if weight else percentage if percentage else None, unit)
        return self.Set(set_type, reps, w, rpe)

    def match_sets_planned_done(self):
        """
        If len() of done and planned sets is the same and there are no rep ranges on done
        sets then presume that done_set[i] corresponds to planned_set[i]
        TODO soon
        """
        pass

    def volume(self):
        vol = 0.0
        if not self.is_superset:
            for s in self.sets_done:
                if s.reps and s.weight.value:
                    vol += s.reps * s.weight.value
            return vol

    def __repr__(self):
        return f"{self.name}"

    def __str__(self):
        if self.done:
            sets_done = [
                f"{s.weight.value or ''}x{s.reps or ''}" f"@{s.rpe or ''}"
                for s in self.sets_done
            ]
        else:
            sets_done = "X"
        sets_planned = [
            f"{s.weight.value or ''}x{s.reps or ''}" f"@{s.rpe or ''}"
            for s in self.sets_planned
        ]
        e1RM = self.e1RM if self.e1RM else 0.0
        if self._next_parallel_exercise:
            return f'\t\t\t{self.name}: {";".join(sets_planned)} | {";".join(sets_done)} & ' + str(self._next_parallel_exercise)
        return f'\t\t\t{self.name}: {";".join(sets_planned)} | {";".join(sets_done)} | e1RM: {e1RM} \n'


class Session:
    def __init__(self, exercises: List[Exercise], date: str):
        self.exercises = exercises
        self.date = date

    def __str__(self):
        ret = f"\t\tSession from {self.date}\n"
        for e in self.exercises:
            ret += str(e)
        return ret + "\n"


class Microcycle:
    def __init__(self, sessions: List[Session]):
        self.sessions = sessions

    def __str__(self):
        ret = f"\tMicrocycle: \n"
        for s in self.sessions:
            ret += str(s)
        return ret + "\n"


class Mesocycle:
    def __init__(self, microcycles: List[Microcycle]):
        self.microcycles = microcycles

    def __str__(self):
        ret = f"Mesocycle: \n"
        for m in self.microcycles:
            ret += str(m)
        return ret + "\n"


def get_exercise(planned_cell, done_cell):
    return Exercise(planned_cell.value, done_cell.value, "")


def get_session(planned_cells, done_cells):
    sessions = []
    exercises = []
    for p, d in zip(planned_cells[1:], done_cells[1:]):
        if p.value == "":
            continue
        exercises.append(get_exercise(p, d))
    date = done_cells[0].value
    return Session(exercises, date)


def get_microcycles(weeks_split):
    micros = []
    pattern = re.compile("^[Dd][0-9]+")  # Ignore GPP column for now
    # breakpoint()
    for c in weeks_split:
        sessions = []
        sessions_row = [e for e in c if e.row == c[0].row]
        logger.debug(sessions_row)
        for x in sessions_row:
            if re.match(pattern, x.value):
                planned_cells = [i for i in c if i.col == x.col and i.row >= x.row]
                done_cells = [i for i in c if i.col == x.col + 1 and i.row >= x.row]
                session = get_session(planned_cells, done_cells)
                sessions.append(session)
        micros.append(Microcycle(sessions))
    return micros


def get_mesocycle(block, last_row):
    mesocycles = []
    pattern = re.compile("^[Ww][0-9]+")
    # for i, b in enumerate(blocks):
    micro_a1 = (
        gspread.utils.rowcol_to_a1(block.row, block.col)
        + ":"
        + gspread.utils.rowcol_to_a1(last_row, G_WIDTH)
    )
    meso_range = wksh.range(micro_a1)
    # logger.debug(meso_range)
    # That code sucks, but works. Done for the need of api usage optimization
    W_row = 0
    weeks_split = []
    # why TF block iterator is here
    for i, c in enumerate(meso_range):
        if re.match(pattern, c.value):
            if W_row:  # If we find a row with W[0-9]
                weeks_split.append(
                    meso_range[W_row : i - 1]
                )  # Save microcycles from former week row to row before current
            W_row = i
        if i == len(meso_range) - 1 and W_row:  # If we reach the end of sheet
            weeks_split.append(meso_range[W_row : i - 1])
    # logger.debug(weeks_split)
    micros = get_microcycles(weeks_split)
    return Mesocycle(micros)


if __name__ == "__main__":
    gc = gspread.oauth(
        credentials_filename="secret.json",
    )
    # sh = gc.open("backup 13.02 Trening 2021-2022")
    sh = gc.open("Trening 2021-2022")

    print(sh.worksheets())
    wksh = sh.worksheet("IDL 2022.02 prep 09.2021-02.2022")
    G_WIDTH = len(wksh.get_all_values()[0]) + 1
    G_HEIGHT = len(wksh.get_all_values()) + 1

    blocks = wksh.findall(re.compile("^[Bb][0-9]+$"), in_column=0)
    mesocycles = []
    for i, block in enumerate(blocks):
        # next_block_row = blocks[i + 1].row - 1 if i + 1 < len(blocks) else G_HEIGHT - 1
        # TODO send mesocycle height to the get_ function
        # change to get_mesocycle that parses only one, move height management to upper level
        last_row = blocks[i + 1].row - 1 if i + 1 < len(blocks) else G_HEIGHT - 1
        mesocycles.append(get_mesocycle(block, last_row))
        break
    # breakpoint()
    print(mesocycles[0])
    logger.info(f"Parsed mesocycle[0]: {mesocycles[0]}")
