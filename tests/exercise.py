import os,sys,inspect
from tkinter.messagebox import NO
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

import unittest
import logging
from main import Exercise, WeightUnit
from schemes import SetType

Set = Exercise.Set
Weight = Exercise.Weight
ST = SetType
DU = Exercise.DefaultUnit
WU = WeightUnit

logger = logging.getLogger(__name__)
logger.info("Starting tests/exercise.py")

class SetsDoneParsing(unittest.TestCase):
    correct_results = (
        ('200@9',   [Set(ST.WEIGHT, None, Weight(200, DU), 9)]),
        ('200kg@9.3', [Set(ST.WEIGHT, None, Weight(200, WU.KG), 9.3)]),
        ('200lbs@9.6', [Set(ST.WEIGHT, None, Weight(200, WU.LBS), 9.6)]),
        ('200x5@9', [Set(ST.WEIGHT, 5, Weight(200, DU), 9)]),
        ('160x5@7@8.5', [Set(ST.WEIGHT, 5, Weight(160, DU), 7),
                        Set(ST.WEIGHT, 5, Weight(160, DU), 8.5)]),
        ('180@7@9', [Set(ST.WEIGHT, None, Weight(180, DU), 7),
                     Set(ST.WEIGHT, None, Weight(180, DU), 9)]),
        ('2x10/20kg', [Set(ST.WEIGHT, 10, Weight(20, WU.KG), None),
                       Set(ST.WEIGHT, 10, Weight(20, WU.KG), None)]),
        ('2x12@15kg', [Set(ST.WEIGHT, 12, Weight(15, WU.KG), None),
                       Set(ST.WEIGHT, 12, Weight(15, WU.KG), None)]),
        ('2x8x30kg', [Set(ST.WEIGHT, 8, Weight(30, WU.KG), None),
                      Set(ST.WEIGHT, 8, Weight(30, WU.KG), None)]),
        ('10x100kg', [Set(ST.WEIGHT, 10, Weight(100, WU.KG), None)]),
        ('X',   []),
        ('V',   []),
        #TODO
        # 'vvvv vvvv'
        #('vvvv vvvv', [Set(ST.DONE, None, None, None) for i in range(8)])
        # 'vvv'
        # 'vv vv vv vv vv'
        # '40kgXvvvv' maybe change the X to eg. 40kg=vvvv
        ('5,3@BW', [Set(ST.WEIGHT, 5, Weight(None, WU.BW), None),
                    Set(ST.WEIGHT, 3, Weight(None, WU.BW), None)]),
        ('5,4@150kg', [Set(ST.WEIGHT, 5, Weight(150, WU.KG), None),
                       Set(ST.WEIGHT, 4, Weight(150, WU.KG), None)]),
    )

    def test_sets_done_from_string(self):
        def f(self):
            pass

        logger.info("Starting tests_sets_done_from_string" + "-"*30)
        e = Exercise
        e.__init__ = f
        e = e()
        for sets_str, output_dict in self.correct_results:
            with self.subTest(msg=f'sets_done for {sets_str}'):
                result = e._sets_done_from_string(sets_str)
                logger.info(f'test_sets_done_from_string:{sets_str} -> {result}')
                self.assertEqual(result, output_dict,
                    msg=f'Failed done for {sets_str} with {result}; correct: {output_dict}')

