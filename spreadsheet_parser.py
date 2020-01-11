from collections import namedtuple
from enum import Enum
from utils import SheetCell, calculate_e1RM
from openpyxl import load_workbook
import copy
import datetime
import json
import logging
import re

MATCH_PLANNED_TO_DONE = False

RPE_SCHEME = '(?P<rpe>(?:[1-9](?:,|\.)[5])|(?:[1-9]|10)|(?:9\.\(3\)|9\.3|9\.\(6\)|9\.6))'
RPE_MULTISET_SCHEME = f'(?P<multi_rpe>(?:@{RPE_SCHEME}){{2,}})'
WEIGHT_SCHEME = '(?:(?P<weight>[0-9]+(?:\.[0-9]{1,3})?)' \
                '(?i)(?P<unit>kg|lbs)?|(?P<bw>BW))'
PERCENTAGE_SCHEME = '(?P<percentage>[1-9][0-9]?|100)'
REPS_SCHEME = '(?P<reps>[0-9]+)'
SETS_SCHEME = '(?P<sets>[0-9]+)'

class WeightUnit(Enum):
    KG = 1
    LBS = 2
    BW = 3

logging.basicConfig(filename='pla.log',
    format='%(levelname)s:%(name)s:%(lineno)s  %(message)s',
    level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TrainingSpreadsheetParser:
    """ Loads training spreadsheet from file and parses it into structure of
    training related objects, in a form easy for further processing
    """

    def __init__(self, file_dir, unit):
        self.unit = unit
        self.wb = load_workbook(filename = file_dir)
        self.ws = self.wb[self.wb.sheetnames[0]]
        self.mesocycles = []

    def get_mesocycles(self):
        return self.mesocycles

    def parse_worksheet(self):
        ws = self.ws
        current_cell = SheetCell(1,1)

        cval = ws.cell(row=current_cell.row, column=current_cell.col).value
        while cval != 'Sheet_end:':
            logger.debug(str(cval) + ' Mesocycle')
            if isinstance(cval, str) and re.match("^Mesocycle:", cval):
                m = self.parse_mesocycle(current_cell)
                self.mesocycles.append(m)

            current_cell.next_row()
            cval = ws.cell(row=current_cell.row, column=current_cell.col).value

    def parse_mesocycle(self, start_cell):
        ws = self.ws
        current_cell = copy.copy(start_cell)
        notes = ws.cell(row=current_cell.row, column=current_cell.col).comment
        date_range = self.ws.cell(row=current_cell.row,
                        column=current_cell.col+1).value
        name = re.sub('^Mesocycle:', '', self.ws.cell(
                      row=current_cell.row, column=current_cell.col).value
                     )
        logger.info(f'Parsing mesocycle: {name}')

        microcycles = []

        cval = ws.cell(row=current_cell.row, column=current_cell.col).value
        while cval != 'Mesocycle_end:':
            if isinstance(cval, str) and re.match("^W(?:\d+)", cval):
                logger.debug(cval + ' :Microcycle')
                micro = self.parse_microcycle(current_cell)
                logger.debug(f'{current_cell.col}-{current_cell.row};' \
                             f'week-{date_range}')
                microcycles.append(micro)

            current_cell.next_row()
            cval = ws.cell(row=current_cell.row, column=current_cell.col).value

        m = Mesocycle(microcycles, name, date_range, notes)
        return m

    def parse_microcycle(self, start_cell):
        ws = self.ws
        current_cell = copy.copy(start_cell)
        w_n = ws.cell(row=current_cell.row, column=current_cell.col).value
        notes = ws.cell(row=current_cell.row, column=current_cell.col).comment
        date = ws.cell(row=current_cell.row+1, column=current_cell.col).value
        workouts = []

        current_cell.next_col()
        cval = ws.cell(row=current_cell.row, column=current_cell.col).value
        while cval:
            if isinstance(cval, str) and re.match("^D(?:\d+)", cval):
                logger.debug(cval)
                workout = self.parse_workout(current_cell)
                workouts.append(workout)

            current_cell.next_col(); current_cell.next_col()
            cval = ws.cell(row=current_cell.row, column=current_cell.col).value

        m = Microcycle(date, workouts, '', notes)
        return m

    def parse_workout(self, current_cell):
        ws = self.ws
        current_cell = copy.copy(current_cell)
        exercises = []

        day = ws.cell(row=current_cell.row, column=current_cell.col).value
        date_place = ws.cell(row=current_cell.row,
                        column=current_cell.col+1).value
        notes = ws.cell(row=current_cell.row,
                    column=current_cell.col).comment

        current_cell.next_row()
        cval = ws.cell(row=current_cell.row, column=current_cell.col).value
        while cval != None:
            logger.debug(cval)
            planned_str = ws.cell(row=current_cell.row,
                              column=current_cell.col).value
            done_str = ws.cell(row=current_cell.row,
                           column=current_cell.col+1).value
            notes = ws.cell(row=current_cell.row,
                        column=current_cell.col).comment
            e = Exercise(planned_str, done_str, notes)
            exercises.append(e)

            current_cell.next_row()
            cval = ws.cell(row=current_cell.row, column=current_cell.col).value

        w = Workout(day, date_place, exercises, notes)
        return w


class Exercise:
    class SetType(Enum):
        NONE = -1
        RPE = 0
        WEIGHT = 1
        PERCENT1RM = 2
        LOAD_DROP = 3
        FATIGUE_PERCENT = 4
        RPE_RAMP = 5

    DefaultUnit = WeightUnit.KG
    Weight = namedtuple('Weight', ('value', 'unit',))
    Set =  namedtuple('Set', ('type', 'reps', 'weight', 'rpe'))
    schemes_planned = (
            (re.compile(f'^x{REPS_SCHEME}@{RPE_SCHEME}$'), SetType.RPE), # REPS at RPE
            (re.compile(f'^{SETS_SCHEME}x{REPS_SCHEME}@{PERCENTAGE_SCHEME}%$'),
                SetType.PERCENT1RM),# SETS of REPS at PERCENTAGE
            (re.compile(f'^{PERCENTAGE_SCHEME}%@{RPE_SCHEME}$'), # PERCENTAGE at RPE
                SetType.PERCENT1RM),
            (re.compile(f'^x{REPS_SCHEME}(?:@{RPE_SCHEME}){{2,}}$'), # REPS at RPE multiple #needs furhter processing
                SetType.RPE),
            (re.compile(f'^{SETS_SCHEME}x{REPS_SCHEME}^@{RPE_SCHEME}$'),# SETS of REPS starting at RPE
                SetType.RPE),
            (re.compile(f'^{SETS_SCHEME}x@{RPE_SCHEME}$'), # number of SETS at RPE
                SetType.RPE),
            (re.compile(f'^{PERCENTAGE_SCHEME}%x{REPS_SCHEME}$'), # REPS at %1RM
                SetType.PERCENT1RM),
            (re.compile(f'^{SETS_SCHEME}x{REPS_SCHEME}V{PERCENTAGE_SCHEME}%$'), # SETS of REPS at PERCENTAGE
                SetType.LOAD_DROP),
            (re.compile(f'^{SETS_SCHEME}x{WEIGHT_SCHEME}@{RPE_SCHEME}$'), # SETS x WEIGHT at RPE
                SetType.WEIGHT),
            (re.compile(f'^{SETS_SCHEME}x{REPS_SCHEME}$'),# SETS of REPS starting at RPE
                SetType.WEIGHT),
            )
    schemes_done = (
            (re.compile(f'^{WEIGHT_SCHEME}x{REPS_SCHEME}@{RPE_SCHEME}$'),#weightXreps at RPE
                SetType.WEIGHT),
            (re.compile(f'^{WEIGHT_SCHEME}@{RPE_SCHEME}$'), #'weight at RPE (presumed same set number as planned)',
                SetType.WEIGHT),
            (re.compile(f'^{WEIGHT_SCHEME}{RPE_MULTISET_SCHEME}$'), #Multiple Weight@Rpe sets written in one string
                SetType.WEIGHT),
            (re.compile(f'^{WEIGHT_SCHEME}x{REPS_SCHEME}' \
                       f'{RPE_MULTISET_SCHEME}$'), #Multiple WeightXReps@Rpe sets written in one string
                SetType.WEIGHT),
            (re.compile(f'^{SETS_SCHEME}x{REPS_SCHEME}' \
                       f'(?:\/|x|@){WEIGHT_SCHEME}$'),
                SetType.WEIGHT),
            (re.compile('^ *X *$'), # exercise not done
                SetType.NONE),
            (re.compile('^ *V *$'),
                SetType.NONE),
            (re.compile(f'^(?:{REPS_SCHEME}(?:,|@))+{WEIGHT_SCHEME}$'), #Multiple sets at given weight
                SetType.WEIGHT),
            (re.compile(f'^{REPS_SCHEME}x{WEIGHT_SCHEME}$'), #Reps at weight
                SetType.WEIGHT),
            )


    def __init__(self, planned_str, done_str, notes):
        logger.debug(self.SetType.RPE)
        logger.debug(self.SetType)

        self.done = True
        self.is_superset = False
        self.workout_from_string(planned_str, done_str)
        self.notes = notes
        self.workset_volume = 0
        self.categories = {}

        if self.done:
            self.e1RM = self.get_e1RM()
        else:
            self.e1RM = None

    def get_e1RM(self):
        logging.debug([ws for ws in self.sets_done])
        logging.debug(self.is_superset)
        if self.is_superset:
            x = [max([calculate_e1RM(ws['weight'], ws['reps'], ws['RPE'])
                for ws in e]) for e in self.sets_done]
            return x
        x = max([calculate_e1RM(ws['weight'], ws['reps'], ws['RPE'])
                for ws in self.sets_done])
        return x

    def workout_from_string(self, first_col_str, second_col_str):
    # First column contains exercise with modifiers and planned sets,
    # second column contains done sets
        logging.debug('first_col_str: ' + first_col_str)
        exercise_str, planned_str = first_col_str.split(':')
        if '&' in exercise_str:
            self.is_superset = True
            exercise_strs = exercise_str.split('&')
            planned_strs = planned_str.split('&')
            second_col_strs = second_col_str.split('&')
            second_col_strs = [s.strip() for s in second_col_strs]

            self.name, self.modifiers, self.sets_planned, self.sets_done = [],[],[],[]
            for e_str, p_str, s_c_str in zip(exercise_strs,
                                             planned_strs, second_col_strs):
                name, modifiers = self.exercise_from_string(e_str)
                self.name.append(e_str)
                self.modifiers.append(modifiers)
                self.sets_planned.append(self.sets_planned_from_string(p_str))
                self.sets_done.append(self.sets_done_from_string(s_c_str))
            return

        self.name, self.modifiers = self.exercise_from_string(exercise_str)
        self.sets_planned = self.sets_planned_from_string(planned_str)
        self.sets_done = self.sets_done_from_string(second_col_str)

    def exercise_from_string(self, exercise_str):
        modifier_schemes = (re.compile(' w/(?P<with>[a-zA-Z0-9]+)'), #'with x',
                            re.compile(' t/(?P<tempo>\d{4})'), #'tempo XXXX',
                            re.compile(' wo/(?P<without>[a-zA-Z0-9]+)'), #'without x',
                            re.compile(' p/(?P<pattern>[a-zA-z0-9]+)')) #'movement patter mod'

        name = exercise_str
        modifiers = [pattern.findall(name) for pattern in modifier_schemes]
        logging.debug(f'Modifiers: {modifiers}')

        for m in modifiers:
            for k in m:
                name = re.sub(f' \w+/{k}(?: |$)', ' ', name)

        return (name.rstrip(), modifiers)

    def sets_done_from_string(self, sets_str):
        prior_weight = 0
        prior_reps = 0
        prior_rpe = 0

        schemes = self.schemes_done

        sets_str = re.split(' |;', sets_str)
        sets_done = []
        set_no = 1
        for set_str in sets_str:
            while True:
                try:
                    match = [(pattern[0].match(set_str), index+1)
                                for index, pattern
                                in enumerate(schemes)
                                if pattern[0].match(set_str)][0]
                except IndexError as e:
                    breakpoint()
                    logging.exception(e)
                    print('Failed to match set with any of schemes')
                    print('Please enter correct string')
                    set_str = input()
                    print(set_str, end='')
                    continue
                break

            logging.debug(f'Done: {sets_str}, {set_str} - no{set_no},' \
                f'match={match}, groups={match[0].groups()}')
            if match[1] == 1:
                # 150x5@9.5 Weight x reps @ RPE
                sets_done.append(self.set_into_dict(
                    weight=float(match[0].group('weight').replace(',', '.')),
                    reps=int(match[0].group('reps').replace(',', '.')),
                    rpe=float(match[0].group('rpe').replace(',', '.')),
                    set_no=set_no))
            elif match[1] == 2:
                # 150lbs@9 Weight @ RPE
                sets_done.append(self.set_into_dict(
                    weight=float(match[0].group('weight').replace(',', '.')),
                    rpe=float(match[0].group('rpe').replace(',', '.')),
                    set_no=set_no))
            elif match[1] == 3:
                # 150@7@8@9 Weight @ multiple rpe
                multiset_weight = float(match[0].group('weight').replace(',','.'))
                multiset_rpe_list = match[0].group('multi_rpe').split('@')[1:]
                for rpe in multiset_rpe_list:
                    sets_done.append(self.set_into_dict(
                        weight=multiset_weight,
                        rpe = rpe.replace(',','.'),
                        set_no=set_no))
            elif match[1] == 4:
                # 150kgx5@7@8@9 Weight x reps @ multiple rpe
                multiset_weight = float(match[0].group('weight').replace(',','.'))
                multiset_reps = match[0].group('reps').replace(',', '.')
                multiset_rpe_list = match[0].group('multi_rpe').split('@')[1:]
                for rpe in multiset_rpe_list:
                    sets_done.append(self.set_into_dict(
                        weight=multiset_weight,
                        reps=int(multiset_reps),
                        rpe=float(rpe.replace(',','.')),
                        set_no=set_no))
            elif match[1] == 5:
                # 3x10x25kg Sets x reps x|/|@ weight
                sets = int(match[0].group('sets'))
                multiset_reps = int(match[0].group('reps'))
                multiset_weight = float(match[0].group('weight'))
                for _ in range(0, sets):
                    sets_done.append(self.set_into_dict(
                        weight=multiset_weight,
                        reps=multiset_reps,
                        set_no=set_no))
            elif match[1] == 6:
                # X Exercise not done
                self.done = False
            elif match[1] == 7:
                # V  Exercise done as planned
                self.done = True
            elif match[1] == 8:
                # 5,4,4,3,3@120kg Multiple sets @ given weight
                for _ in sets:
                    pass
            elif match[1] == 9:
                # 5x100kg Reps x weight
                sets_done.append(self.set_into_dict(
                    weight=float(match[0].group('weight')),
                    reps=int(match[0].group('reps')),
                    set_no=set_no))

        return sets_done

    def sets_planned_from_string(self, sets_planned_str):
        schemes = self.schemes_planned

        sets_planned_str = sets_planned_str.strip()
        if sets_planned_str == '':
            return []
        logging.debug('sets planned str:' + sets_planned_str +'/')
        sets_str = re.split(' |;', sets_planned_str)
        logging.debug(sets_str)
        sets_planned = []
        set_no = 1
        for set_str in sets_str:
            while True:
                try:
                    match = [(pattern[0].match(set_str), index+1)
                                for index, pattern
                                in enumerate(schemes)
                                if pattern[0].match(set_str)][0]
                except IndexError as e:
                    logging.exception(e)
                    print('Failed to match set with any of schemes')
                    print('Please enter correct string')
                    print('wrong set str ' + set_str, end='')
                    set_str = input()
                    continue
                break

            logger.info(f'Planned: {sets_str}, {set_str} - no{set_no},' \
                        f'match={match}, groups={match[0].groups()}')

            if match[1] == 1:
            # x5@9 Reps @ RPE
                sets_planned.append(self.set_into_dict(
                    reps=int(match[0].group('reps').replace(',', '.')),
                    rpe=float(match[0].group('rpe').replace(',', '.')),
                    set_no=set_no
                ))
            elif match[1] == 2:
            # 3x5@90% Sets x reps @ percentage
                multiset_sets = int(match[0].group('sets').replace(',', '.'))
                multiset_reps = int(match[0].group('reps').replace(',', '.'))
                multiset_weight = match[0].group('percentage').replace(',','.')
                for _ in range(0,multiset_sets):
                    sets_planned.append(self.set_into_dict(
                        weight=multiset_weight,
                        reps=multiset_reps,
                        set_no=set_no
                    ))
            elif match[1] == 3:
            # 80%@9 Percentage @ RPE
                sets_planned.append(self.set_into_dict(
                    weight=float(match[0].group('weight').replace(',','.')),
                    rpe=float(match[0].group('rpe').replace(',', '.')),
                    set_no=set_no
                ))
            elif match[1] == 4:
            # x5@7@8@9 x reps @ multiple rpe
                multiset_reps = int(match[0].group('reps').replace(',', '.'))
                multiset_rpe_list = match[0].group('multi_rpe').split('@')[1:]
                for rpe in multiset_rpe_list:
                    sets_planned.append(self.set_into_dict(
                        reps=multiset_reps,
                        rpe=float(rpe.replace(',','.')),
                        set_no=set_no
                    ))
            elif match[1] == 5:
            # 3x5@8 sets x reps @ RPE
                multiset_reps = int(match[0].group('reps').replace(',', '.'))
                multiset_rpe = float(match[0].group('rpe').replace(',', '.'))
                for _ in range(0,int(match[0].group('sets').replace(',','.'))):
                    sets_planned.append(self.set_into_dict(
                        reps=multiset_reps,
                        rpe=multiset_rpe,
                        set_no=set_no
                    ))
            elif match[1] == 6:
            # 5x@9 Sets x @ RPE
                multiset_sets = int(match[0].group('sets').replace(',', '.'))
                multiset_rpe = float(match[0].group('rpe').replace(',', '.'))
                for _ in range(0,multiset_sets):
                    sets_planned.append(self.set_into_dict(
                        rpe=multiset_rpe,
                        set_no=set_no
                    ))
            elif match[1] == 7:
            # 80%x5 percentage x reps
                sets_planned.append(self.set_into_dict(
                    weight=float(match[0].group('weight').replace(',','.')),
                    reps=int(match[0].group('reps').replace(',', '.')),
                    set_no = set_no
                ))
            elif match[1] == 8:
            # 3x5@90% Sets x reps @ percentage
                pass
            elif match[1] == 9:
            # 5xBW@9 sets x weight @ RPE
                multiset_sets = int(match[0].group('sets').replace(',', '.'))
                multiset_weight = float(match[0]
                                      .group('weight').replace(',','.'))
                multiset_rpe = float(match[0].group('rpe').replace(',','.'))
                for _ in range(0,multiset_sets):
                    sets_planned.append(self.set_into_dict(
                        weight=multiset_weight,
                        rpe=multiset_rpe,
                        set_no=set_no))
            elif match[1] == 10:
            # 5x3 sets x reps
                multiset_sets = int(match[0].group('sets').replace(',', '.'))
                multiset_reps = int(match[0].group('reps').replace(',', '.'))
                for _ in range(0,multiset_sets):
                    sets_planned.append(self.set_into_dict(reps=multiset_reps,
                                                           set_no = set_no))


        return sets_planned

    def match_to_set_planned(self, match, set_no):
        groupdict = match[0].groupdict()
        if 'sets' in groupdict:
            if 'reps' in groupdict:
                groupdict['reps'] = int(groupdict['reps'].replace(',', '.'))
            if 'weight' in groupdict:
                groupdict['weight'] = float(
                                          groupdict['weight'].replace(',','.'))
            sets = []
            for _ in range(0, groupdict['sets']):
                sets.append(set_into_dict(set_no=set_no, **groupdict))
            return sets

        if 'multi_rpe' in groupdict:
            multiset_weight = float(match[0].group('weight').replace(',','.'))
            multiset_reps = match[0].group('reps').replace(',', '.')
            multiset_rpe_list = match[0].group('multi_rpe').split('@')[1:]
            for rpe in multiset_rpe_list:
                c_set = {'reps': '', 'weight':'', 'RPE': '', 'set_no': ''}
                c_set['weight'] = multiset_weight
                c_set['reps'] = int(multiset_reps)
                c_set['RPE'] = float(rpe.replace(',','.'))
                c_set['set_no'] = set_no

            return

        if 'rpe' in groupdict:
            rpe=float(match[0].group('rpe').replace(',', '.')),

        if 'reps' in groupdict:
            reps=int(match[0].group(1).replace(',', '.')),

        if 'weight' in groupdict:
            weight=float(match[0].group('weight').replace(',', '.')),


    def set_into_dict(self, reps=None, rpe=None, weight=None, unit=None, set_no=0):
        Weight, Set = self.Weight, self.Set #namedtuple('Weight', ('value', 'unit',))
        #namedtuple('Set', ('type', 'reps', 'weight', 'rpe'))
        cnt_set = Set(self.SetType.RPE, reps, Weight(weight, unit), rpe)
        return cnt_set

    def match_sets_planned_done(self):
        pass


    def analyze_exercise(self):
        ''' Retrieves information form datasets.json and perfrorms analyze'''
        #json.
        pass

    def volume(self):
        vol = 0.0
        if not self.is_superset:
            for s in self.sets_done:
                if s['reps'] and s['weight']:
                    vol += s['reps']*s['weight']
            return vol

    def str(self):
        if self.is_superset:
            sets_planned = [f"{s['weight'] or ''}x{s['reps'] or ''}" \
                f"@{s['RPE'] or ''}" if s!='&' else f' {s} '
                for e in self.sets_planned for s in e + ['&']]
            if self.done:
                sets_done = [f"{s['weight'] or ''}x{s['reps'] or ''}" \
                    f"@{s['RPE'] or ''}" if s!='&' else f' {s} '
                    for e in self.sets_done for s in e + ['&']]
            else:
                sets_done = "X"
            ret = (f"{'&'.join(self.name)}: {';'.join(sets_planned)}"\
                    f"| {';'.join(sets_done)} e1RM:" \
                    f"{';'.join(['{:4.2f}'.format(f) for f in self.e1RM])}",
                    0)
            return ret
        if self.done:
            sets_done = [f"{s['weight'] or ''}x{s['reps'] or ''}" \
                f"@{s['RPE'] or ''}" for s in self.sets_done]
        else:
            sets_done = "X"
        sets_planned = [f"{s['weight'] or ''}x{s['reps'] or ''}" \
                        f"@{s['RPE'] or ''}" for s in self.sets_planned]
        e1RM = self.e1RM if self.e1RM else 0.0
        return (f'{self.name}: {";".join(sets_planned)} ' \
                f'| {";".join(sets_done)}',
                e1RM)

class Workout:
    def __init__(self, day, date_place_str, exercises, notes):
        self.day = day
        self.date, self.place = self.parse_date_place(date_place_str)
        self.exercises = exercises
        self.notes = notes

    def calculate_volume(self):
        vol = 0.0
        for e in self.exercises:
            vol += e.volume()
        return vol

    def parse_date_place(self, date_place_str):
        if '@' in date_place_str:
            date, place = date_place_str.split('@')
        else:
            date, place = date_place_str, ''
        return (date, place)

    def str(self):
        return [e.str() for e in self.exercises]

class Microcycle:
    def __init__(self, date, workouts, drugs, notes):
        self.length = len(workouts) # TODO
        self.date_start, self.date_end = self.parse_date(date)
        self.workouts = workouts
        self.drugs = drugs
        self.notes = notes

    def parse_date(self,date_str):
        #TODO
        date_start = date_str
        date_end = date_str
        return date_start, date_end

    def calculate_volume(self):
        pass

    def str(self):
        return f'\tDate: {self.date_start}-{self.date_end}, notes: {self.notes}'


class Mesocycle:
    def __init__(self, microcycles, name, date_range, notes):
        self.name = name
        self.microcycles = microcycles
        self.date_start = date_range
        self.date_end = date_range
        self.notes = notes

    def str(self):
        return f'Name: {self.name}, Date:{self.date_start}-{self.date_end}, ' \
               f'Length: {len(self.microcycles)}, Notes: {self.notes}'

class ExerciseCategory:
    def __init__(self):
        DATASETS = 'datasets.json'
        with open(DATASETS, 'r') as ds:
            self.data = json.load(ds)


class Bodyweight:
    pass

if __name__ == '__main__':
    #wb = load_workbook(filename = XSL_FILE)
    #ws = wb['program']

    tsp = TrainingSpreadsheetParser(XSL_FILE, 'kg')
    tsp.parse_worksheet()

