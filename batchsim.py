from __future__ import print_function, division
import battlesimlib as bsl
import pokelibrary3 as plib
import csvimport as cv
import csv
try: input = raw_input
except NameError: pass

# in batchsim 2.0, you can enter the name of a CSV file instead of an attacker (or defender)
# name. Then, instead of matching a single pokemon against that defender (or attacker),
# it will match all pokemon which are in the CSV file against that defender (or attacker).

# in addition, instead of writing a specific move, you can write "all", and it will
# test all moves.

#it will output: 

# raise Exception("""Problems:
# -Alakazam always seems to end with 100 energy
#    """)

#current GM file path:
GMfilepath = plib.GMFileName_Current
bsl.graphical = False
bsl.trollMode = False
bsl.showlog = False
bsl.gymmode = True

input_csv = "pokemoninput.csv"
output_csv = "battlesoutput.csv"

def metric1(dfdrDmgTaken, dfdrMaxHP, atkrDmgTaken, atkrMaxHP, n_repeats):
    dfdrDmgTakenPerMaxHP = dfdrDmgTaken/dfdrMaxHP
    atkrDmgTakenPerMaxHP = atkrDmgTaken/atkrMaxHP

    metric = 100*(dfdrDmgTakenPerMaxHP - atkrDmgTakenPerMaxHP)/n_repeats
    return metric

# This is for gym battles. Return to this later.
# def single_battle_repeat(atkr, dfdr, speciesdata, typeadvantages, n_repeats):
#     atkrDmgTaken = 0
#     dfdrDmgTaken = 0
#     totalTimeTaken_s = 0
#     atkrWins = 0
#     dfdrWins = 0
#     for m in range(n_repeats):
#         atkr.reset_stats()
#         dfdr.reset_stats()

#         # SIM RESULTS DO NOT AGREE WITH SINGLESIM RESULTS!! check atkr, dfdr stats.
#         # import ips; ips.ips()

#         # winner, atkr_postbattle, dfdr_postbattle, length_ms, tline = \
#         #     bsl.raid_singleteam_battle(atkr, dfdr, speciesdata, typeadvantages, new_battle_bool=True)
        
#         # atkr_postbattle.printstatus()
#         # dfdr_postbattle.printstatus()
#         # print()
#         atkrDmgTaken += atkr_postbattle.maxHP-atkr_postbattle.HP
#         dfdrDmgTaken += dfdr_postbattle.maxHP-dfdr_postbattle.HP
#         totalTimeTaken_s += length_ms/1000

#         if winner == 1: 
#             atkrwin = True
#             winnername = atkr_postbattle.name
#             atkrWins +=1

#         if winner == 2: 
#             atkrwin = False
#             winnername = dfdr_postbattle.name
#             dfdrWins +=1

#         if winner == -1: 
#             atkrwin = "TIE!"
#             winnername = "NOBODY"
#         # print("%s won battle %d" % (winnername, n+1))
#         # outputrow = data[n] + [win, length_ms/1000, atkr_postbattle.HP, dfdr_postbattle.HP,
#         #     atkr_postbattle.energy, dfdr_postbattle.energy]

#     metric = metric1(dfdrDmgTaken, dfdr.maxHP, atkrDmgTaken, atkr.maxHP, n_repeats)

#     atkrDPS = dfdrDmgTaken/totalTimeTaken_s
#     dfdrDPS = atkrDmgTaken/totalTimeTaken_s
#     totalTimeTaken_s = totalTimeTaken_s/n_repeats

#     return [atkrWins, dfdrWins, metric, totalTimeTaken_s, atkrDPS, dfdrDPS]
ans1 = input("Dodge cmoves if free? y/n: ").strip()
if ans1 == "y": dodgeCMovesIfFree = True
else: 
    dodgeCMovesIfFree = False
    print("Okay, attacker will not dodge at all.")

ans2 = input("Let CPU use randomness, as in the real game? y/n: ").strip()
if ans2 == "y": randomness = True
else: 
    randomness = False
    print("Okay, defender will not use randomness.")

