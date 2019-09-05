import math

def roundWithBias(x):
    y = round(math.ceil(x)-x,1)
    if y > 0.5:
        return round(x,1)-(1-y)
    else:
        return round(x,1)+y

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
    return roundWithBias(kg*2.204)

def lbs_to_kg(kg):
    return roundWithBias(kg/2.204)

def calculate_wilks(weight_lifted, bodyweight, sex):
    pass

def calculate_ipf(weight_lifted, bodyweight, sex):
    pass

def calculate_aas(weight_lifted, bodyweight, sex):
    pass
