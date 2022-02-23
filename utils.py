import json
import math

from collections import Counter


DATASETS = 'datasets.json'
with open(DATASETS, 'r') as ds:
    DATA = json.load(ds)

def roundWithBias(x):
    # round to 0.5kgs as it's usually what people have
    # TODO round to an arbitrary number
    return (round(x * 2))/2

def kg_to_lbs(kg):
    return roundWithBias(kg*2.204)

def lbs_to_kg(lbs):
    return roundWithBias(lbs/2.204)

def calculate_wilks(weight_lifted, bodyweight, sex):
    pass

def calculate_ipf(weight_lifted, bodyweight, sex):
    pass

def calculate_aas(weight_lifted, bodyweight, sex):
    pass

def calculate_e1RM(weight, reps, rpe_str):
    if rpe_str == None:
        rpe = 10.0
    else:
        rpe = rpe_str
    if weight and reps and rpe >= 6.0:
        return round(100*weight/DATA['rpe_percentage_chart']
                                    [str(rpe)][int(reps-1)], 3)
    else:
        return 0

def calculate_plate_order(available_plates: Counter,
                          bar_weight: float, goal_weight: float) -> tuple:
    #TODO
    return plate_order

def print_plate_order(plate_order: tuple) -> None:
    #TODO
    return
