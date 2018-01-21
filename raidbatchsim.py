from __future__ import print_function, division
import battlesimlib as bsl
import pokelibrary as plib
import csvimport as cv
import csv
import copy
import itertools
import time
import math
try: input = raw_input
except NameError: pass

# in batchsim 2.0, you can enter the name of a CSV file instead of an attacker (or defender)
# name. Then, instead of matching a single pokemon against that defender (or attacker),
# it will match all pokemon which are in the CSV file against that defender (or attacker).

# in addition, instead of writing a specific move, you can write "all", and it will
# test all moves.

# to do:
# -investigate the low win%s for these raids. what's up with that?

"""
The metrics used here are:
1. Win percentage
    -Just for kicks
2. Atkr_DPS
    -Used for offensive metric in solo and team raids.
3. Atkr DPS / minimum needed DPS
    -It has to be >1 for your DPS to be high enough to beat the timer
4. Dfdr_DPS
    -Just for kicks
5. Atkr DPS as % of enemy HP
    -Used for defensive constraint in solo raids
6. Dfdr DPS as % of enemy HP
    -Used for defensive constraint in solo raids
7. TTW_defender per single poke 
    -TTW stands for "time to win".
    -Used for defensive constraint in team raids
    -Used for offensive metric in solo and team raids.
8. TTW for attackers.
    -For comparison with pokebattler

The metrics are used for:
For team raids:
1. The defensive constraint: 
    TTW_defender > 0.9 * time limit: do not die before 90% of time has run out.
2. The offensive metric:
    Atkr_DPS is maximized for the team. 
    -This is calculated as: for each pk on the team, sorted from high > low DPS,
    add atkr_i_DPS * min(TTL_against_this_atkr, time_remaining). Result is TDO.
    Then divide by the battle length.
For solo raids:
3. The defensive constraint:
    Atkr DPS as % > Dfdr DPS as %: do not die before killing the boss.
    No constraint is needed for time limits: beyond the first one, you just optimize DPS.
    If you optimize atkrDPS with just the first constraint and STILL run out of time, then
    you cannot beat the timer anyway. So the timer can be ignored when choosing a team.
4. The offensive metric:
    Atkr_DPS is maximized. It's the same as the offensive metric for team raids.

"""

#current GM file path:
GMfilepath = plib.GMFileName_Current
bsl.graphical = False
bsl.trollMode = False
bsl.showlog = False
bsl.gymmode = True

input_csv = "pokemoninput_raid.csv"
output_csv = "battlesoutput.csv"

input_col_headers = [
    "atkr name or pokedex number",
    "atkr fmove",
    "atkr cmove",
    "raid boss",
    "boss fmove",
    "boss cmove",
    "atkr lvl",
    "atkr atkIV",
    "atkr defIV",
    "atkr staIV",
    "nOtherPlayers",
    "nRepeats",
    "dodgeCmovesIfFree?",
    "randomness"]
output_col_headers = [\
    "win_percent",
    "atkr_DPS_riskadjusted",
    "atkr_TDO_riskadjusted",
    "TTL_riskadjusted",
    "atkr_DPS_avg", "atkr_DPS_absdev",
    "normalized_DPS_avg", "normalized_DPS_absdev",
    "dfdr_DPS_avg", "dfdr_DPS_absdev",
    "atkr_percent_DPS_avg", "atkr_percent_DPS_absdev",
    "dfdr_percent_DPS_avg", "dfdr_percent_DPS_absdev",
    "TTL_s_avg", "TTL_s_absdev",
    "TTW_s_avg", "TTW_s_absdev",
    "atkr_TDO_avg", "atkr_TDO_absdev",
    "battle_duration_avg"
    ]
col_headers = input_col_headers + output_col_headers
# These are the indices of outputdata that are used in this file:
DPS_RAi = 15
TDO_RAi = 16
TTL_RAi = 17
DPSi = 18
DPSdevi = 19
TDOi = 32
TDOdevi = 33

