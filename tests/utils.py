import inspect
import os
import sys

currentdir = os.path.dirname(
    os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

import logging
import unittest

from utils import calculate_e1RM, roundWithBias

logger = logging.getLogger(__name__)
logger.info("Starting tests/utils.py")


class RoundWithBiasTest(unittest.TestCase):
    correct_results = (
        (2.5, 2.5),
        (2.4, 2.5),
        (2.7, 2.5),
        (2.76, 3),
        (3.0001, 3),
        (0.999999, 1),
        (0.5, 0.5),
    )

    def test_rounding(self):
        for x, r in self.correct_results:
            ret = roundWithBias(x)
            msg = f'RoundWithBias({x}) == {ret}, correct=={r}'
            logger.info(msg)
            self.assertEqual(r, ret, msg=msg)


class E1rmCalcTest(unittest.TestCase):
    correct_results = (((100.0, 3, 9.0), 112.108), )

    def test_e1rm_calc(self):
        for test_input, correct_result in self.correct_results:
            result = calculate_e1RM(*test_input)

            self.assertEqual(result,
                             correct_result,
                             msg=f'{result}, {correct_result}')


if __name__ == '__main__':
    unittest.main()
