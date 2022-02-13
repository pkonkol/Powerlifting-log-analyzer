import gspread
import re
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

def parse_sessions(session_cells, height: int):
    sessions = []
    for s in session_cells:
        exercises = []
        for i in range(1,height):
            planned_cell = wksh.cell(s.row + i, s.col)
            done_cell = wksh.cell(s.row + i, s.col + 1)
            if planned_cell.value == "" or done_cell.value == "":
                continue
            exercises.append(parse_exercise(planned_cell, done_cell))
        date = wksh.cell(s.row, s.col + 1)
        sessions.append(Session(exercises, date.value))

    return sessions

def parse_microcycles(micro_cells):
    sessions = []
    for i, m in enumerate(micro_cells):
        pattern = re.compile("^[Dd][0-9]+|GPP")
        session_cells = wksh.findall(pattern, in_row=m.row)
        print(session_cells)
        height = abs(m.row - (micro_cells[i+1].row if i+i < len(micro_cells) else G_HEIGHT))
        session = parse_sessions(session_cells, height)
        sessions.append(session)

    return Micro(sessions)

def parse_mesocycles(blocks):
    mesocycles = []
    for i, b in enumerate(blocks):
        pattern = re.compile("^[Ww][0-9]+")
        micro_cells = wksh.findall(pattern, in_column=0)
        micro_cells = [w for w in micro_cells if w.row > b.row and w.row < (blocks[i+1].row if i+1 < len(blocks) else G_HEIGHT)]

        micros = parse_microcycles(micro_cells)
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

    # Identifty blocks
    blocks = wksh.findall(re.compile("^[Bb][0-9]+$"), in_column=0)
    print(blocks)
    mesocycles = parse_mesocycles(blocks)