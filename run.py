'''
    Run opl as independent commandline script
'''
import argparse

import spreadsheet_parser as sp
import analytics as al
#import program_generator as pg

parser = argparse.ArgumentParser()

parser.add_argument('-i', '--input', type=str,  dest='input',
                    metavar='filepath', help="input training spreadsheet",
                    required=True)

parser.add_argument('-u', '--unit', type=str, dest='unit', default='kg', help="kg or lbs")



args = parser.parse_args()

if args.input:
    input_file = args.input
if args.unit:
    unit = args.unit

tsp = sp.TrainingSpreadsheetParser(input_file, unit)
tsp.parse_worksheet()
mcs = tsp.get_mesocycles()

dv = al.DataVisualizer(mcs)
dv.print_mesocycles_cmd()
