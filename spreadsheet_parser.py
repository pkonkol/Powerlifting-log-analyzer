#import pandas as pd
from utils import SheetCell
from openpyxl import load_workbook
import re
import copy

XSL_FILE = 'data/program.xlsx'
UNITS = 'KG'

RPE_SCHEME = '((?:[1-9],[5])|(?:[1-9]|10))'
WEIGHT_SCHEME = '([0-9]+)(kg|lbs)?'
PERCENTAGE_SCHEME = '([1-9][0-9]?|100)'
REPS_SCHEME = '([0-9]+)'
SETS_SCHEME = '([0-9]+)'

class TrainingSpreadsheetParser:

    def __init__(self, file_dir):
        self.mesocycles = []
        self.wb = load_workbook(filename = file_dir)
        self.ws = self.wb[self.wb.sheetnames[0]]

    def parse_worksheet(self):
        ws = self.ws
        current_cell = SheetCell(1,1)

        cval = ws.cell(row=current_cell.row, column=current_cell.col).value
        while cval != 'Sheet_end:':
            #print(str(cval) + ' Mesocycle')
            if isinstance(cval, str) and re.match("^Mesocycle:", cval):
                m = self.parse_mesocycle(current_cell)
                self.mesocycles.append(m)

            current_cell.next_row()
            cval = ws.cell(row=current_cell.row, column=current_cell.col).value

    def parse_mesocycle(self, start_cell):
        ws = self.ws
        current_cell = copy.copy(start_cell)
        date_range = self.ws.cell(row=current_cell.row, column=current_cell.col+1).value
        name = re.sub('^Mesocycle:', '', self.ws.cell(
                      row=current_cell.row, column=current_cell.col).value
                     )
        notes = ws.cell(row=current_cell.row, column=current_cell.col).comment
        print(name)

        microcycles = []

        cval = ws.cell(row=current_cell.row, column=current_cell.col).value
        while cval != 'Mesocycle_end:':
            if isinstance(cval, str) and re.match("^W(?:\d+)", cval):
                print(cval + ' :Microcycle')
                micro = self.parse_microcycle(current_cell)
            #print("|{},-{},; week-{},nweek-{}".format(cur_col, cur_row, week, nweek))
                microcycles.append(micro)

            current_cell.next_row()
            cval = ws.cell(row=current_cell.row, column=current_cell.col).value

        m = Mesocycle(microcycles, name, date_range, notes)
        return m

    def parse_microcycle(self, start_cell):
        ws = self.ws
        current_cell = copy.copy(start_cell)
        notes = ws.cell(row=current_cell.row, column=current_cell.col).comment
        date = ws.cell(row=current_cell.row+1, column=current_cell.col)
        workouts = []

        current_cell.next_col()
        cval = ws.cell(row=current_cell.row, column=current_cell.col).value
        while cval:
            if isinstance(cval, str) and re.match("^D(?:\d+)", cval):
                print(cval)
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
        date_place = ws.cell(row=current_cell.row, column=current_cell.col+1).value
        notes = ws.cell(row=current_cell.row, column=current_cell.col).comment

        cval = ws.cell(row=current_cell.row, column=current_cell.col).value
        while cval != None:
            print(cval)
            planned_str = ws.cell(row=current_cell.row, column=current_cell.col).value
            done_str = ws.cell(row=current_cell.row, column=current_cell.col+1).value
            notes = ws.cell(row=current_cell.row, column=current_cell.col).comment
            e = Exercise(planned_str, done_str, notes)
            exercises.append(e)

            current_cell.next_row()
            cval = ws.cell(row=current_cell.row, column=current_cell.col).value


        w = Workout(day, date_place, exercises, notes)

        return w


