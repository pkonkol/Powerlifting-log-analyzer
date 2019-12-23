#import pandas as pd
from utils import SheetCell, calculate_e1RM
from openpyxl import load_workbook
import copy
import datetime
import json
import logging
import re

XSL_FILE = 'data/program.xlsx'

RPE_SCHEME = '((?:[1-9],[5])|(?:[1-9]|10))'
WEIGHT_SCHEME = '([0-9]+)(kg|lbs)?'
PERCENTAGE_SCHEME = '([1-9][0-9]?|100)'
REPS_SCHEME = '([0-9]+)'
SETS_SCHEME = '([0-9]+)'

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
            #print(str(cval) + ' Mesocycle')
            if isinstance(cval, str) and re.match("^Mesocycle:", cval):
                m = self.parse_mesocycle(current_cell)
                self.mesocycles.append(m)

            current_cell.next_row()
            cval = ws.cell(row=current_cell.row, column=current_cell.col).value

    def parse_mesocycle(self, start_cell):
        ws = self.ws
        current_cell = copy.copy(start_cell)
        notes = ws.cell(row=current_cell.row, column=current_cell.col).comment
        date_range = self.ws.cell(row=current_cell.row, column=current_cell.col+1).value
        name = re.sub('^Mesocycle:', '', self.ws.cell(
                      row=current_cell.row, column=current_cell.col).value
                     )
        print(name)

        microcycles = []

        cval = ws.cell(row=current_cell.row, column=current_cell.col).value
        while cval != 'Mesocycle_end:':
            if isinstance(cval, str) and re.match("^W(?:\d+)", cval):
                print(cval + ' :Microcycle')
                micro = self.parse_microcycle(current_cell)
                print(micro)
                print(type(micro))
            #print("|{},-{},; week-{},nweek-{}".format(cur_col, cur_row, week, nweek))
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

        current_cell.next_row()
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
        print([ws for ws in self.sets_done])
        print(self.is_superset)
        if self.is_superset:
            return 0
        x = max([calculate_e1RM(ws['weight'], ws['reps'], ws['RPE']) for ws in self.sets_done])
        return x

    def workout_from_string(self, first_col_str, second_col_str): # First column contains exercise with modifiers and planned sets, second column contains done sets
        print('first_col_str: ' + first_col_str)
        exercise_str, planned_str = first_col_str.split(':')
        if '&' in exercise_str:
            self.is_superset = True
            exercise_strs = exercise_str.split('&')
            planned_strs = planned_str.split('&')
            second_col_strs = second_col_str.split('&')
            second_col_strs = [s.strip() for s in second_col_strs]

            self.name, self.modifiers, self.sets_planned, self.sets_done = [],[],[],[]
            for e_str, p_str, s_c_str in zip(exercise_strs, planned_strs, second_col_strs):
                name, modifiers = self.exercise_from_string(e_str)
                self.name.append(e_str)
                self.modifiers.append(modifiers)
                self.sets_planned.append(self.sets_planned_from_string(p_str))
                self.sets_done.append(self.sets_done_from_string(s_c_str))
                breakpoint()
            return

        self.name, self.modifiers = self.exercise_from_string(exercise_str)
        self.sets_planned = self.sets_planned_from_string(planned_str)
        self.sets_done = self.sets_done_from_string(second_col_str)

    def exercise_from_string(self, exercise_str):
        modifier_schemes = {' w/([a-zA-Z0-9]+)': 'with x',
                            ' t/(\d{4})': 'tempo XXXX',
                            ' wo/([a-zA-Z0-9]+)': 'without x',
                            ' p/([a-zA-z0-9]+)': 'movement patter mod'}

        name = exercise_str
        modifiers = [(re.findall(key, name), value) for key, value in modifier_schemes.items()]
        print(modifiers)

        for key in modifiers:
            for k in key[0]:
                name = re.sub(k, '', name)

        return (name, modifiers)

    def sets_done_from_string(self, sets_str):
        set_scheme = {'reps': '', 'weight':'', 'RPE': '', 'set_no': ''}
        prior_weight = 0
        prior_reps = 0
        prior_rpe = 0


        schemes = {'^([0-9]+)x([0-9]+)@(([1-9],[5])|([1-9]|10))$': 1, #'weight x reps at RPE'
                   '^([0-9]+)@(([1-9],[5])|([1-9]|10))$': 2, #'weight at RPE (presumed same set number as planned)',
                   '^{weight}((?:@{rpe}){{2,}})$'.format(weight=WEIGHT_SCHEME, rpe= RPE_SCHEME): 3, #Multiple Weight@Rpe sets written in one string
                   '^{weight}x{reps}((?:@{rpe}){{2,}})$'.format(weight=WEIGHT_SCHEME,reps=REPS_SCHEME, rpe= RPE_SCHEME): 4, #Multiple WeightXReps@Rpe sets written in one string
                   '^{sets}x{reps}/{weight}$'.format(weight=WEIGHT_SCHEME, reps=REPS_SCHEME, sets=SETS_SCHEME): 5,
                   '^X$': 6 # exercise not done
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

            print('Done: {}, {} - no{}, match={}, groups={}'.format(sets_str, set_str, set_no, match, match[0].groups()))
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
                multiset_weight = float(match[0].group(1).replace(',','.'))
                multiset_rpe_list = match[0].group(0).split('@')[1:]
                for rpe in multiset_rpe_list:
                    c_set = {'reps': '', 'weight':'', 'RPE': '', 'set_no': ''}
                    c_set['weight'] = multiset_weight
                    c_set['RPE'] = float(rpe.replace(',','.'))
                    c_set['set_no'] = set_no
                    set_no += 1
                    sets_done.append(c_set)
            elif match[1] == 4:
                multiset_weight = float(match[0].group(1).replace(',','.'))
                multiset_reps = match[0].group(3).replace(',', '.')
                multiset_rpe_list = match[0].group(4).split('@')[1:]
                for rpe in multiset_rpe_list:
                    c_set = {'reps': '', 'weight':'', 'RPE': '', 'set_no': ''}
                    c_set['weight'] = multiset_weight
                    c_set['reps'] = int(multiset_reps)
                    c_set['RPE'] = float(rpe.replace(',','.'))
                    c_set['set_no'] = set_no
                    set_no += 1
                    sets_done.append(c_set)
            elif match[1] == 5:
                sets = int(match[0].group(1))
                multiset_reps = int(match[0].group(2))
                multiset_weight = float(match[0].group(3))
                for _ in range(0, sets):
                    c_set = {'reps': '', 'weight':'', 'RPE': '', 'set_no': ''}
                    c_set['weight'] = multiset_weight
                    c_set['reps'] = multiset_reps
                    c_set['set_no'] = set_no
                    set_no += 1
                    sets_done.append(c_set)
            elif match[1] == 6:
                self.done = False

        return sets_done

    def sets_planned_from_string(self, sets_planned_str):
        set_scheme = {'reps': '', 'weight':'', 'RPE': '', 'set_no': ''}
        sets_num = 0
        schemes = {'^x{reps}@{rpe}$'.format(reps=REPS_SCHEME, rpe=RPE_SCHEME): 1, #'reps at RPE',
                   '^{sets}x{reps}@{percentage}%$'.format(sets=SETS_SCHEME, reps=REPS_SCHEME, percentage=PERCENTAGE_SCHEME): 2, # 'sets of reps at percentage',
                   '^{percentage}%@{rpe}$'.format(percentage=PERCENTAGE_SCHEME, rpe=RPE_SCHEME): 3, # 'percentage at RPE',
                   '^x{reps}(?:@{rpe}){{2,}}$'.format(reps=REPS_SCHEME, rpe=RPE_SCHEME): 4, #'reps at RPE multiple', #needs furhter processing
                   '^{sets}x{reps}@{rpe}$'.format(sets=SETS_SCHEME, reps=REPS_SCHEME, rpe=RPE_SCHEME):5,# 'sets of reps starting at RPE',
                   '^{sets}x@{rpe}$'.format(sets=SETS_SCHEME, rpe=RPE_SCHEME): 6, #'number of sets at RPE',
                   '^{percentage}%x{reps}$'.format(percentage=PERCENTAGE_SCHEME, reps=REPS_SCHEME): 7, #'reps at %1RM',
                   '^{sets}x{reps}@{percentage}%$'.format(sets=SETS_SCHEME, reps=REPS_SCHEME, percentage=PERCENTAGE_SCHEME): 8, #'sets of reps at percentage',
                   '^{sets}x{weight}@{rpe}$'.format(sets=SETS_SCHEME, weight=WEIGHT_SCHEME, rpe=RPE_SCHEME) : 9, #'Sets x weight at RPE',
                   '^{sets}x{reps}$'.format(sets=SETS_SCHEME, reps=REPS_SCHEME):10,# 'sets of reps starting at RPE',
                   }

        sets_planned_str = sets_planned_str.strip()
        if sets_planned_str == '':
            return []
        print('sets planned str:' + sets_planned_str +'/')
        sets_str = re.split(' |;', sets_planned_str)
        print(sets_str)
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
                    print('wrong set str ' + set_str, end='')
                    set_str = input()
                    continue
                break

            print('Planned: {}, {} - no{}, match={}, groups={}'.format(sets_str, set_str, set_no, match, match[0].groups()))
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
                    sets_planned.append(c_set)
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
                    sets_planned.append(c_set)
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
                    sets_planned.append(c_set)
            elif match[1] == 6:
                multiset_sets = int(match[0].group(1).replace(',', '.'))
                multiset_rpe = float(match[0].group(2).replace(',', '.'))
                for _ in range(0,multiset_sets):
                    c_set = {'reps': '', 'weight':'', 'RPE': '', 'set_no': ''}
                    c_set['set_no'] = set_no
                    c_set['RPE'] = multiset_rpe
                    set_no += 1
                    sets_planned.append(c_set)
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
                    sets_planned.append(c_set)
            elif match[1] == 10:
                multiset_sets = int(match[0].group(1).replace(',', '.'))
                multiset_reps = int(match[0].group(2).replace(',', '.'))
                for _ in range(0,multiset_sets):
                    c_set = {'reps': '', 'weight':'', 'RPE': '', 'set_no': ''}
                    c_set['reps'] = multiset_reps
                    c_set['set_no'] = set_no
                    set_no += 1
                    sets_planned.append(c_set)


        return sets_planned

    def analyze_exercise(self):
        ''' Retrieves information form datasets.json and perfrorms analyze'''
        #json.
        pass

    def volume(self):
        vol = 0.0
        if not self.is_superset:
            for s in self.sets_done:
                vol += s['reps']*s['weight']
            return vol

    def str(self):
        if self.is_superset:
            print('if_superset')
            print(self.name)
            return ("&".join(self.name), 0)
        if self.done:
            sets_done = ["{}x{}@{}".format(s['weight'], s['reps'], s['RPE']) for s in self.sets_done]
        else:
            sets_done = "X"
        sets_planned = ["{}x{}@{}".format(s['weight'], s['reps'], s['RPE']) for s in self.sets_planned]
        e1RM = self.e1RM if self.e1RM else 0.0
        return ("{}: {} | {}  ".format(self.name,
                                       ";".join(sets_planned),
                                       ";".join(sets_done)),
                                e1RM)

class Workout:
    def __init__(self, day, date_place, exercises, notes):
        self.day = day
        self.date = date_place
        self.place = date_place
        self.exercises = exercises
        self.notes = notes

    def calculate_volume(self):
        vol = 0.0
        for e in self.exercises:
            vol += e.volume()
        return vol

    def parse_date_place(self, date_place_str):
        date, place = date_place_str.split('@')

    def str(self):
        return [e.str() for e in self.exercises]

class Microcycle:
    def __init__(self, date, workouts, drugs, notes):
        self.length = len(workouts) #TODO
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
        return "\tDate: {}-{}, notes: {}".format(self.date_start,
                                        self.date_end, self.notes)


class Mesocycle:
    def __init__(self, microcycles, name, date_range, notes):
        self.name = name
        self.microcycles = microcycles
        self.date_start = date_range
        self.date_end = date_range
        self.notes = notes

    def str(self):
        return "Name: {}, Date:{}-{}, Length: {}, Notes: {}".format(
                self.name, self.date_start, self.date_end,
                len(self.microcycles), self.notes)

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