ans1 = input("Select the optimal team of 6 after simulations end? y/n: ")
select_optimal_team = True if ans1 in ['y', 'yes', 'yy'] else False

print("Importing game master file. It should be in this folder, named \n'%s'..." %
    GMfilepath)
fmovedata, cmovedata, speciesdata, CPMultiplier, typeadvantages = \
    plib.importAllGM()
print("This program needs input via a csv file named 'pokemoninput_raid.csv'. "
    + "if you want to change the input, open it in excel. "
    + "The csv file must be in the same folder as this script.")
data = cv.importcsv(input_csv,
    typelist = ['s', 's', 's', 's', 's', 's',  # [0-5]: names and moves
        'f', 'i', 'i', 'i',     # [6-9]:   atkr lvl and IVs
        'i', 'i',               # [10-11]: nOtherPlayers, nRepeats
        'b', 'b'])              # [12-13]: dodgeCmovesIfFree, randomness)

def expandColumnsOfSingleInputRow(inputrow, fmovedata, cmovedata, speciesdata, atkrDexNumber, dfdrDexNumber):
    # if "all" was written, write out all combinations.
    atkr_species = speciesdata[atkrDexNumber]
    dfdr_species = speciesdata[dfdrDexNumber]
    if "all" in inputrow[1]:
        atkrFMovesToSimulate = atkr_species.fmoves
        if "non legacy" in inputrow[1]:
            atkrFMovesToSimulate = \
                [x for x in atkrFMovesToSimulate if not (x.name in atkr_species.legacyfmnames)]
    else: atkrFMovesToSimulate = [plib.getFMoveObject(inputrow[1],fmovedata)]

    if "all" in inputrow[2]:
        atkrCMovesToSimulate = atkr_species.cmoves
        if "non legacy" in inputrow[2]:
            atkrCMovesToSimulate = \
                [x for x in atkrCMovesToSimulate if not (x.name in atkr_species.legacycmnames)]
    else: atkrCMovesToSimulate = [plib.getCMoveObject(inputrow[2], cmovedata)]

    if "all" in inputrow[4]:
        dfdrFMovesToSimulate = dfdr_species.fmoves
        if "non legacy" in inputrow[4]:
            dfdrFMovesToSimulate = \
                [x for x in dfdrFMovesToSimulate if not (x.name in dfdr_species.legacyfmnames)]
    else: dfdrFMovesToSimulate = [plib.getFMoveObject(inputrow[4], fmovedata)]

    if "all" in inputrow[5]:
        dfdrCMovesToSimulate = dfdr_species.cmoves
        if "non legacy" in inputrow[5]:
            dfdrCMovesToSimulate = \
                [x for x in dfdrCMovesToSimulate if not (x.name in dfdr_species.legacycmnames)]
    else: dfdrCMovesToSimulate = [plib.getCMoveObject(inputrow[5], cmovedata)]

    return atkrFMovesToSimulate, atkrCMovesToSimulate, dfdrFMovesToSimulate, dfdrCMovesToSimulate

def format_move_names(inputrow_part1, atkr, dfdr, speciesdata):
    atkrDexNumber = plib.getPokedexNumber(atkr.name, speciesdata)
    dfdrDexNumber = plib.getPokedexNumber(dfdr.name, speciesdata)

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