class SetsPlannedParsing(unittest.TestCase):
    #Set =  self.Set #namedtuple('Set', ('type', 'reps', 'weight', 'rpe'))
    correct_results = (
        ('x8@9.3', [Set(ST.RPE, 8, Weight(None, None), 9.3)]),
        ('2x5V80%', [Set(ST.LOAD_DROP, 5, Weight(0.8, -1), None),
                     Set(ST.LOAD_DROP, 5, Weight(0.8, -2), None),
                    ]), # deprecated i think
        
        ('2x3@80%', [Set(ST.LOAD_DROP, 3, Weight(0.8, WU.PERCENT_1RM), None),
                     Set(ST.LOAD_DROP, 3, Weight(0.8, WU.PERCENT_1RM), None)]),
                     # this shoud represent load drop from last set now
                     # so 1rm% sets need new scheme
        ('3x1@100%', [Set(ST.LOAD_DROP, 1, Weight(1.0, WU.PERCENT_1RM), None),
                      Set(ST.LOAD_DROP, 1, Weight(1.0, WU.PERCENT_1RM), None),
                      Set(ST.LOAD_DROP, 1, Weight(1.0, WU.PERCENT_1RM), None)]),
                      # Maybe refactor LOAD_DROP to DROP later as rep drop also counts
        ('2x3@80%RM', [Set(ST.PERCENT_1RM, 3, Weight(0.8, WU.PERCENT_1RM), None),
                       Set(ST.PERCENT_1RM, 3, Weight(0.8, WU.PERCENT_1RM), None)]),
        ('2x8', [Set(ST.DONE, 8, Weight(None, None), None),
                 Set(ST.DONE, 8, Weight(None, None), None)]),
        ('80%x5', [Set(ST.PERCENT_1RM, 5, Weight(0.8, WU.PERCENT_1RM), None) ]),
        ('x5@7.5@9', [Set(ST.RPE, 5, Weight(None,None), 7.5),
                      Set(ST.RPE, 5, Weight(None,None), 9.0)]),
        ('2x5^@7', [Set(ST.RPE, 5, Weight(None,None), 7.0),
                    Set(ST.LOAD_DROP, 5, Weight(1.0, -1), None)]),
        ('x6$@9', [Set(ST.RPE_RAMP, 6, Weight(None, None), 9.0)]),
        ('x4@9-7%', [Set(ST.FATIGUE_PERCENT, 4, Weight(0.07, None), 9.0)]),
        ('160lbs@9', [Set(ST.RPE, None, Weight(160.0, WU.LBS), 9.0)]),
        ('160kg@9.6', [Set(ST.RPE, None , Weight(160.0, WU.KG), 9.6)]),
        ('160@7', [Set(ST.RPE, None , Weight(160.0, WU.KG), 7)]),
        ('150/5', [Set(ST.WEIGHT, 5, Weight(150.0, DU), None)]),
        ('150lbs/5', [Set(ST.WEIGHT, 5, Weight(150.0, WU.LBS), None)]),
        ('5x', [Set(ST.DONE, None, Weight(None, None), None) for _ in range(5)]),  # '5x'
        # '150kgx5' Is this even going to be implemented?
    )

    def test_sets_planned_from_string(self):
        def f(self):
            pass

        logger.info("Starting tests_sets_planned_from_string" + "-"*30)
        e = Exercise
        e.__init__ = f
        e = e()
        for sets_str, output_dict in self.correct_results:
            with self.subTest(msg=f'sets_planned for {sets_str}'):
                result = e._sets_planned_from_string(sets_str)
                logger.info(f'test_sets_planned_from_string: {sets_str} -> {result}')
                self.assertEqual(result, output_dict, 
                    msg=f'Failed planned for {sets_str} with {result}, correct {output_dict}')


class ExerciseInit(unittest.TestCase):
    # TODO check if complete class instance initializes correctly
    # Also may split it in tests for specific class init elements
    cases = (
        (
            {'planned': 'SQ: x5@9', 'done': '220x5@8.5 '}, 
            {'name': 'SQ', 'start': None, 'end': None,
             'sets_planned': [Set(ST.RPE, 5, Weight(None, None), 9)] , 
             'sets_done': [Set(ST.RPE, 5, Weight(220.0, WU.KG), 8.5)],
            },
            # TODO: case for the error from B1M1S1 Comp BP, 
            # case with matching planned to done
            # case with start & end time
        ),
    )

    def test_match_sets_planned_with_done(self):
        pass

    def test_exercise_init_with_correct_values(self):
        logger.info("Starting exercise_init_with_correct_values" + "-"*30)
        for strs, correct_dict in self.cases:
            with self.subTest(msg=f'exercise_init for {strs["planned"]}:{strs["done"]}'):
                e = Exercise(strs['planned'], strs['done'], "")
                self.assertEqual(e.name, correct_dict['name'])
                self.assertEqual(e.sets_planned, correct_dict['sets_planned'])
                self.assertEqual(e.sets_done, correct_dict['sets_done'])

if __name__ == '__main__':
    unittest.main(verbosity=2)

#set struct
# ({'reps': <int> , 'type': <str>, 'weight': <float>, 'RPE': <float>}, ...)
# Set =  namedtuple('Set', ('type', 'reps, 'weight', 'rpe'))

