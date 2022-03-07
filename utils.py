import json

DATASETS = 'datasets.json'
with open(DATASETS, 'r') as ds:
    DATA = json.load(ds)


def round_with_bias(x):
    # round to 0.5kgs as it's usually what people have
    # TODO round to an arbitrary number
    return (round(x * 2)) / 2


def kg_to_lbs(kg):
    return round_with_bias(kg * 2.204)


def lbs_to_kg(lbs):
    return round_with_bias(lbs / 2.204)


def calculate_wilks(weight_lifted, bodyweight, sex):
    pass


def calculate_ipf(weight_lifted, bodyweight, sex):
    pass


def calculate_aas(weight_lifted, bodyweight, sex):
    pass


def calculate_e1rm(weight, reps, rpe_str):
    rpe = 10.0 if rpe_str is None else rpe_str
    if not(weight and reps and rpe >= 6.0):
        return 0
    return round(100 * weight / DATA['rpe_percentage_chart'][str(rpe)][int(reps - 1)],
                 3)


def get_percentage(reps: float, rpe: float):
    if not(reps and rpe >= 6.0):
        return 0
    return DATA['rpe_percentage_chart'][str(rpe)][int(reps - 1)]


def calculate_inol(reps, intensity):
    return reps / (100.01 - intensity)


# def calculate_plate_order(available_plates: Counter, bar_weight: float,
#                          goal_weight: float) -> tuple:
#    # TODO
#    return plate_order
#
#
# def print_plate_order(plate_order: tuple) -> None:
#    # TODO
#    return
