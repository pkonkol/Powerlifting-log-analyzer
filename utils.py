import json
import math

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
    if reps > 12:
        return 0
    return round(100 * weight / DATA['rpe_percentage_chart'][str(rpe)][int(reps - 1)],
                 3)


def get_percentage(reps: float, rpe: float):
    if not(reps and rpe >= 6.0):
        return 0
    if reps > 12:
        return 0
    return DATA['rpe_percentage_chart'][str(rpe)][int(reps - 1)]


def get_rpe(reps: float, percentage: float) -> float:
    """
    Finds first RPE for given rep range that's lower than percentage param
    """
    for i in DATA['rpe_percentage_chart']:
        if i[reps - 1] < percentage:
            return i[reps - 1]
    return 0.0


def calculate_inol(reps, intensity):
    return reps / (100.01 - intensity)


def get_stress_index(rpe: float, reps: int) -> tuple[float, float, float]:
    if rpe < 5.0:
        return 0, 0, 0
    return(DATA['cs'][str(rpe)][min(int(reps - 1), 14)],
           DATA['ps'][str(rpe)][min(int(reps - 1), 14)],
           DATA['ts'][str(rpe)][min(int(reps - 1), 14)])


def get_old_stress_index(rpe: float) -> float:
    # rpe_to_si = {
    # }
    match rpe:
        case 5:
            return 0.1
        case 5.5 | 6:
            return 0.5
        case 6.5 | 7:
            return 0.667
        case 7.5 | 8:
            return 0.8
        case 8.5 | 9:
            return 1
        case 9.3 | 9.5 | 9.6 | 10:
            return 1.333
        case _:
            return 0.0


def get_exercise_aliases():
    return DATA["exercise_aliases"]


def rpe_to_rir(rpe: float) -> float:
    x = {
        10: 0, 9.6: 0.3, 9.5: 0.5, 9.3: 0.6, 9: 1, 8.5: 1.5,
        8: 2, 7.5: 3, 7: 4, 6.5: 5, 6: 7, 5.5: 9, 5: 12
    }
    return x.get(rpe, 0)


def get_exertion_load_for_rep(rep: int) -> float:
    return math.pow(math.e, -0.215 * rep)


def get_exertion_load_for_reps_rpe(reps: int, rpe: float) -> float:
    # TODO allow range to start from a 0.5 rpe, then go by ints
    rir = math.ceil(rpe_to_rir(rpe))
    return sum((math.pow(math.e, -0.215 * x)
                for x in range(rir, rir + reps, 1)))


def get_central_exertion_load(reps: int, rpe: float, weight: float) -> float:
    return get_exertion_load_for_reps_rpe(reps, rpe) * weight / reps


def get_peripheral_exertion_load(reps: int, rpe: float, weight: float) -> float:
    return get_exertion_load_for_reps_rpe(reps, rpe) * weight


# def calculate_plate_order(available_plates: Counter, bar_weight: float,
#                          goal_weight: float) -> tuple:
#    # TODO
#    return plate_order
#
#
# def print_plate_order(plate_order: tuple) -> None:
#    # TODO
#    return
