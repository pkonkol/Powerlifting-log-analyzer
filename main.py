import argparse
import logging
import re
from collections import namedtuple
from enum import Enum
from typing import List

import colorama
import gspread
from colorama import Back, Fore

from schemes import SCHEMES_DONE, SCHEMES_PLANNED, SetType
from utils import (calculate_e1rm, calculate_inol, get_exercise_aliases,
                   get_percentage, get_stress_index)

parser = argparse.ArgumentParser(description="powerlifting-log-analyzer")
parser.add_argument('--spreadsheet', action='store', type=str,
                    help='Your google spreadsheet\'s name')
parser.add_argument('--worksheet', action='store', type=str,
                    help='The tab in the spreasheet')

colorama.init()

logging.basicConfig(
    filename="pla.log",
    format="%(levelname)s:%(funcName)30s():%(lineno)s  %(message)s",
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
    ExerciseAliases = get_exercise_aliases()
    DefaultUnit = WeightUnit.KG
    Weight = namedtuple("Weight", ("value", "unit"))
    Set = namedtuple("Set", ("type", "reps", "weight", "rpe"))

    def __init__(self, planned_str, done_str, notes):
        self.done = True
        self.is_superset = False  # TODO remove this if _next_parallel keeps the info
        # only problem is with last superset exercise not knowing it's in superset
        self._next_parallel_exercise = None
        self._workout_from_string(planned_str, done_str)
        self.notes = notes

        self.stress_index_done = self.get_stress_index_done()
        self.inol = self.inol_planned()
        self.vol_planned = self.volume_planned()

        if self.done:
            self.e1rm = self.get_e1rm()
            self.vol_done = self.volume_done()
        else:
            self.e1rm = 0
            # self.vol_planned = 0
            self.vol_done = 0
            # self.inol = 0

    def get_e1rm(self):
        # TMP fix, TODO if done there are always sets (fails on superset)
        # "vvvvv" done pattern not matched correctly
        # may jus throw this away for supersets anyway, i do just easy
        # supplemental work on supersets anyway
        if (self.is_superset or not self.sets_done):
            return 0
        e1rm = max([
            calculate_e1rm(ws.weight.value, ws.reps, ws.rpe)
            for ws in self.sets_done
            if ws.weight.value and ws.reps and ws.rpe
        ], default=0)
        return e1rm

    def _workout_from_string(self, first_col_str, second_col_str):
        # First column contains exercise with modifiers and planned sets,
        # second column contains done sets
        logger.debug(f'PARSING WORKOUT {"-"*20}')
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
                                planned_str]  # this idiocy twice...
            if "&" in second_col_str:
                second_col_strs = second_col_str.split("&", 1)
                second_col_strs = [s.strip() for s in second_col_strs]
            else:
                # Retarded but it integrates with less if's with split on & (^^^)
                # TODO write it well
                second_col_strs = [second_col_str, second_col_str]

            if self._next_parallel_exercise is None:
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

    def _exercise_sub_aliases(exercise: str) -> str:
        """Change exercise aliases to exercise basename with modifier """
        unaliased = exercise
        for alias, final in Exercise.ExerciseAliases:
            unaliased = re.sub(alias, final, unaliased, flags=re.IGNORECASE)
        logger.debug(f"cleared {exercise} for aliases into {unaliased}")
        return unaliased

    @staticmethod
    def _exercise_from_string(exercise: str) -> tuple[str, list]:
        exercise = Exercise._exercise_sub_aliases(exercise)
        logger.debug(f"Parsing exercise from {exercise}")
        modifier_schemes = (
            (re.compile(r' w/(?P<with>[a-zA-Z0-9_\']+)'), 'with'),    # 'with x',
            (re.compile(r' t/(?P<tempo>\d{4})'), 'tempo'),    # 'tempo XXXX',
            (re.compile(r' wo/(?P<without>[a-zA-Z0-9_\']+)'),
             'without'),    # 'without x',
            (re.compile(r' p/(?P<pattern>[a-zA-z0-9_\']+)'),
             'pattern'),    # 'movement patter mod'
        )
        modifiers = {
            name: pattern.findall(exercise)
            for pattern, name in modifier_schemes
        }
        logging.debug(f"Modifiers: {modifiers}")
        # TODO normal data structure for modifier, eg dict
        for modifier in modifiers.values():
            for modifier_name in modifier:  # Remove modifiers from name
                exercise = re.sub(fr" \w+/{modifier_name}(?: |$)", " ", exercise)
        # why was there rstrip instead of strip()? It should work
        return exercise.strip(), modifiers

    def _sets_done_from_string(self, sets_str):
        logger.debug(f"-----------Parsing sets done from {sets_str}")
        start_time, sets_str, end_time = (lambda m: (
            m["start"],
            m["sets"],
            m["end"],
        ))(re.match(r"^(?P<start>[^)]*\))?(?P<sets>[^(]*)(?P<end>\(.*)?$", sets_str))
        logger.debug(
            f"Splitting time from sets done: {start_time};; {sets_str};; {end_time}")
        sets_str = list(filter(lambda x: x != '', re.split(" |;", sets_str.strip())))
        sets_done = []
        if not sets_str:
            self.done = False
            return []    # return sets_done := []
        for set_str in sets_str:
            logger.debug(f'Parsing while round for "{set_str}"')
            try:
                match = [(pattern[0].match(set_str), index + 1, pattern[1])
                         for index, pattern in enumerate(SCHEMES_DONE)
                         if pattern[0].match(set_str)][0]
                logging.debug(f"Done: {sets_str}, {set_str}, "
                              f"match={match}, groups={match[0].groups()}")
            except IndexError as err:
                logger.exception(err)
                logger.info(
                    f"Failed to match set {set_str} with any of schemes")
                match = ('error', set_str)
            sets_done.extend(self._parse_matched_set(match))
            # these are TMP and suck
            if sets_done == [0, ]:
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
        logging.debug(f"sets planned str: {sets_planned_str}/")
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
            except IndexError as err:
                logger.exception(err)
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
             "weight" in groupdict and groupdict["weight"] is not None else None),
            "percentage":
            (float(match[0].group("percentage").replace(",", ".")) / 100.0
             if "percentage" in groupdict else None),
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
                raise Exception("Unsupported Set Type for percentage")
        elif getdict["set_type"] == SetType.LOAD_DROP:
            getdict["unit"] = WeightUnit.PERCENT_TOPSET
            getdict["percentage"] = 1.0
        elif getdict["done"] and len(getdict["done"]) == 1:
            getdict["set_type"] = SetType.DONE_ALL
        # So here we handle the cases of multisets if necessary and at
        # the end we append that to return object
        if "sets" in groupdict:
            for _ in range(0, getdict["sets"]):
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
        del kwargs  # Unused, but passed dict may have additional elements
        weight = self.Weight(
            weight if weight else percentage if percentage else None, unit)
        return self.Set(set_type, reps, weight, rpe)

    def _match_sets_planned_done(self, done):
        """
        If len() of done and planned sets is the same and there are no rep
        ranges on done sets then presume that done_set[i] corresponds to
        planned_set[i] While this may not seem as the cleanest solution I use
        it in practice all the time inside my spreadsheets.
        """
        if not len(done) == len(self.sets_planned):
            return done
        if not all((s.reps is None for s in done)):
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
        for i, set_done in enumerate(self.sets_done):
            if set_done.type != SetType.LOAD_DROP:
                continue
            if self.sets_done[i - 1].type != SetType.WEIGHT:
                continue
            self.sets_done[i] = self.Set(SetType.WEIGHT, set_done.reps,
                                         self.sets_done[i - 1].weight, set_done.rpe)

    def volume_planned(self):
        """
        relative volume (as %1RM)
        """
        vol = 0
        base_percentage = None
        for (i, s) in enumerate(self.sets_planned):
            if base_percentage and s.weight.unit != WeightUnit.PERCENT_TOPSET:
                base_percentage = None
            elif s.reps and s.weight.unit in (WeightUnit.KG, WeightUnit.LBS):
                continue  # skip normal volume for now, just do relative vol from RPE
                # vol += s.reps * s.weight.value
            elif s.reps and s.rpe:
                vol += get_percentage(s.reps, s.rpe) * s.reps
            elif s.weight.unit == WeightUnit.PERCENT_TOPSET:
                if base_percentage is None:
                    base_percentage = get_percentage(
                        self.sets_planned[i - 1].reps,
                        self.sets_planned[i - 1].rpe)
                if s.reps and s.weight.value:
                    vol += base_percentage * s.weight.value * s.reps
        return round(vol, 1)

    def inol_planned(self):
        inol = 0.0
        base_percentage = None
        for (i, set_planned) in enumerate(self.sets_planned):
            if base_percentage and set_planned.weight.unit != WeightUnit.PERCENT_TOPSET:
                base_percentage = None
            elif set_planned.reps and set_planned.weight.unit in (WeightUnit.KG,
                                                                  WeightUnit.LBS):
                continue    # skip normal volume for now, just do relative vol from RPE
            elif set_planned.reps and set_planned.rpe:
                inol += calculate_inol(
                    set_planned.reps, get_percentage(set_planned.reps, set_planned.rpe))
            elif set_planned.weight.unit == WeightUnit.PERCENT_TOPSET:
                if base_percentage is None:
                    base_percentage = get_percentage(self.sets_planned[i - 1].reps,
                                                     self.sets_planned[i - 1].rpe)
                if set_planned.reps:
                    inol += calculate_inol(set_planned.reps,
                                           base_percentage * set_planned.weight.value)
        return round(inol, 2)

    def get_stress_index_done(self):
        cs = ps = ts = 0.0
        for s in self.sets_done:
            if not s.rpe or not s.reps:
                continue
            tmp_cs, tmp_ps, tmp_ts = get_stress_index(s.rpe, s.reps)
            cs += tmp_cs
            ps += tmp_ps
            ts += tmp_ts
        return {'cs': cs, 'ps': ps, 'ts': ts}

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
            if len(self.sets_done) == 1 and self.sets_done[0].type == SetType.DONE_ALL:
                sets_done = (f"{Fore.GREEN}V(all){Fore.RESET}", )
            else:
                sets_done = [(
                    f"{Fore.RED}{s.weight.value or ''}{Fore.RESET}"
                    f"x{Fore.LIGHTYELLOW_EX}{s.reps or ''}{Fore.RESET}"
                    f"@{Fore.LIGHTGREEN_EX}{s.rpe or ''}{Fore.RESET}"
                    f"{Back.RED}{'ERR' if s.type == SetType.ERROR else ''}{Back.RESET}"
                ) for s in self.sets_done]
        else:
            sets_done = [
                f"{Fore.LIGHTRED_EX} X {Fore.RESET}",
            ]
        sets_planned = [
            (f"{Fore.RED}{s.weight.value or ''}{Fore.RESET}"
             f"x{Fore.LIGHTYELLOW_EX}{s.reps or ''}{Fore.RESET}"
             f"@{Fore.LIGHTGREEN_EX}{s.rpe or ''}{Fore.RESET}"
             f"{Back.RED}{'ERR' if s.type == SetType.ERROR else ''}{Back.RESET}")
            for s in self.sets_planned
        ]
        modifiers = ' '.join(
            [k + ':' + ','.join(v) for k, v in self.modifiers.items() if v])

        e1rm = f'{Fore.MAGENTA} e1rm: {self.e1rm}{Fore.RESET}' if self.e1rm else ''
        vol_planned = (f'{Fore.GREEN} vol_p: '
                       f'{self.vol_planned}%{Fore.RESET}') if self.vol_planned else ''
        vol_done = (f'{Fore.GREEN} vol_d: {self.vol_done}kg{Fore.RESET}'
                    if self.vol_done else '')
        vol_done_relative = (
            f' {Fore.RED} vol_d%: {round(100*self.vol_done/self.e1rm, 1)}%{Fore.RESET}'
            if self.vol_done and self.e1rm else '')
        inol = f'{Fore.CYAN} inol: {self.inol}{Fore.RESET}' if self.inol else ''
        si = (f'{Fore.YELLOW} CS: {round(self.stress_index_done["cs"], 1)} '
              f'PS: {round(self.stress_index_done["ps"], 1)} '
              f'TS: {round(self.stress_index_done["ts"], 1)}{Fore.RESET}'
              if self.stress_index_done['ts'] != 0.0 else '')
        ret = (
            f'{Fore.RED}{self.name} {modifiers}{Fore.RESET} | p:{inol}{vol_planned} '
            f'd:{e1rm}{vol_done}{vol_done_relative}{si}\n'
            f'\t\t{" ".join(sets_planned)} {Back.LIGHTBLUE_EX}=>{Back.RESET} '
            f'{" ".join(sets_done)} '
        )
        if self._next_parallel_exercise:
            return ret + str(self._next_parallel_exercise)
        return ret + '\n'


