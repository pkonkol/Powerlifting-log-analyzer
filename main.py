import gspread
import re
import numpy as np
from pprint import pprint
from typing import List

class Exercise:
    def __init__(self, planned: str, done: str, notes):
        self.planned = planned
        self.done = done
        self.notes = notes

class Session: 
    def __init__(self, exercises: List[Exercise], date: str):
        self.exercises = exercises
        self.date = date

class Micro:
    def __init__(self, sessions: List[Session]):
        self.sessions = sessions

class Meso:
    def __init__(self, cell: gspread.Cell, micros: List[Micro]):
        self.cell = cell
        self.micros = micros
    
    def __repr__(self):
        return self.cell.value + str(self.micros)

def parse_exercise(planned_cell, done_cell):
    notes = wksh.get_note(planned_cell.address) + '\n' + wksh.get_note(done_cell.address)
    return Exercise(planned_cell.value, done_cell.value, notes)

def parse_sessions(planned_cells, done_cells):
    sessions = []
    exercises = []
    for p, d in zip(planned_cells[1:], done_cells[1:]):
        exercises.append(parse_exercise(p, d))
    date = done_cells[0].value

    # for s in session_cells:
    #     exercises = []
    #     for i in range(1,height):
    #         planned_cell = wksh.cell(s.row + i, s.col)
    #         done_cell = wksh.cell(s.row + i, s.col + 1)
    #         if planned_cell.value == "" or done_cell.value == "":
    #             continue
    #         exercises.append(parse_exercise(planned_cell, done_cell))
    #     date = wksh.cell(s.row, s.col + 1)
    #     sessions.append(Session(exercises, date.value))

    return Session(exercises, date)

def parse_microcycles(weeks_split):
    sessions = []
    pattern = re.compile("^[Dd][0-9]+|GPP")
    for i, m in enumerate(weeks_split):
        # session_cells = wksh.findall(pattern, in_row=m.row)
        # print(session_cells)
        # height = abs(m.row - (micro_cells[i+1].row if i+i < len(micro_cells) else G_HEIGHT))
        for c in weeks_split:
            sessions_row = [e for e in c if e.row == c[0].row ]
            print(sessions_row)
            for x in sessions_row:
                if re.match(pattern, x.value):
                    planned_cells = [i for i in c if i.col == x.col and i.row >= x.row]
                    done_cells = [i for i in c if i.col == x.col + 1 and i.row >= x.row]
                    print(planned_cells)
                    print(done_cells)
                    session = parse_sessions(planned_cells, done_cells)
                    sessions.append(session)

    return Micro(sessions)

def parse_mesocycles(blocks):
    mesocycles = []
    pattern = re.compile("^[Ww][0-9]+")
    # micro_cells = wksh.findall(pattern, in_column=0)
    for i, b in enumerate(blocks):
        next_block_row = blocks[i+1].row - 1 if i+1 < len(blocks) else G_HEIGHT - 1
        # micro_cells = [m for m in micro_cells if m.row > b.row and m.row < next_block_row]

        micro_a1 = gspread.utils.rowcol_to_a1(b.row, b.col) + ':' + gspread.utils.rowcol_to_a1(next_block_row, G_WIDTH)
        meso_range = wksh.range( micro_a1 )
        print(meso_range)
        # micro_cells_2 = [c for c in meso_range if c.]
        # That code sucks, but works. Done for the need of api usage optimization
        W_row = 0
        weeks_split = []
        while i < len(meso_range):
            c = meso_range[i]
            if (re.match(pattern, c.value)):
                if (W_row):
                    micro_rows = range(W_row, i - 1)
                    weeks_split.append(meso_range[W_row : i - 1])
                W_row = i           
            if i == len(meso_range) - 1:
                weeks_split.append(meso_range[W_row : i - 1])
            i += 1

        print(weeks_split)
        for w in weeks_split:
            print('WEEKS SPLIT -------------------------')
            print(w)

        micros = parse_microcycles(weeks_split)
        mesocycles.append(Meso(micros))
    return mesocycles

if __name__=="__main__":
    gc = gspread.oauth(
        credentials_filename='secret.json',    
    )
    # sh = gc.open("backup 13.02 Trening 2021-2022")
    sh = gc.open("Trening 2021-2022")

    print(sh.worksheets())
    wksh = sh.worksheet("IDL 2022.02 prep 09.2021-02.2022")
    G_WIDTH = len(wksh.get_all_values()[0]) +1
    G_HEIGHT = len(wksh.get_all_values()) +1

    # print(wksh.get_all_values())
    # print(wksh.get_all_records())
    # array = np.array(wksh.get_all_values())
    # pprint(array)
    # exit()

    # Identifty blocks
    blocks = wksh.findall(re.compile("^[Bb][0-9]+$"), in_column=0)
    print(blocks)
    mesocycles = parse_mesocycles(blocks)