import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

import unittest
import logging

from utils import roundWithBias

logger = logging.getLogger(__name__)

class RoundWithBiasTest(unittest.TestCase):
    correct_results = ((2.5, 2.5),
                       (2.4,2.5),
                       (2.7, 3),
                       (3.0001, 3),
                       (0.999999, 1),
                       (0.5, 0.5),
                      )
    
    def test_rounding(self):
        for x, r in self.correct_results:
            ret = roundWithBias(x)
            logger.info(f'RoundWithBias({x}) == {ret}, correct=={r}')
            self.assertEqual(r, ret)

if __name__ == '__main__':
    unittest.main()