def raid_singleplayer_repeat(atkrs, dfdr, speciesdata, typeadvantages, n_repeats, 
    nOtherPlayers, dodgeCMovesIfFree, randomness):
    timelimit_ms = ( bsl.TIMELIMIT_LEGENDARYRAID_MS if plib.raidboss_dict[dfdr.name]["lvl"] == 5
        else bsl.TIMELIMIT_NORMALRAID_MS )

    atkr_wincount = 0
    atkr_DPS_list = []
    dfdr_DPS_list = []
    TTL_s_list = []
    battle_durations = []

    for m in range(n_repeats):
        # a deepcopy will completely recreate the elements of the list, which is 
        # necessary since objects (pokemon) are mutable.
        atkrs_copy = copy.deepcopy(atkrs)
        dfdr_copy = copy.deepcopy(dfdr)
        raidwinner, atkrs_postbattle, dfdr_postbattle, length_ms, tline = \
            bsl.raid_singleteam_battle(atkrs_copy, dfdr_copy, speciesdata, typeadvantages, 
                nOtherPlayers, dodgeCMovesIfFree, randomness)

        if raidwinner == 1: atkr_wincount += 1

        atkr_DPS_list += [(dfdr_postbattle.nonbackground_damage_taken/(length_ms/1000))]

        total_atkr_HP_lost = sum([atkr.maxHP-max(atkr.HP,0) for atkr in atkrs_postbattle])
        dfdr_DPS_list += [total_atkr_HP_lost/(length_ms/1000)]
        
        n_atkrs_killed = total_atkr_HP_lost / atkrs[0].maxHP
        TTL_s_list += [(length_ms/1000)/n_atkrs_killed]

        battle_durations += [length_ms/1000]

    # metric 1: Atkr win percentage
    win_percent = atkr_wincount / n_repeats

    # metric 2: Risk-adjusted atkr DPS (calculated after atkr DPS)

    # metric 3: Risk-adjusted atkr TTL (calculated after atkr TTL)

    # metric 4: Risk-adjusted atkr TDO (calculated after atkr TDO)

    # metric 5: Atkr DPS
    atkr_DPS_avg = sum(atkr_DPS_list)/n_repeats
    atkr_DPS_absdev = sum([abs(x-atkr_DPS_avg) for x in atkr_DPS_list])/n_repeats
    atkr_DPS_riskadjusted = atkr_DPS_avg - 0.5 * atkr_DPS_absdev

    # metric 6: Atkr DPS / minimum needed DPS
    boss_HP = plib.raidboss_dict[dfdr.name]['HP']
    DPS_to_win = boss_HP / (timelimit_ms/1000)
    normalized_DPS_avg = atkr_DPS_avg / DPS_to_win
    normalized_DPS_absdev = atkr_DPS_absdev / DPS_to_win

    # metric 7: Dfdr DPS
    dfdr_DPS_avg = sum(dfdr_DPS_list)/n_repeats
    dfdr_DPS_absdev = sum([abs(x-dfdr_DPS_avg) for x in dfdr_DPS_list])/n_repeats

    # metric 8: Atkr DPS as % enemy HP
    atkr_percent_DPS_avg = atkr_DPS_avg / boss_HP
    atkr_percent_DPS_absdev = atkr_DPS_absdev / boss_HP

    # metric 9: Dfdr DPS as % atkrteam HP
    atkrteam_HP = sum([atkr.maxHP for atkr in atkrs])
    dfdr_percent_DPS_avg = dfdr_DPS_avg / atkrteam_HP
    dfdr_percent_DPS_absdev = dfdr_DPS_absdev / atkrteam_HP

    # metric 10: Atkr time to lose (TTL) per single poke
    TTL_s_avg = sum(TTL_s_list)/n_repeats
    TTL_s_absdev = sum([abs(x-TTL_s_avg) for x in TTL_s_list])/n_repeats
    TTL_riskadjusted = TTL_s_avg - 0.5 * TTL_s_absdev

    # metric 11: Atkr time to win (TTW)
    TTW_s_list = [boss_HP / DPS for DPS in atkr_DPS_list]
    TTW_s_avg = sum(TTW_s_list)/n_repeats
    TTW_s_absdev = sum([abs(x-TTW_s_avg) for x in TTW_s_list])/n_repeats

    # metric 12: TDO for attackers
    atkr_TDO_list = [atkr_DPS_list[n]*TTL_s_list[n] for n in range(n_repeats)]
    atkr_TDO_avg = sum(atkr_TDO_list)/n_repeats
    atkr_TDO_absdev = sum([abs(x-atkr_TDO_avg) for x in atkr_TDO_list])/n_repeats
    atkr_TDO_riskadjusted = atkr_TDO_avg - 0.5 * atkr_TDO_absdev

    # metric 13: battle length (s)
    battle_duration_avg = sum(battle_durations)/n_repeats

    return [win_percent,
        atkr_DPS_riskadjusted,
        atkr_TDO_riskadjusted,
        TTL_riskadjusted,
        atkr_DPS_avg, atkr_DPS_absdev,
        normalized_DPS_avg, normalized_DPS_absdev,
        dfdr_DPS_avg, dfdr_DPS_absdev,
        atkr_percent_DPS_avg, atkr_percent_DPS_absdev,
        dfdr_percent_DPS_avg, dfdr_percent_DPS_absdev,
        TTL_s_avg, TTL_s_absdev,
        TTW_s_avg, TTW_s_absdev,
        atkr_TDO_avg, atkr_TDO_absdev,
        battle_duration_avg
        ]