def raid_singleplayer_repeat(atkrs, dfdr, speciesdata, typeadvantages, n_repeats, 
    nOtherPlayers, dodgeCMovesIfFree, randomness):
    total_atkr_HPloss = 0
    total_dfdr_nonbackground_HPloss = 0
    total_time_taken_s = 0

    for m in range(n_repeats):
        raidwinner, atkrs_postbattle, dfdr_postbattle, length_ms, tline = \
            bsl.raid_singleteam_battle(atkrs, dfdr, speciesdata, typeadvantages, nOtherPlayers,
                dodgeCMovesIfFree, randomness)
        total_atkrteam_HPloss += \
            sum([atkr_postbattle.maxHP-max(atkr_postbattle.HP, 0) for pk in atkrs_postbattle])
        if nOtherPlayers==0:
            # use dfdr_postbattle.maxHP because that has been doubled already
            total_dfdr_nonbackground_HPloss += (dfdr_postbattle.maxHP - max(dfdr_postbattle.HP,0))
        else:
            # this is slightly inaccurate because it doesn't subtract overkill damage,
            # or else we'd always use it.
            total_dfdr_nonbackground_HPloss += dfdr_postbattle.nonbackground_damage_taken

        total_time_taken_s += length_ms/1000

    # metric 1: what is the team's %HP loss, on average?
    atkrteam_maxHP = sum([atkr.maxHP for atkr in atkrs])
    avg_atkrteam_HPloss = total_atkrteam_HPloss/n_repeats
    avg_atkrteam_HPloss_normalized = avg_atkrteam_HPloss/atkrteam_maxHP

    # metric 2: what is the team's avg DPS divided by the DPS needed to win in time?
    avg_atkrteam_DPS = total_dfdr_nonbackground_HPloss/total_time_taken_s
    avg_atkr_DPS = avg_atkrteam_DPS/len(atkrs)
    DPS_to_win = plib.raidboss_dict[dfdr.name]['HP']/bsl.CLOCKRAIDSTARTMS
    avg_atkrteam_DPS_normalized = avg_atkrteam_DPS/DPS_to_win
    return avg_atkrteam_HPloss_normalized, avg_atkrteam_DPS_normalized, avg_atkr_DPS


def expandColumnsOfSingleInputRow(inputrow, fmovedata, cmovedata, speciesdata, atkrDexNumber, dfdrDexNumber):
    # if "all" was written, write out all combinations.
    atkr_species = speciesdata[atkrDexNumber]
    dfdr_species = speciesdata[dfdrDexNumber]
    if "all" in inputrow[1]:
        atkrFMovesToSimulate = atkr_species.fmoves
        if "non-legacy" in inputrow[1]:
            atkrFMovesToSimulate = \
                [x for x in atkrFMovesToSimulate if not (x.name in atkr_species.legacyfmnames)]
    else: atkrFMovesToSimulate = [plib.getFMoveObject(inputrow[1],fmovedata)]

    if "all" in inputrow[2]:
        atkrCMovesToSimulate = atkr_species.cmoves
        if "non-legacy" in inputrow[2]:
            atkrCMovesToSimulate = \
                [x for x in atkrCMovesToSimulate if not (x.name in atkr_species.legacycmnames)]
    else: atkrCMovesToSimulate = [plib.getCMoveObject(inputrow[2], cmovedata)]

    if "all" in inputrow[4]:
        dfdrFMovesToSimulate = dfdr_species.fmoves
        if "non-legacy" in inputrow[4]:
            dfdrFMovesToSimulate = \
                [x for x in dfdrFMovesToSimulate if not (x.name in dfdr_species.legacyfmnames)]
    else: dfdrFMovesToSimulate = [plib.getFMoveObject(inputrow[4], fmovedata)]

    if "all" in inputrow[5]:
        dfdrCMovesToSimulate = dfdr_species.cmoves
        if "non-legacy" in inputrow[5]:
            dfdrCMovesToSimulate = \
                [x for x in dfdrCMovesToSimulate if not (x.name in dfdr_species.legacycmnames)]
    else: dfdrCMovesToSimulate = [plib.getCMoveObject(inputrow[5], cmovedata)]

    return atkrFMovesToSimulate, atkrCMovesToSimulate, dfdrFMovesToSimulate, dfdrCMovesToSimulate