class Session:

    def __init__(self, exercises: List[Exercise], date: str, name: str):
        self.exercises = exercises
        self.date = date
        self.name = name

    def __str__(self):
        ret = f"{Back.BLUE}Session {self.name} from {self.date}{Back.RESET}\n"
        for exercise in self.exercises:
            ret += str(exercise)
        return ret + "\n"


class Microcycle:

    def __init__(self, sessions: List[Session], name):
        self.sessions = sessions
        self.name = name

    def __str__(self):
        e = self._get_exercise_analysis()
        exercise_analysis_str = '\n\t'.join(f'{k:<20}' + str(v) for k, v in e.items())
        ret = (f"{Back.GREEN}Microcycle: {self.name}\n"
               f"Summary:\n\t{exercise_analysis_str}{Back.RESET}\n")
        for session in self.sessions:
            ret += str(session)
        return ret + "\n"

    def _get_exercise_analysis(self):
        ret = {}
        for s in self.sessions:
            for e in s.exercises:
                if e.name not in ret.keys():
                    if not e.inol and not e.stress_index_done['cs']:
                        continue
                    ret[e.name] = {'inol': 0.0, 'cs': 0.0, 'ps': 0.0, 'ts': 0.0}
                ret[e.name]['inol'] += e.inol
                ret[e.name]['cs'] += e.stress_index_done['cs']
                ret[e.name]['ps'] += e.stress_index_done['ps']
                ret[e.name]['ts'] += e.stress_index_done['ts']
        for e in ret:
            for k in ret[e]:
                ret[e][k] = round(ret[e][k], 1)

        return ret