est_time_mins = (22/60) * (len(data)*int(data[1][11])/(47*10)) 
print("Simulating battles. Estimated time needed: %.2f minutes." % est_time_mins)
print("Takes six times as long with multiple attackers per input row.")
print("================================================================")
time.sleep(2)
outputdata = []
for n in range(1,len(data)):
    inputrow = [data[n][k].lower() for k in range(6)] + data[n][6:]
    for k in range(6):
        inputrow[k] = inputrow[k].replace("_"," ").lower()
        inputrow[k] = inputrow[k].replace("-"," ")
        inputrow[k] = inputrow[k].replace(","," ")
        
    atkr_name = inputrow[0]
    dfdr_name = inputrow[3]
    # inputrow[1] = atkr fmove
    # inputrow[2] = atkr cmove
    # inputrow[4] = boss fmove
    # inputrow[5] = boss cmove

    # extract from the input row
    atkrDexNumber = plib.getPokedexNumber(atkr_name, speciesdata)
    dfdrDexNumber = plib.getPokedexNumber(dfdr_name, speciesdata)    
    atkrFMovesToSimulate, atkrCMovesToSimulate, dfdrFMovesToSimulate, dfdrCMovesToSimulate = (
        expandColumnsOfSingleInputRow(inputrow, fmovedata, cmovedata, speciesdata, atkrDexNumber, dfdrDexNumber))
    print("simulating:\n%s" % atkr_name, end=", ")
    for x in atkrFMovesToSimulate: print(x.name, end=" ")
    print("with ", end="")
    for x in atkrCMovesToSimulate: print(x.name, end=" ")
    print("\nvs. ")
    for x in dfdrFMovesToSimulate: print(x.name, end=" ")
    print("with ", end="")
    for x in dfdrCMovesToSimulate: print(x.name, end=" ")
    print()
    print()
    atkr_lvl = inputrow[6]
    atkrIVs = inputrow[7:10]
    nOtherPlayers = inputrow[10]
    n_repeats = inputrow[11]
    dodgeCMovesIfFree = inputrow[12]
    randomness = inputrow[13]

    if n_repeats == 0: raise Exception("Error: n_repeats must be > 0. Please modify input data.")

    # For raidbosses, CPM and IVs will be re-assigned when the pokemon() is created,
    # so give them arbitrary values now:
    dfdrIVs = [15, 15, 15]
    dfdrCPM = 1

    # simulate all combinations of atkr/dfdr fmove/cmove in this row
    outputdata0 = []
    for atkr_fm, atkr_cm, dfdr_fm, dfdr_cm in itertools.product(
        atkrFMovesToSimulate, atkrCMovesToSimulate, dfdrFMovesToSimulate, dfdrCMovesToSimulate):
            
        atkrs = [
            plib.pokemon(speciesdata[atkrDexNumber], atkrIVs, plib.CPM(
                atkr_lvl, CPMultiplier), 
            atkr_fm, atkr_cm, poketype="player") for _ in range(6) ]
        
        dfdr = plib.pokemon(speciesdata[dfdrDexNumber], dfdrIVs, dfdrCPM, 
            dfdr_fm, dfdr_cm, poketype="raid_boss")

        # results has:
        # win_percent, 
        # atkr_DPS_avg, atkr_DPS_absdev,
        # normalized_DPS_avg, normalized_DPS_absdev,
        # dfdr_DPS_avg, dfdr_DPS_absdev,
        # atkr_percent_DPS_avg, atkr_percent_DPS_absdev,
        # dfdr_percent_DPS_avg, dfdr_percent_DPS_absdev,
        # TTL_s_avg, TTL_s_absdev,
        # TTW_s_avg, TTW_s_absdev
        results = raid_singleplayer_repeat(atkrs, dfdr, speciesdata, typeadvantages, 
            n_repeats, nOtherPlayers, dodgeCMovesIfFree, randomness)
        
        inputrow_part1 = format_move_names([x for x in data[n][:6]], atkrs[0], dfdr, speciesdata)
        inputrow_part2 = [x for x in data[n][6:]]
        row = inputrow_part1 + inputrow_part2 + results
        outputdata0 += [row]
    # perform averaging. For now, only handle the non-legacy case, and for defenders only.
    average_dfdr_fmoves = True if "average all non legacy" in inputrow[4] else False
    average_dfdr_cmoves = True if "average all non legacy" in inputrow[5] else False

    results_length = len(output_col_headers)
    results_index = len(input_col_headers)

    if average_dfdr_fmoves:
        outputdata0T = cv.transpose(outputdata0)
        remaining_atkrFMoves = list(set(outputdata0T[1]))
        remaining_atkrCMoves = list(set(outputdata0T[2]))
        remaining_dfdrCMoves = list(set(outputdata0T[5]))
        for atkr_fm_name, atkr_cm_name, dfdr_cm_name in itertools.product(
            remaining_atkrFMoves, remaining_atkrCMoves, remaining_dfdrCMoves):
            results_summed = [0] * results_length
            indices = []
            # average all rows with these moves
            for n in range(len(outputdata0)):
                row = outputdata0[n]
                if [row[k] for k in [1, 2, 5]] == [atkr_fm_name, atkr_cm_name, dfdr_cm_name]:
                    results_summed = [x+y for (x,y) in zip(results_summed, row[results_index:])]
                    indices += [n]
            results_avgd = [x/len(indices) for x in results_summed]
            # combine the averaged results into a full row
            averaged_full_row = (
                [atkr_name, atkr_fm_name, atkr_cm_name, 
                dfdr_name, "average all non legacy", dfdr_cm_name]
                + row[6:results_index]
                + results_avgd)
            # delete the non-averaged rows
            outputdata0 = [outputdata0[n] for n in range(len(outputdata0)) if not (n in indices)]
            # add the averaged one back
            outputdata0 += [averaged_full_row]
        
    if average_dfdr_cmoves:
        # get unique moves remaining, as some might have already been avgd out:
        outputdata0T = cv.transpose(outputdata0)
        remaining_atkrFMoves = list(set(outputdata0T[1]))
        remaining_atkrCMoves = list(set(outputdata0T[2]))
        remaining_dfdrFMoves = list(set(outputdata0T[4]))
        for atkr_fm_name, atkr_cm_name, dfdr_fm_name in itertools.product(
            remaining_atkrFMoves, remaining_atkrCMoves, remaining_dfdrFMoves):
            results_summed = [0] * results_length
            indices = []
            # average all rows with these moves
            for n in range(len(outputdata0)):
                row = outputdata0[n]
                if [row[k] for k in [1, 2, 4]] == [atkr_fm_name, atkr_cm_name, dfdr_fm_name]:
                    results_summed = [x+y for (x,y) in zip(results_summed, row[results_index:])]
                    indices += [n]
            results_avgd = [x/len(indices) for x in results_summed]
            # combine the averaged results into a full row
            averaged_full_row = (
                [atkr_name, atkr_fm_name, atkr_cm_name, 
                dfdr_name, dfdr_fm_name, "average all non legacy"]
                + row[6:results_index]
                + results_avgd)
            # delete the non-averaged rows
            outputdata0 = [outputdata0[n] for n in range(len(outputdata0)) if not (n in indices)]
            # add the averaged one back
            outputdata0 += [averaged_full_row]
    outputdata += outputdata0
