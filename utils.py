class SheetCell:
    def __init__(self, row=-1, col=-1):
        self.row = row
        self.col = col

    def next_col(self):
        self.col = self.col+1
        return self.col

    def next_row(self):
        self.row = self.row+1
        return self.row

def kg_to_lbs(kg):
    pass

def lbs_to_kg(kg):
    pass

def calculate_wilks(weight_lifted, bodyweight, sex):
    pass

def calculate_ipf(weight_lifted, bodyweight, sex):
    pass

def calculate_aas(weight_lifted, bodyweight, sex):
    pass