def format_input_part_1(inputrow_part1, atkr, dfdr, speciesdata):
    # Some formatting. First rename "all" to actual move names
    formatted_row = inputrow_part1
    formatted_row[1] = atkr.fmove.name
    formatted_row[2] = atkr.cmove.name
    formatted_row[4] = dfdr.fmove.name
    formatted_row[5] = dfdr.cmove.name
    
    # then mark legacy move names with a star
    if atkr.fmove.name in speciesdata[atkrDexNumber].legacyfmnames: 
        formatted_row[1] = "*" + formatted_row[1]
    if atkr.cmove.name in speciesdata[atkrDexNumber].legacycmnames: 
        formatted_row[2] = "*" + formatted_row[2]
    if dfdr.fmove.name in speciesdata[dfdrDexNumber].legacyfmnames: 
        formatted_row[4] = "*" + formatted_row[4]
    if dfdr.cmove.name in speciesdata[dfdrDexNumber].legacycmnames: 
        formatted_row[5] = "*" + formatted_row[5]

    return formatted_row

def write_to_csv(output_csv, inputColHeaders, outputColHeaders, outputdata):
    with open(output_csv, 'wb') as csvfile:
        mywriter = csv.writer(csvfile)
        mywriter.writerow(inputColHeaders[:6] + outputColHeaders + inputColHeaders[6:])
        for line in outputdata:
            mywriter.writerow(line)
        csvfile.close()


print("\nThis program runs a batch of simulations at once.")

inputColHeaders = [
    "attacker's dex number or name",
    "attacker's fast move",
    "attacker's charge move",
    "defender's dex number or name",
    "defender's fast move",
    "defender's charge move", # [5]

    "attacker's pokemon level", # [6]
    "attacker's ATK IV (from 0 to 15)",
    "attacker's DEF IV (from 0 to 15)",
    "attacker's STA IV (from 0 to 15)",
    "defender's pokemon level", # [10]
    "defender's ATK IV (from 0 to 15)",
    "defender's DEF IV (from 0 to 15)",
    "defender's STA IV (from 0 to 15)",
    "number of battle repeats" # [14]
    ]

print("It needs input via a csv file named 'pokemoninput.csv'. "
    + "if you want to change the input, open it in excel. "
    + "The csv file must be in the same folder as this script.\n")

print("Importing game master file. It should be in this folder, named \n'%s'." %
    GMfilepath)
print("... ", end="")
fmovedata, cmovedata, speciesdata, CPMultiplier, typeadvantages = \
    plib.importAllGM()

data = cv.importcsv(input_csv,
    typelist = ['s', 's', 's', 's', 's', 's', 
        'f', 'i', 'i', 'i', 
        'f', 'i', 'i', 'i', 'i'])

outputdata = []
print("Simulating battles... ")

# modification for batch batch sims
outputColHeaders = ['atkrWins', 'dfdrWins', 'metric', 'avg battle time (s)',
    'atkrDPS', 'dfdrDPS']