print("\ndone simulating.\n")
if select_optimal_team:
    # sort, increasing, by risk-adjusted DPS
    outputdata.sort(key = lambda x: x[DPS_RAi])

    def prop_equals(prop1, dev1, prop2, dev2):
        # the properties are equal if each is within the other's error bounds.
        # this is not an equivalence relation because a=b, b=c =/=> a=c
        one_in_two = True if prop2-dev2 < prop1 < prop2 + dev2 else False
        two_in_one = True if prop1-dev1 < prop2 < prop1 + dev1 else False
        if one_in_two and two_in_one: return True
        else: return False
    def prop_greater_than(prop1, dev1, prop2, dev2):
        # property1>property2 if it is greater and outside error bounds.
        if prop1 > prop2 + dev2: return True
        else: return False
    def pkmn_greater_than(pk1, pk2):
        # returns 1 if pk1 > pk2 in combat.
        # returns -1 if pk2 > p1 in combat. 
        # returns 0 if no conclusion could  be made.
        # Each "pk" is a row of outputdata. 

        if pk1[DPSi] > pk2[DPSi] and pk1[TDOi] > pk2[TDOi]: return 1
        if pk2[DPSi] > pk1[DPSi] and pk2[TDOi] > pk1[TDOi]: return -1

        if prop_equals(pk1[TDOi], pk1[TDOdevi], pk2[TDOi], pk2[TDOdevi]):
            if prop_greater_than(pk1[DPSi], pk1[DPSdevi], pk2[DPSi], pk2[DPSdevi]):
                return 1
        if prop_equals(pk2[TDOi], pk2[TDOdevi], pk1[TDOi], pk1[TDOdevi]):
            if prop_greater_than(pk2[DPSi], pk2[DPSdevi], pk1[DPSi], pk1[DPSdevi]):
                return -1
        return 0

    def add_to_chain(item, chain):
        # after this loop, n will be the index to place the item if successful.
        n = 0
        while n < len(chain):
            # print("n = %d, chain:" % n)
            # print(chain)
            rel = pkmn_greater_than(item, chain[n])
            if rel == 1: 
                break
            if rel == 0: 
                success = False
                return success, chain
            if rel == -1: 
                n += 1

        success = True
        if n < len(chain):
            chain = chain[:n] + [item] + chain[n:]
        else:
            chain = chain + [item]
        return success, chain

    def create_reduced_partially_ordered_set(outputdata):
        chains = []
        for n in range(len(outputdata)):
            # print("adding row %d to a chain"%n)
            pk = copy.deepcopy(outputdata[n])
            success = False
            for n in range(len(chains)):
                success, chains[n] = add_to_chain(pk, chains[n])
                if success:
                    break
            if not success:
                chains += [[pk]]

        # make the set smaller by removing links which are the 7th or higher element of a chain.
        for n in range(len(chains)):
            if len(chains[n]) >= 7:
                print("reducing possibilities by %d items." % (len(chains[n]) - 6))
                chains[n] = chains[n][:6]

        return chains

    def predicted_battle_duration(predicted_DPS, others_DPS):
        predicted_total_DPS = predicted_DPS + others_DPS
        predicted_TTW = plib.raidboss_dict[dfdr_name]["HP"] / predicted_total_DPS
        return min(timelimit_ms/1000, predicted_TTW)

    print("original pokebox size: %d" % len(outputdata))
    poset = create_reduced_partially_ordered_set(outputdata)
    outputdata2 = []
    for ch in poset:
        outputdata2 += ch
    outputdata = outputdata2
    print("new pokebox size: %d" % len(outputdata))
    # ok now we have reduced the possibilities through partial ordering.
    # time to just do all the combinations...
    possible_teams = itertools.combinations(outputdata, 6)

    # define a combination fn to find out how many iterations there will be
    from operator import mul
    from fractions import Fraction
    def ncr(n,r): 
      return int( reduce(mul, (Fraction(n-i, i+1) for i in range(r)), 1) )
    n_possible_teams = ncr(len(outputdata), 6)

    print("\nThere are %d possible teams. Finding the best one now..." % n_possible_teams)
    print("Estimated time (minutes) is %.1f. Please be patient." 
        % (1.5 * n_possible_teams/3838380))
    topteams = [[], [], []]
    topdamages = [0, 0, 0]

    predicted_others_DPS = ( nOtherPlayers * bsl.vs_lugia_DPS_per_other_player 
        * (bsl.lugia_base_DEF_adj/(speciesdata[dfdrDexNumber].base_DEF+plib.raidboss_IVs[1])))
    predicted_others_DPS_deviation = math.sqrt(predicted_others_DPS)

    tstart = time.time()
    timelimit_ms = plib.raidboss_dict[dfdr_name]["timelimit_ms"]
    for team in possible_teams:
        # sort by risk-adjusted DPS
        team = list(team)
        team.sort(key = lambda x: -x[DPS_RAi])


        predicted_DPS = team[3][DPSi]
        others_DPS = [predicted_others_DPS + c * predicted_others_DPS_deviation
            for c in [-1, -0.5, 0, 0, 0.5, 1]]
        battle_durations = [min(predicted_battle_duration(predicted_DPS, oDPS), timelimit_ms/1000) 
            for oDPS in others_DPS]

        survivaltime_s = sum([x[TTL_RAi] for x in team])

        # calculate damage average over the distribution of battle lengths:
        total_damage_sum = 0

        for bat_dur in battle_durations:
            current_time = 0
            total_damage = 0
            endtime_s = min(survivaltime_s, bat_dur)
            for poke in team:
                dt = poke[TTL_RAi]
                new_time = current_time + dt
                if new_time < endtime_s:
                    total_damage += poke[TDO_RAi]
                    continue
                total_damage += poke[TDO_RAi]*(dt/poke[TTL_RAi])
                break
            total_damage_sum += total_damage

        total_damage_avg = total_damage_sum / len(battle_durations)
        if total_damage_avg > topdamages[0]:
            topteams[0] = team
            topdamages[0] = total_damage
        elif total_damage_avg > topdamages[1]:
            topteams[1] = team
            topdamages[1] = total_damage
        elif total_damage_avg > topdamages[2]:
            topteams[2] = team
            topdamages[2] = total_damage

    print("calculation took %f minutes" % ((time.time() - tstart)/60))

