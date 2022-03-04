from email.mime import base
import colorama

colorama.init()
import gspread
import re
import pprint
from collections import namedtuple
from colorama import Fore, Back, Style
from enum import Enum
from typing import List
from utils import calculate_e1RM, get_percentage, calculate_inol
from schemes import *
import logging

logging.basicConfig(
    filename="pla.log",
    format="%(levelname)s:%(name)s:%(lineno)s - %(funcName)20s()  %(message)s",
    level=logging.DEBUG,
    filemode="w",
)
logger = logging.getLogger(__name__)


class WeightUnit(Enum):
    KG = 1
    LBS = 2
    BW = 3
    PERCENT_1RM = 4
    PERCENT_TOPSET = 5


class Exercise:

    DefaultUnit = WeightUnit.KG
    Weight = namedtuple("Weight", ("value", "unit"))
    Set = namedtuple("Set", ("type", "reps", "weight", "rpe"))

    def __init__(self, planned_str, done_str, notes):
        logger.debug(SetType.RPE)
        logger.debug(SetType)

        self.done = True
        self.is_superset = False  # TODO remove this if _next_parallel keeps the info
        # only problem is with last superset exercise not knowing it's in superset
        self._next_parallel_exercise = None
        self._workout_from_string(planned_str, done_str)
        self.notes = notes

        if self.done:
            self.e1RM = self.get_e1RM()
            self.vol_planned = self.volume_planned()
            self.vol_done = self.volume_done()
            self.inol = self.inol_planned()
        else:
            self.e1RM = 0
            self.vol_planned = 0
            self.vol_done = 0
            self.inol = 0

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
                max([
                    calculate_e1RM(ws.weight.value, ws.reps, ws.rpe)
                    for ws in e
                ]) for e in self.sets_done
            ]
            return x
        x = max([
            calculate_e1RM(ws.weight.value, ws.reps, ws.rpe)
            for ws in self.sets_done if ws.weight.value and ws.reps and ws.rpe
        ], default=0)
        return x

    def _workout_from_string(self, first_col_str, second_col_str):
        # First column contains exercise with modifiers and planned sets,
        # second column contains done sets
        logger.debug("PARSING WORKOUT" + "-" * 20)
        logger.debug(
            f"first_col_str: {first_col_str}; second_col_str: {second_col_str}"
        )
        exercise_str, planned_str = first_col_str.split(":")
        if "&" in exercise_str:  # Superset manual handling
            logger.debug(f"Found superset sign in {exercise_str}")
            self.is_superset = True
            exercise_strs = exercise_str.split("&", 1)
            # Maybe just reduce code by acknowledging the superset and
            # letting the normal workflow take over
            if "&" in planned_str:
                planned_strs = planned_str.split("&", 1)
            else:
                planned_strs = [planned_str,
                                planned_str]  #this idiocy twice...
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
                self.name, self.modifiers = self._exercise_from_string(
                    exercise_strs[0])
                self.sets_planned = self._sets_planned_from_string(
                    planned_strs[0])
                self.sets_done = self._match_sets_planned_done(
                    self._sets_done_from_string(second_col_strs[0]))
                self._sets_done_connect_relative_weight()

            # Create new Exercise object with strings stripped from data leftmost of &
            self._next_parallel_exercise = Exercise(
                f"{exercise_strs[1]}:{planned_strs[1]}",
                second_col_strs[1],
                "",
            )
            return

        self.name, self.modifiers = self._exercise_from_string(exercise_str)
        self.sets_planned = self._sets_planned_from_string(planned_str)
        self.sets_done = self._match_sets_planned_done(
            self._sets_done_from_string(second_col_str))
        self._sets_done_connect_relative_weight()

    def _exercise_from_string(self, exercise_str):
        logger.debug(f"Parsing exercise from {exercise_str}")
        modifier_schemes = (
            re.compile(" w/(?P<with>[a-zA-Z0-9_']+)"),  #'with x',
            re.compile(" t/(?P<tempo>\d{4})"),  #'tempo XXXX',
            re.compile(" wo/(?P<without>[a-zA-Z0-9_']+)"),  #'without x',
            re.compile(" p/(?P<pattern>[a-zA-z0-9_']+)"),
        )  #'movement patter mod'

        name = exercise_str
        modifiers = [pattern.findall(name) for pattern in modifier_schemes]
        logging.debug(f"Modifiers: {modifiers}")
        # TODO normal data structure for modifier, eg dict
        for m in modifiers:
            for k in m:  # Remove modifiers from name
                name = re.sub(f" \w+/{k}(?: |$)", " ", name)
        # why was there rstrip instead of strip()? It should work
        return (name.strip(), modifiers)

    def _sets_done_from_string(self, sets_str):
        logger.debug(f"-----------Parsing sets done from {sets_str}")
        start_time, sets_str, end_time = (lambda m: (
            m["start"],
            m["sets"],
            m["end"],
        ))(re.match("^(?P<start>[^)]*\))?(?P<sets>[^(]*)(?P<end>\(.*)?$",
                    sets_str))
        logger.debug(
            f"Splitting time from sets done: {start_time};; {sets_str};; {end_time}"
        )
        sets_str = list(
            filter(lambda x: x != '', re.split(" |;", sets_str.strip())))
        sets_done = []
        if sets_str == []:
            self.done = False
            return []  # return sets_done := []
        for set_str in sets_str:
            logger.debug(f'Parsing while round for "{set_str}"')
            try:
                match = [(pattern[0].match(set_str), index + 1, pattern[1])
                            for index, pattern in enumerate(SCHEMES_DONE)
                            if pattern[0].match(set_str)][0]
                logging.debug(f"Done: {sets_str}, {set_str}, "
                                f"match={match}, groups={match[0].groups()}")
            except IndexError as e:
                logger.exception(e)
                logger.info(
                    f"Failed to match set {set_str} with any of schemes")
                match = ('error', set_str)
            sets_done.extend(self._parse_matched_set(match))
            # these are TMP and suck
            if sets_done == [ 0, ]:
                self.done = False
                sets_done = []
                break

        logger.debug("Finish sets_done_from_string-----------")
        return sets_done

    def _sets_planned_from_string(self, sets_planned_str):
        logger.debug(
            f"----------- Parsing sets planned from {sets_planned_str}")

        sets_planned = []
        sets_planned_str = sets_planned_str.strip()
        if sets_planned_str == "":
            return []
        logging.debug("sets planned str:" + sets_planned_str + "/")
        sets_str = re.split(" |;", sets_planned_str.strip())
        logging.debug(sets_str)
        for set_str in sets_str:
            logger.debug(f"Parsing while round for {set_str}")
            try:
                match = [(pattern[0].match(set_str), index + 1, pattern[1])
                            for index, pattern in enumerate(SCHEMES_PLANNED)
                            if pattern[0].match(set_str)][0]
                logger.info(f"Planned: {sets_str}, {set_str}, "
                            f"match={match}, groups={match[0].groups()}")
            except IndexError as e:
                logger.exception(e)
                logger.debug(
                    f"Failed to match set {set_str} with any of schemes")
                match = ('error', set_str)

            sets_planned.extend(self._parse_matched_set(match))
        logger.debug("Finish sets_planned_from_string-----------")
        return sets_planned

    def _parse_matched_set(self, match):
        # This whole shit needs refactoring
        # Hard to get what is going on here
        # Maybe legit parser, like parser instead of regexes would really make sense
        if match[0] == 'error':
            return (self.Set(SetType.ERROR, None, self.Weight(None, None), None),)
        groupdict = match[0].groupdict()
        # TODO rewrite these exceptions into normal Set() object
        # This shit shouldn't even be here but with the rest of the groups
        if "undone" in groupdict:
            return (0, )
        logger.debug(f"groupdict for :{match}: {groupdict}"
                     )  # wtf is this even,dont remember
        sets = []
        # So we generate a dict based on matched groups by regexps
        getdict = {
            "set_type":
            match[2],
            "reps":
            int(match[0].group("reps").replace(",", "."))
            if "reps" in groupdict else None,
            "sets":
            int(match[0].group("sets").replace(",", "."))
            if "sets" in groupdict else None,
            "rpe": (float(match[0].group("rpe").replace(",", ".").replace(
                "(", "").replace(")", "")) if "rpe" in groupdict else None),
            "weight":
            (float(match[0].group("weight").replace(",", ".")) if
             "weight" in groupdict and groupdict["weight"] != None else None),
            "percentage":
            (float(match[0].group("percentage").replace(",", ".")) /
             100.0 if "percentage" in groupdict else None),
            "multi_rpe":
            match[0].group("multi_rpe").split("@")[1:]
            if "multi_rpe" in groupdict else None,
            "multi_reps":
            match[0].group("multi_reps").strip("@").split(",")
            if "multi_reps" in groupdict else None,
            "done":
            match[0].group("done").replace(" ", "")
            if "done" in groupdict else None,
        }
        logger.debug(f'getdict is {getdict}')
        # Then based on these groups we set values that
        # These are used for basic values that need no advanced parsing
        # like multisets/multiRPEs etc
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
                getdict["unit"] = WeightUnit.PERCENT_TOPSET
            elif getdict["set_type"] == SetType.FATIGUE_PERCENT:
                getdict["unit"] = None
            else:
                raise StandardError("Unsupported Set Type for percentage")
        elif getdict["set_type"] == SetType.LOAD_DROP:
            getdict["unit"] = WeightUnit.PERCENT_TOPSET
            getdict["percentage"] = 1.0
        elif getdict["done"] and len(getdict["done"]) == 1:
            getdict["set_type"] == SetType.DONE_ALL
        # So here we handle the cases of multisets if necessary and at
        # the end we append that to return object
        if "sets" in groupdict:
            for i in range(0, getdict["sets"]):
                _set = self.create_set_object(**getdict)
                sets.append(_set)
                if getdict["set_type"] == SetType.RPE:
                    if "unit" in getdict and getdict["unit"] == WeightUnit.BW:
                        continue
                    getdict.update({
                        "percentage": 1.0,
                        "unit": WeightUnit.PERCENT_TOPSET,
                        "rpe": None,
                        "set_type": SetType.LOAD_DROP,
                    })
                    continue
                if getdict["set_type"] == SetType.LOAD_DROP:
                    getdict["unit"] = WeightUnit.PERCENT_TOPSET
        elif "multi_rpe" in groupdict:
            for rpe in getdict["multi_rpe"]:
                getdict["rpe"] = float(
                    rpe.replace(",", ".").replace("(", "").replace(")", ""))
                # are passed to sets
                _set = self.create_set_object(**getdict)
                sets.append(_set)
        elif "multi_reps" in groupdict:
            for reps in getdict["multi_reps"]:
                getdict["reps"] = int(reps)
                # are passed to sets
                _set = self.create_set_object(**getdict)
                sets.append(_set)
        elif getdict["done"] and len(getdict["done"]) > 1:
            logger.debug(f'Found set of type done multiset: {getdict["done"]}')
            sets.extend(
                self.create_set_object(**getdict)
                for _ in range(len(getdict["done"])))
        else:
            # are passed to sets
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
        w = self.Weight(
            weight if weight else percentage if percentage else None, unit)
        return self.Set(set_type, reps, w, rpe)

    def _match_sets_planned_done(self, done):
        """
        If len() of done and planned sets is the same and there are no rep ranges on done
        sets then presume that done_set[i] corresponds to planned_set[i]
        While this may not seem as the cleanest solution I use it in practice all the time
        inside my spreadsheets.
        """
        if not len(done) == len(self.sets_planned):
            return done
        if not all([s.reps == None for s in done]):
            return done
        new_sets_done = []
        for p, d in zip(self.sets_planned, done):
            new_sets_done.append(self.Set(d.type, p.reps, d.weight, d.rpe))
        return new_sets_done

    def _sets_done_connect_relative_weight(self):
        """
        If set with type LOAD_DROP (TODO change it) found in sets_done then
        set it's weight to first weighted set before it.
        """
        for i, s in enumerate(self.sets_done):
            if s.type != SetType.LOAD_DROP:
                continue
            if self.sets_done[i-1].type != SetType.WEIGHT:
                continue
            self.sets_done[i] = self.Set(SetType.WEIGHT, s.reps, self.sets_done[i-1].weight, s.rpe)
                
    def volume_planned(self):
        """
        relative volume (as %1RM) 
        """
        vol = 0
        base_percentage = None
        for (i, s) in enumerate(self.sets_planned):
            if base_percentage and s.weight.unit != WeightUnit.PERCENT_TOPSET:
                base_percentage = None
            if s.reps and s.weight.unit in (WeightUnit.KG, WeightUnit.LBS):
                continue #skip normal volume for now, just do relative vol from RPE
                vol += s.reps * s.weight.value
            if s.reps and s.rpe:
                vol += get_percentage(s.reps, s.rpe)*s.reps 
            if s.weight.unit == WeightUnit.PERCENT_TOPSET:
                if base_percentage == None:
                    base_percentage = get_percentage(self.sets_planned[i-1].reps,
                                                    self.sets_planned[i-1].rpe)
                vol += base_percentage*s.weight.value*s.reps
                
        return round(vol, 1)

    def inol_planned(self):
        inol = 0.0
        base_percentage = None
        for (i, s) in enumerate(self.sets_planned):
            if base_percentage and s.weight.unit != WeightUnit.PERCENT_TOPSET:
                base_percentage = None
            if s.reps and s.weight.unit in (WeightUnit.KG, WeightUnit.LBS):
                continue #skip normal volume for now, just do relative vol from RPE
            if s.reps and s.rpe:
                inol += calculate_inol(s.reps, get_percentage(s.reps, s.rpe)) 
            if s.weight.unit == WeightUnit.PERCENT_TOPSET:
                if base_percentage == None:
                    base_percentage = get_percentage(self.sets_planned[i-1].reps,
                                                     self.sets_planned[i-1].rpe)
                inol += calculate_inol(s.reps, base_percentage*s.weight.value)
                
        return round(inol, 2)



    def volume_done_relative(self):
        # TODO remove as unnecessary? (just divide vol by e1RM)
        if not self.e1RM:
            return 0
        vol = 0.0
        for s in self.sets_done:
            pass

    def volume_done(self):
        vol = 0.0
        for s in self.sets_done:
            if s.reps and s.weight.value:
                vol += s.reps * s.weight.value
        return vol

    def __repr__(self):
        return f"{self.name}"

    def __str__(self):
        if self.done:
            logger.debug(f"{self.name}: {self.sets_done}")
            if len(self.sets_done
                   ) == 1 and self.sets_done[0].type == SetType.DONE_ALL:
                sets_done = (f"{Fore.GREEN}V(all){Fore.RESET}", )
            else:
                sets_done = [
                    (f"{Fore.RED}{s.weight.value or ''}{Fore.RESET}"
                     f"x{Fore.LIGHTYELLOW_EX}{s.reps or ''}{Fore.RESET}"
                     f"@{Fore.LIGHTGREEN_EX}{s.rpe or ''}{Fore.RESET}")
                    for s in self.sets_done
                ]
        else:
            sets_done = [
                f"{Fore.LIGHTRED_EX} X {Fore.RESET}",
            ]
        sets_planned = [(f"{Fore.RED}{s.weight.value or ''}{Fore.RESET}"
                         f"x{Fore.LIGHTYELLOW_EX}{s.reps or ''}{Fore.RESET}"
                         f"@{Fore.LIGHTGREEN_EX}{s.rpe or ''}{Fore.RESET}")
                        for s in self.sets_planned]
        e1RM = f'|{Fore.MAGENTA} e1RM: {self.e1RM}{Fore.RESET}' if self.e1RM else ''
        vol_planned = f'|{Fore.GREEN} vol_p: {self.vol_planned}%{Fore.RESET}' if self.vol_planned else ''
        vol_done = f'|{Fore.GREEN} vol_d: {self.vol_done}kg{Fore.RESET}' if self.vol_done else ''
        vol_done_relative = f'|{Fore.RED} vol_d%: {round(100*self.vol_done/self.e1RM, 1)}%{Fore.RESET}' if self.vol_done and self.e1RM else ''
        inol = f'|{Fore.CYAN} inol: {self.inol}{Fore.RESET}|' if self.inol else ''
        ret = (f'{Fore.RED}{self.name}{inol}{Fore.RESET}: '
               f'{" ".join(sets_planned)} {Back.BLUE}|{Back.RESET} '
               f'{" ".join(sets_done)} {e1RM} {vol_planned} {vol_done} {vol_done_relative}')
        if self._next_parallel_exercise:
            return ret + str(self._next_parallel_exercise)
        return ret + '\n'