inputColHeaderLengths = [len(x) for x in inputColHeaders]
outputColHeaderLengths = [len(x) for x in outputColHeaders]
def main():
    for n in range(1,len(data)):
        inputrow = [data[n][k].lower() for k in range(6)] + data[n][6:]
        # inputrow[0] = atkr name
        # inputrow[1] = atkr fmove
        # inputrow[2] = atkr cmove
        # inputrow[3] = dfdr name
        # inputrow[4] = dfdr fmove
        # inputrow[5] = dfdr cmove

        # extract from the input row
        atkrDexNumber = plib.getPokedexNumber(inputrow[0], speciesdata)
        dfdrDexNumber = plib.getPokedexNumber(inputrow[3], speciesdata)    
        atkrFMovesToSimulate, atkrCMovesToSimulate, dfdrFMovesToSimulate, dfdrCMovesToSimulate = (
            expandColumnsOfSingleInputRow(inputrow, fmovedata, cmovedata, speciesdata, atkrDexNumber, dfdrDexNumber))
        atkrlvl = inputrow[6]
        atkrIVs = inputrow[7:10]
        nOtherPlayers = int(inputrow[10])

        # old, from when it was with gym defenders
        # dfdrlvl = inputrow[10]
        # dfdrIVs = inputrow[11:14]

        n_repeats = data[n][14]

        # simulate all combinations of atkr/dfdr fmove/cmove in this row
        outputdata0 = []
        for atkr_fm in atkrFMovesToSimulate:
            for atkr_cm in atkrCMovesToSimulate:
                for dfdr_fm in dfdrFMovesToSimulate:
                    for dfdr_cm in dfdrCMovesToSimulate:

                        atkrs = [plib.pokemon(speciesdata[atkrDexNumber], 
                            atkrIVs, plib.CPM(atkrlvl, CPMultiplier), atkr_fm, atkr_cm, 
                            poketype="player") for _ in range(6) ]

                        dfdr = plib.pokemon(speciesdata[dfdrDexNumber], 
                            dfdrIVs, plib.CPM(dfdrlvl, CPMultiplier), dfdr_fm, dfdr_cm,
                            poketype="gym_defender")

                        # results has [atkrWins, dfdrWins, metric, totalTimeTaken_s, atkrDPS, dfdrDPS]
                        results = raid_singleplayer_repeat(atkrs, dfdr, speciesdata, typeadvantages, 
                            n_repeats, nOtherPlayers, dodgeCMovesIfFree, randomness)

                        atkr.printstatus()
                        dfdr.printstatus()
                        print()
                        inputrow_part1 = format_input_part_1([x for x in data[n][:6]], atkr, dfdr, speciesdata)
                        inputrow_part2 = [x for x in data[n][6:]]
                        outputrow0 = inputrow_part1 + results + inputrow_part2
                        outputdata0 += [outputrow0]
        # perform averaging. For now, only handle the non-legacy case, and for defenders only.
        average_dfdr_fmoves = True if "average all non-legacy" in inputrow[4] else False
        average_dfdr_cmoves = True if "average all non-legacy" in inputrow[5] else False

        if average_dfdr_fmoves:
            dfdr_cm_names = cv.transpose(outputdata0)[5]
            outputdata0_averaged = []
            # list(set()) gets just the unique values
            for dfdr_cm_name in list(set(dfdr_cm_names)):
                # sum over all results with this particular cm_name.
                # results has [atkrWins, dfdrWins, metric, length_s, atkrDPS, dfdrDPS].
                results_summed = [0, 0, 0, 0, 0, 0]
                # keep track of indices to remove what we averaged over
                indices = []
                for n in range(len(outputdata0)):
                    if outputdata0[n][5] == dfdr_cm_name:
                        results_summed = [x+y for (x,y) in zip(results_summed, outputdata0[n][6:12])]
                        indices += [n]
                results_avgd = [x/len(indices) for x in results_summed]
                averaged_full_row = ([ outputdata0[0][:4] + ["average all non-legacy"] 
                    + [dfdr_cm_name] + results_avgd + outputdata0[0][12:]])
                # delete the non-averaged rows
                outputdata0 = [outputdata0[n] for n in range(len(outputdata0)) if not (n in indices)]
                # add the averaged one back
                outputdata0 += averaged_full_row
        
        if average_dfdr_cmoves:
            dfdr_fm_names = cv.transpose(outputdata0)[4]
            outputdata0_averaged = []
            # list(set()) gets just the unique values.
            for dfdr_fm_name in list(set(dfdr_fm_names)):
                results_summed = [0, 0, 0, 0, 0, 0]
                indices = []
                for n in range(len(outputdata0)):
                    if outputdata0[n][4] == dfdr_fm_name:
                        results_summed = [x+y for (x,y) in zip(results_summed, outputdata0[n][6:12])]
                        indices += [n]
                results_avgd = [x/len(indices) for x in results_summed]
                averaged_full_row = ([ outputdata0[0][:5] + ["average all non-legacy"]
                    + results_avgd + outputdata0[0][12:]])
                # delete the non-averaged rows
                outputdata0 = [outputdata0[n] for n in range(len(outputdata0)) if not (n in indices)]
                # add the averaged one back
                outputdata0 += averaged_full_row

        outputdata += outputdata0

    # sort results by atkrDPS
    outputdata.sort(key = lambda x: -x[10])
        
    print("done.")


    print("Writing to file %s... " % output_csv, end="")

    try: 
        write_to_csv(output_csv, inputColHeaders, outputColHeaders, outputdata)
    except IOError as e:
        # if they have battlesoutput.csv open, warn them to close it and try again.
        if e.errno != 13: raise e
        ans = input("\nPermission denied: Please close battlesoutput.csv and then type 'go': ")
        if not (ans in ["go", "g", "o"]): raise e
        print("Thanks. Trying again...")
        write_to_csv(output_csv, inputColHeaders, outputColHeaders, outputdata)

    print("done.")
    print("You will find the results in '%s' in this folder." % 
        output_csv)
    return
