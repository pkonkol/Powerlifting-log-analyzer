'''
    Run opl as independent commandline script
'''
import argparse

import opl_spreadsheet_parser as sp
import opl_analytics as al
import opl_program_generator as pg

parser = argparse.ArgumentParser()

parser.add_argument('-i', '--input', type=str,  dest='input',
                    metavar='filepath', help="input training spreadsheet")

args = parser.parse_args()

if args.input:
    print('works')