class Session:

    def __init__(self, exercises: List[Exercise], date: str):
        self.exercises = exercises
        self.date = date

    def __str__(self):
        ret = f"{Back.BLUE}Session from {self.date}{Back.RESET}\n"
        for e in self.exercises:
            ret += str(e)
        return ret + "\n"


class Microcycle:

    def __init__(self, sessions: List[Session]):
        self.sessions = sessions

    def __str__(self):
        ret = f"{Back.GREEN}Microcycle: {Back.RESET}\n"
        for s in self.sessions:
            ret += str(s)
        return ret + "\n"


class Mesocycle:

    def __init__(self, microcycles: List[Microcycle]):
        self.microcycles = microcycles

    def __str__(self):
        ret = f"{Fore.BLACK}{Back.YELLOW}Mesocycle: {Back.RESET}{Fore.RESET}\n"
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
                planned_cells = [
                    i for i in c if i.col == x.col and i.row >= x.row
                ]
                done_cells = [
                    i for i in c if i.col == x.col + 1 and i.row >= x.row
                ]
                session = get_session(planned_cells, done_cells)
                sessions.append(session)
        micros.append(Microcycle(sessions))
    return micros


def get_mesocycle(block, last_row):
    mesocycles = []
    pattern = re.compile("^[Ww][0-9]+")
    # for i, b in enumerate(blocks):
    micro_a1 = (gspread.utils.rowcol_to_a1(block.row, block.col) + ":" +
                gspread.utils.rowcol_to_a1(last_row, G_WIDTH))
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
                    meso_range[W_row:i - 1]
                )  # Save microcycles from former week row to row before current
            W_row = i
        if i == len(meso_range) - 1 and W_row:  # If we reach the end of sheet
            weeks_split.append(meso_range[W_row:i - 1])
    # logger.debug(weeks_split)
    micros = get_microcycles(weeks_split)
    return Mesocycle(micros)


if __name__ == "__main__":
    gc = gspread.oauth(credentials_filename="secret.json", )
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
        last_row = blocks[i+1].row - 1 if i + 1 < len(blocks) else G_HEIGHT - 1
        mesocycles.append(get_mesocycle(block, last_row))
    #breakpoint()
    for m in mesocycles:
        print(m)
