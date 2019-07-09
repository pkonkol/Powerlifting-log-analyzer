import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

import unittest
import opl_spreadsheet_parser as opl

class SetsDoneParsing(unittest.TestCase):
    correct_results = ( ('150@7', [{'reps': '', 'weight':150.0, 'RPE': 7.0, 'set_no': 1}]),
                        ('150@8,5', [{'reps': '', 'weight':150.0, 'RPE': 8.5, 'set_no': 1}]),
                        ('150@7 170@9 180@10', [{'reps': '', 'weight':150.0, 'RPE': 7.0, 'set_no': 1},
                                                {'reps': '', 'weight':170.0, 'RPE': 9.0, 'set_no': 2},
                                                {'reps': '', 'weight':180.0, 'RPE': 10.0, 'set_no': 3}]),
                        ('150x5@7', [{'reps': 5, 'weight':150.0, 'RPE': 7.0, 'set_no': 1}]),
                        ('150@7 170@8,5 180x3@10', [{'reps': '', 'weight':150.0, 'RPE': 7, 'set_no': 1},
                                                  {'reps': '', 'weight':170.0, 'RPE': 8.5, 'set_no': 2},
                                                  {'reps': 3, 'weight':180.0, 'RPE': 10.0, 'set_no': 3}]),
                        ('150x5@7@7,5@8,5@9@9,5', [{'reps': 5, 'weight':150.0, 'RPE': 7.0, 'set_no': 1},
                                                   {'reps': 5, 'weight':150.0, 'RPE': 7.5, 'set_no': 2},
                                                   {'reps': 5, 'weight':150.0, 'RPE': 8.5, 'set_no': 3},
                                                   {'reps': 5, 'weight':150.0, 'RPE': 9.0, 'set_no': 4},
                                                   {'reps': 5, 'weight':150.0, 'RPE': 9.5, 'set_no': 5}]),
                        ('170@7@7,5@8,5@9@9,5', [{'reps': '', 'weight':170.0, 'RPE': 7.0, 'set_no': 1},
                                                   {'reps': '', 'weight':170.0, 'RPE': 7.5, 'set_no': 2},
                                                   {'reps': '', 'weight':170.0, 'RPE': 8.5, 'set_no': 3},
                                                   {'reps': '', 'weight':170.0, 'RPE': 9.0, 'set_no': 4},
                                                   {'reps': '', 'weight':170.0, 'RPE': 9.5, 'set_no': 5}]),
                        ('170@7@7,5@8,5@9@9,5 190x1@9 200x1@10', [{'reps': '', 'weight':170.0, 'RPE': 7.0, 'set_no': 1},
                                                   {'reps': '', 'weight':170.0, 'RPE': 7.5, 'set_no': 2},
                                                   {'reps': '', 'weight':170.0, 'RPE': 8.5, 'set_no': 3},
                                                   {'reps': '', 'weight':170.0, 'RPE': 9.0, 'set_no': 4},
                                                   {'reps': '', 'weight':170.0, 'RPE': 9.5, 'set_no': 5},
                                                   {'reps': 1, 'weight':190.0, 'RPE': 9.0, 'set_no': 6},
                                                   {'reps': 1, 'weight':200.0, 'RPE': 10.0, 'set_no': 7}]),
                      )

    def test_sets_done_from_string(self):
        e = opl.Exercise()
        for sets_str, output_dict in self.correct_results:
            result = e.sets_done_from_string(sets_str)
            print('test_sets_done_from_string: {}'.format(result))
            self.assertEqual(result, output_dict, msg='{}, {}'.format(result, output_dict))

class SetsPlannedParsing(unittest.TestCase):
    correct_results = ( ('x8@9', [{ }]),
                        ('3x5@80%'), [{ }],
            )

    def test_sets_planned_from_string(self):
        pass

if __name__ == '__main__':
    unittest.main()
