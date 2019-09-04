import math

def roundWithBias(x):
    y = round(math.ceil(x)-x,1)
    if y > 0.5:
        return round(x,1)-(1-y)
    else:
        return round(x,1)+y

def kg_to_lbs(kg):
    return roundWithBias(kg*2.204)

def lbs_to_kg(kg):
    return roundWithBias(kg/2.204)
