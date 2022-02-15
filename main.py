import gspread
import re
from pprint import pprint
from typing import List


class Exercise:
    def __init__(self, planned: str, done: str, notes):
        self.planned = planned
        self.done = done
        self.notes = notes

    def __repr__(self):
        return f"{self.planned}:{self.done}\n"


class Session:
    def __init__(self, exercises: List[Exercise], date: str):
        self.exercises = exercises
        self.date = date

    def __repr__(self):
        ret = f"Session from {self.date}"
        for e in self.exercises:
            ret += str(e)
        return ret + "\n"


class Microcycle:
    def __init__(self, sessions: List[Session]):
        self.sessions = sessions

    def __repr__(self):
        ret = f"Microcycle: "
        for s in self.sessions:
            ret += str(s)
        return ret + "\n"


class Mesocycle:
    def __init__(self, micros: List[Microcycle]):
        self.micros = micros

    def __repr__(self):
        ret = f"Mesocycle: "
        for m in self.micros:
            ret += str(m)
        return ret + "\n"


def get_exercise(planned_cell, done_cell):
    return Exercise(planned_cell.value, done_cell.value, "")


def get_sessions(planned_cells, done_cells):
    sessions = []
    exercises = []
    for p, d in zip(planned_cells[1:], done_cells[1:]):
        exercises.append(get_exercise(p, d))
    date = done_cells[0].value
    return Session(exercises, date)


def get_microcycles(weeks_split):
    micros = []
    pattern = re.compile("^[Dd][0-9]+|GPP")
    for i, m in enumerate(weeks_split):
        sessions = []
        for c in weeks_split:
            sessions_row = [e for e in c if e.row == c[0].row]
            print(sessions_row)
            for x in sessions_row:
                if re.match(pattern, x.value):
                    planned_cells = [i for i in c if i.col == x.col and i.row >= x.row]
                    done_cells = [i for i in c if i.col == x.col + 1 and i.row >= x.row]
                    print(planned_cells)
                    print(done_cells)
                    session = get_sessions(planned_cells, done_cells)
                    sessions.append(session)
        micros.append(Microcycle(sessions))
    return micros


def get_mesocycles(blocks):
    mesocycles = []
    pattern = re.compile("^[Ww][0-9]+")
    for i, b in enumerate(blocks):
        next_block_row = blocks[i + 1].row - 1 if i + 1 < len(blocks) else G_HEIGHT - 1
        micro_a1 = (
            gspread.utils.rowcol_to_a1(b.row, b.col)
            + ":"
            + gspread.utils.rowcol_to_a1(next_block_row, G_WIDTH)
        )
        meso_range = wksh.range(micro_a1)
        print(meso_range)
        # That code sucks, but works. Done for the need of api usage optimization
        W_row = 0
        weeks_split = []
        while i < len(meso_range):
            c = meso_range[i]
            if re.match(pattern, c.value):
                if W_row:
                    micro_rows = range(W_row, i - 1)
                    weeks_split.append(meso_range[W_row : i - 1])
                W_row = i
            if i == len(meso_range) - 1:
                weeks_split.append(meso_range[W_row : i - 1])
            i += 1
        micros = get_microcycles(weeks_split)
        mesocycles.append(Mesocycle(micros))
    return mesocycles


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
    mesocycles = get_mesocycles(blocks)
    print(mesocycles[0])