class Exercise:
    def __init__(self, planned_str, done_str, notes):
        self.name = ''
        self.modifiers = []
        self.sets_planned = []
        self.sets_done = []
        self.notes = notes
        self.workset_volume = 0
        self.is_superset = False
        self.done = True

    def workout_from_string(self, first_col_str, second_col_str): # First column contains exercise with modifiers and planned sets, second column contains done sets
        exercise_str, planned_str = first_col.split(':')
        self.name, self.modifiers = exercise_from_string(exercise_str)
        self.sets_planned = sets_planned_from_string(planned_str)
        self.sets_done = sets_done_from_string(second_col_str)

    def exercise_from_string(self, exercise_str):
        modifier_schemes = {' w/([a-zA-Z0-9]+)': 'with x',
                            ' t/(\d{4})': 'tempo XXXX',
                            ' wo/([a-zA-Z0-9]+)': 'without x',
                            ' p/([a-zA-z0-9]+)': 'movement patter mod'}

        modifiers = [(re.findall(key, name), value) for key, value in modifiers.items()]

        name = exercise_str
        for key in modifiers.keys():
            name = re.sub(key, '', name)

        return (name, modifiers)

    def sets_done_from_string(self, sets_str):
        set_scheme = {'reps': '', 'weight':'', 'RPE': '', 'set_no': ''}
        prior_weight = 0
        prior_reps = 0
        prior_rpe = 0


        schemes = {'^([0-9]+)x([0-9]+)@(([1-9],[5])|([1-9]|10))$': 1, #'weight x reps at RPE'
                   '^([0-9]+)@(([1-9],[5])|([1-9]|10))$': 2, #'weight at RPE (presumed same set number as planned)',
                   '^{weight}(?:@{rpe}){{2,}}$'.format(weight=WEIGHT_SCHEME, rpe= RPE_SCHEME): 3, #Multiple Weight@Rpe sets written in one string
                   '^{weight}x{reps}(?:@{rpe}){{2,}}$'.format(weight=WEIGHT_SCHEME,reps=REPS_SCHEME, rpe= RPE_SCHEME): 4, #Multiple WeightXReps@Rpe sets written in one string
                   '^X$': 5 # exercise not done
                   }

        sets_str = re.split(' |;', sets_str)
        sets_done = []
        set_no = 1
        for set_str in sets_str:
            c_set = {'reps': '', 'weight':'', 'RPE': '', 'set_no': ''}
            while True:
                try:
                    match = [(re.match(key, set_str), value) for key, value in zip(schemes.keys(), schemes.values()) if re.match(key, set_str)][0]
                except IndexError:
                    print('Failed to match set with any of schemes')
                    print('Please enter correct string')
                    print(set_str, end='')
                    set_str = input()
                    continue
                break

            print('{}, {} - no{}, match={}, groups={}'.format(sets_str, set_str, set_no, match, match[0].groups()))
            if match[1] == 1:
                c_set['weight'] = float(match[0].group(1).replace(',', '.'))
                c_set['reps'] = int(match[0].group(2).replace(',', '.'))
                c_set['RPE'] = float(match[0].group(3).replace(',', '.'))
                c_set['set_no'] = set_no
                set_no += 1
                sets_done.append(c_set)
            elif match[1] == 2:
                c_set['weight'] = float(match[0].group(1).replace(',', '.'))
                c_set['RPE'] = float(match[0].group(2).replace(',', '.'))
                c_set['set_no'] = set_no
                set_no += 1
                sets_done.append(c_set)
            elif match[1] == 3:
                print('match[1]==3')
                multiset_weight = float(match[0].group(1).replace(',','.'))
                multiset_rpe_list = match[0].group(0).split('@')[1:]
                print('multiset_rpe_list: ' + str(multiset_rpe_list))
                for rpe in multiset_rpe_list:
                    c_set = {'reps': '', 'weight':'', 'RPE': '', 'set_no': ''}
                    c_set['weight'] = multiset_weight
                    c_set['RPE'] = float(rpe.replace(',','.'))
                    c_set['set_no'] = set_no
                    set_no += 1
                    sets_done.append(c_set)
            elif match[1] == 4:
                print('match[1]==4')
                multiset_weight = float(match[0].group(1).replace(',','.'))
                multiset_reps = int(match[0].group(2).replace(',', '.'))
                multiset_rpe_list = match[0].group(0).split('@')[1:]
                for rpe in multiset_rpe_list:
                    c_set = {'reps': '', 'weight':'', 'RPE': '', 'set_no': ''}
                    c_set['weight'] = multiset_weight
                    c_set['reps'] = multiset_reps
                    c_set['RPE'] = float(rpe.replace(',','.'))
                    c_set['set_no'] = set_no
                    set_no += 1
                    sets_done.append(c_set)
            elif match[1] == 5:
                self.done = False

        return sets_done

    def sets_planned_from_string(self, sets_planned_str):
        set_scheme = {'reps': '', 'weight':'', 'RPE': '', 'set_no': ''}
        sets_num = 0
        schemes = {'^x{reps}@{rpe}$'.format(reps=REPS_SCHEME, rpe=RPE_SCHEME): 1, #'reps at RPE',
                   '^{sets}x{reps}@{percentage}%$'.format(sets=SETS_SCHEME, reps=REPS_SCHEME, rpe=RPE_SCHEME): 2, # 'sets of reps at percentage',
                   '^{percentage}%@{rpe}$': 3, # 'percentage at RPE',
                   '^x{reps}(?:@{rpe}){{2,}}$': 4, #'reps at RPE multiple', #needs furhter processing
                   '^{sets}x{reps}@{rpe}$':5,# 'sets of reps starting at RPE',
                   '^{sets}x@{rpe}$': 6, #'number of sets at RPE',
                   '^{percentage}%x{reps}$': 7, #'reps at %1RM',
                   '^{sets}x{reps}@{percentage}%$': 8, #'sets of reps at percentage',
                   '^{sets}x{weight}@{rpe}$': 9, #'Sets x weight at RPE',
                   }

        sets_str = re.split(' |;', sets_str)
        sets_planned = []
        set_no = 1
        for set_str in sets_str:
            c_set = {'reps': '', 'weight':'', 'RPE': '', 'set_no': ''}
            while True:
                try:
                    match = [(re.match(key, set_str), value) for key, value in zip(schemes.keys(), schemes.values()) if re.match(key, set_str)][0]
                except IndexError:
                    print('Failed to match set with any of schemes')
                    print('Please enter correct string')
                    print(set_str, end='')
                    set_str = input()
                    continue
                break

        print('{}, {} - no{}, match={}, groups={}'.format(sets_str, set_str, set_no, match, match[0].groups()))
        if match[1] == 1:
            c_set['reps'] = int(match[0].group(1).replace(',', '.'))
            c_set['RPE'] = float(match[0].group(2).replace(',', '.'))
            c_set['set_no'] = set_no
            set_no += 1
            sets_planned.append(c_set)
        elif match[1] == 2:
            multiset_sets = int(match[0].group(1).replace(',', '.'))
            multiset_reps = int(match[0].group(2).replace(',', '.'))
            multiset_weight = float(match[0].group(3).replace(',','.'))
            for _ in range(0,multiset_sets):
                c_set = {'reps': '', 'weight':'', 'RPE': '', 'set_no': ''}
                c_set['weight'] = multiset_weight
                c_set['reps'] = multiset_reps
                c_set['set_no'] = set_no
                set_no += 1
                sets_done.append(c_set)
        elif match[1] == 3:
            c_set['weight'] = float(match[0].group(1).replace(',','.'))
            c_set['RPE'] = float(match[0].group(2).replace(',', '.'))
            c_set['set_no'] = set_no
            set_no += 1
            sets_planned.append(c_set)
        elif match[1] == 4:
            multiset_reps = int(match[0].group(1).replace(',', '.'))
            multiset_rpe_list = match[0].group(0).split('@')[1:]
            for rpe in multiset_rpe_list:
                c_set = {'reps': '', 'weight':'', 'RPE': '', 'set_no': ''}
                c_set['reps'] = multiset_reps
                c_set['RPE'] = float(rpe.replace(',','.'))
                c_set['set_no'] = set_no
                set_no += 1
                sets_done.append(c_set)
        elif match[1] == 5:
            multiset_sets = int(match[0].group(1).replace(',', '.'))
            multiset_reps = int(match[0].group(2).replace(',', '.'))
            multiset_rpe = float(match[0].group(3).replace(',', '.'))
            for _ in range(0,multiset_sets):
                c_set = {'reps': '', 'weight':'', 'RPE': '', 'set_no': ''}
                c_set['reps'] = multiset_reps
                c_set['set_no'] = set_no
                c_set['RPE'] = multiset_rpe
                set_no += 1
                sets_done.append(c_set)
        elif match[1] == 6:
            multiset_sets = int(match[0].group(1).replace(',', '.'))
            multiset_rpe = float(match[0].group(2).replace(',', '.'))
            for _ in range(0,multiset_sets):
                c_set = {'reps': '', 'weight':'', 'RPE': '', 'set_no': ''}
                c_set['set_no'] = set_no
                c_set['RPE'] = multiset_rpe
                set_no += 1
                sets_done.append(c_set)
        elif match[1] == 7:
            c_set['weight'] = float(match[0].group(1).replace(',','.'))
            c_set['reps'] = int(match[0].group(2).replace(',', '.'))
            c_set['set_no'] = set_no
            set_no += 1
            sets_planned.append(c_set)
        elif match[1] == 8:
            pass
        elif match[1] == 9:
            multiset_sets = int(match[0].group(1).replace(',', '.'))
            multiset_weight = float(match[0].group(2).replace(',','.'))
            multiset_rpe = float(match[0].group(3).replace(',', '.'))
            for _ in range(0,multiset_sets):
                c_set = {'reps': '', 'weight':'', 'RPE': '', 'set_no': ''}
                c_set['weight'] = multiset_weight
                c_set['RPE'] = multiset_rpe
                c_set['set_no'] = set_no
                set_no += 1
                sets_done.append(c_set)

    def print(self):
        pass

class Workout:
    def __init__(self, day, date_place, exercises, notes):
        self.day = day
        self.date = date_place
        self.place = date_place
        self.exercises = exercises
        self.notes = notes

    def print(self):
        pass

class Microcycle:
    def __init__(self, date, workouts, drugs, notes):
        self.length = date #TODO
        self.date_start, self.date_end = self.parse_date(date)
        self.workouts = workouts
        self.drugs = drugs
        self.notes = notes

    def parse_date(self,date_str):
        #TODO
        date_start = date_str
        date_end = date_str
        return date_start, date_end

    def print(self):
        pass

class Mesocycle:
    def __init__(self,name, microcycles, date_range, notes):
        self.name = name
        self.microcycles = microcycles
        self.date_start = date_range
        self.date_end = date_range
        self.notes = notes

    def print(self):
        pass

class Bodyweight:
    pass

if __name__ == '__main__':
    #wb = load_workbook(filename = XSL_FILE)
    #ws = wb['program']

    tsp = TrainingSpreadsheetParser(XSL_FILE)
    tsp.parse_worksheet()

