import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

import unittest
import logging
import spreadsheet_parser as sp
Set = sp.Exercise.Set
Weight = sp.Exercise.Weight
ST = sp.Exercise.SetType
DU = sp.Exercise.DefaultUnit
WU = sp.WeightUnit

logger = logging.getLogger(__name__)

class SetsDoneParsing(unittest.TestCase):
    correct_results = (('2x8', [Set(ST.NONE, 8, Weight(None, None), None),
                                Set(ST.NONE, 8, Weight(None, None), None)]),
                      )

    def test_sets_done_from_string(self):
        e = sp.Exercise()
        for sets_str, output_dict in self.correct_results:
            result = e.sets_done_from_string(sets_str)
            print('test_sets_done_from_string: {}'.format(result))
            self.assertEqual(result, output_dict, msg='{}, {}'.format(result, output_dict))

class SetsPlannedParsing(unittest.TestCase):
    #Set =  self.Set #namedtuple('Set', ('type', 'reps', 'weight', 'rpe'))
    correct_results = (('x8@9.(3)', [Set(ST.RPE, 8, Weight(None, None), 9.3)]),
                        ('2x5V80%', [Set(ST.LOAD_DROP, 5, Weight(0.8, None), None),
                                     Set(ST.LOAD_DROP, 5, Weight(0.8, None), None),
                                    ]),
                        ('2x3@80%', [Set(ST.PERCENT1RM, 3, Weight(0.8, None), None),
                                     Set(ST.PERCENT1RM, 3, Weight(0.8, None), None)]),
                        ('2x8', [Set(ST.NONE, 8, Weight(None, None), None),
                                 Set(ST.NONE, 8, Weight(None, None), None)]),
                        ('5x80%', [Set(ST.PERCENT1RM, 5, Weight(0.8, None), None) ]),
                        ('x5@7.5@9', [Set(ST.RPE, 5, Weight(None,None), 7.5),
                                      Set(ST.RPE, 5, Weight(None,None), 9)]),
                        ('2x5^@7', [Set(ST.RPE, 5, Weight(None,None), 7),
                                    Set(ST.LOAD_DROP, 5, Weight(1.0, None), None)]),
                        ('x6$@9', [Set(ST.RPE_RAMP, 6, Weight(None, None), 9)]),
                        ('x4@9-7%', [Set(ST.FATIGUE_PERCENT, 4, Weight(0.93, None), 9.0)]),
                        ('2x@9', [Set(ST.RPE, None, Weight(None, WU.BW), 9)]),
                        ('160lbs@9', [Set(ST.RPE, None, Weight(160, WU.LBS), 9)]),
                        ('160kg@9.(6)', [Set(ST.RPE, None , Weight(160, WU.KG), 9.6)]),
                        ('150x5', [Set(ST.RPE, 5, Weight(150, DU.value), None)]),
            )

    def test_sets_planned_from_string(self):
        def f(self):
            pass

        e = sp.Exercise
        e.__init__ = f
        e = e()
        for sets_str, output_dict in self.correct_results:
            result = e.sets_planned_from_string(sets_str)
            logger.info(f'test_sets_planned_from_string: {result}')
            self.assertEqual(result, output_dict, msg=f'{result}, {output_dict}')

if __name__ == '__main__':
    unittest.main()

#set struct
# ({'reps': <int> , 'type': <str>, 'weight': <float>, 'RPE': <float>}, ...)
# Set =  namedtuple('Set', ('type', 'reps, 'weight', 'rpe'))