outputdata.sort(key = lambda x: -x[DPS_RAi])
print("Writing to file %s... " % output_csv, end="")

csv_header = ["dodgeCMovesIfFree =", "", dodgeCMovesIfFree,  "randomness =", "", randomness]
csv_header2 = []
if select_optimal_team:
    csv_header2 = [["optimal teams:"]]
    for n in range(3):
        csv_header2 += [["team #%d : TDO = " %(n+1), "", topdamages[n]]] 
        csv_header2 += [col_headers]
        csv_header2 += topteams[n]
        csv_header2 += [[""]]

def write_to_csv(output_csv, col_headers, outputdata):
    with open(output_csv, 'wb') as csvfile:
        mywriter = csv.writer(csvfile)
        mywriter.writerow(csv_header)
        for line in csv_header2:
            mywriter.writerow(line)
        mywriter.writerow(col_headers)
        for line in outputdata:
            mywriter.writerow(line)
        csvfile.close()

try: 
    write_to_csv(output_csv, col_headers, outputdata)
except IOError as e:
    # if they have battlesoutput.csv open, warn them to close it and try again.
    if e.errno != 13: raise e
    ans = input("\nPermission denied: Please close battlesoutput.csv and then type 'go': ")
    if not (ans in ["go", "g", "o"]): raise e
    print("Thanks. Trying again...")
    write_to_csv(output_csv, col_headers, outputdata)

print("done.")
print("You will find the results in '%s' in this folder." % 
    output_csv)