class Mesocycle:

    def __init__(self, microcycles: List[Microcycle], name):
        self.microcycles = microcycles
        self.name = name

    def __str__(self):
        ret = (f"{Fore.BLACK}{Back.YELLOW}Mesocycle: {self.name}"
               f"{Back.RESET}{Fore.RESET}\n")
        for microcycle in self.microcycles:
            ret += str(microcycle)
        return ret + "\n"


def get_exercise(planned_cell, done_cell):
    return Exercise(planned_cell.value, done_cell.value, "")


def get_session(planned_cells, done_cells):
    exercises = []
    for p, d in zip(planned_cells[1:], done_cells[1:]):
        if p.value == "":
            continue
        exercises.append(get_exercise(p, d))
    date = done_cells[0].value
    return Session(exercises, date, planned_cells[0].value)


def get_microcycles(weeks_split: List[gspread.Cell]) -> List[Microcycle]:
    micros = []
    pattern = re.compile("^[DdSs][0-9]+")  # Ignore GPP column for now
    for session_cells in weeks_split:
        sessions = []
        sessions_row = (cell for cell in session_cells
                        if cell.row == session_cells[0].row)
        logger.debug(sessions_row)
        for session_cell in sessions_row:
            if re.match(pattern, session_cell.value):
                planned_cells = [
                    cell for cell in session_cells
                    if cell.col == session_cell.col and cell.row >= session_cell.row
                ]
                done_cells = [
                    cell for cell in session_cells
                    if cell.col == session_cell.col + 1 and cell.row >= session_cell.row
                ]
                session = get_session(planned_cells, done_cells)
                sessions.append(session)
        micros.append(Microcycle(sessions, session_cells[0].value))
    return micros


