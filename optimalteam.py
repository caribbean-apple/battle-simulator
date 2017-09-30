from __future__ import print_function, division
import pokelibrary as plib
import csvimport as cv
import csv
try: input = raw_input
except NameError: pass


input_csv = "battlesoutput.csv"
data = cv.importcsv(input_csv,
    typelist = ['s', 's', 's', 's', 's', 's',  # [0-5]: names and moves
        'f', 'i', 'i', 'i',     # [6-9]:   atkr lvl and IVs
        'i', 'i',               # [10-11]: nOtherPlayers, nRepeats
        'b', 'b',               # [12-13]: dodgeCmovesIfFree, randomness
        'i',    # [14] averageAroudnLevelDistance (NYI)
        

        ])