def get_mesocycle(mesocycle_start: gspread.Cell, mesocycle_last_row: int) -> Mesocycle:
    microcycle_pattern = re.compile("^[WwMm][0-9]+")
    micro_a1 = (gspread.utils.rowcol_to_a1(mesocycle_start.row, mesocycle_start.col) +
                ":" + gspread.utils.rowcol_to_a1(mesocycle_last_row, G_WIDTH))
    meso_cell_range: List[gspread.Cell] = wksh.range(micro_a1)
    microcycle_row = 0
    microcycles_split = []
    for i, cell in enumerate(meso_cell_range):
        if re.match(microcycle_pattern, cell.value):
            if microcycle_row:    # If we find a row with W[0-9]
                microcycles_split.append(
                    meso_cell_range[microcycle_row:i - 1]
                )    # Save microcycles from former week row to row before current
            microcycle_row = i
        if i == len(meso_cell_range
                    ) - 1 and microcycle_row:    # If we reach the end of sheet
            microcycles_split.append(meso_cell_range[microcycle_row:i - 1])
    micros = get_microcycles(microcycles_split)
    return Mesocycle(micros, mesocycle_start.value)


if __name__ == "__main__":
    args = parser.parse_args()
    gc = gspread.oauth(credentials_filename="secret.json", )

    sh = gc.open(args.spreadsheet)
    print(sh.worksheets())
    wksh = sh.worksheet(args.worksheet)
    G_WIDTH = len(wksh.get_all_values()[0]) + 1
    G_HEIGHT = len(wksh.get_all_values()) + 1

    blocks = wksh.findall(re.compile("^[Bb][0-9]+$"), in_column=0)
    mesocycles = []
    for i, block in enumerate(blocks):
        # next_block_row = blocks[i + 1].row - 1 if i + 1 < len(blocks) else
        # G_HEIGHT - 1 TODO send mesocycle height to the get_ function change
        # to get_mesocycle that parses only one, move height management to upper
        # level
        last_row = blocks[i + 1].row - 1 if i + 1 < len(blocks) else G_HEIGHT - 1
        mesocycles.append(get_mesocycle(block, last_row))
    with open('output', 'w') as f:
        for m in mesocycles:
            s = str(m)
            print(s)
            f.write(s)
