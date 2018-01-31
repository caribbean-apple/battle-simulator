from battlesimlib import *
from ui import *




def debug():

    debug_world = world()
    debug_world.importAllGM()
    
    debug_world.starting_t_ms = TIMELIMIT_GYM_MS
    debug_world.new_battle_bool = True

    # assign atkr and dfdr
    debug_world.atkr = pokemon(debug_world.speciesdata[getPokedexNumber('machamp', debug_world.speciesdata)], [15,15,15],
                               CPM(40, debug_world.CPMultiplier), 
                    debug_world.fmovedata['counter'], debug_world.cmovedata['dynamic punch'], poketype="player")
    debug_world.dfdr = pokemon(debug_world.speciesdata[getPokedexNumber('blissey', debug_world.speciesdata)], [15,15,15],
                               CPM(40, debug_world.CPMultiplier), 
                    debug_world.fmovedata['pound'], debug_world.cmovedata['hyper beam'], poketype="gym_defender")
 
    debug_world.battle_type = 'gym'
    debug_world.dodgeCMovesIfFree = True
    debug_world.randomness = True
    debug_world.weather = 'CLOUDY'

    for n in range(100):
        print("simulation:", n+1)
        debug_world.atkr.reset_stats()
        debug_world.dfdr.reset_stats()
        debug_world.elog = []
        debug_world.tline = timeline()
        winner, length_ms = raid_1v1_battle(debug_world)
        
    

    if 0:
        for msg in generate_glog(debug_world):
            print(msg)
        print()
    
    if winner == -1:
        print("It was a tie! Who knows what happens now.")
    elif winner == 1:
        print("%s won!" % debug_world.atkr.name)
    elif winner == 2:
        print("%s won!" % debug_world.dfdr.name)
    lengthsecs = length_ms/1000
    print("Ending Stats:")
    debug_world.atkr.printstatus()
    print("DPS: %.2f    EPS gain: %.2f" % (
            (debug_world.dfdr.maxHP - debug_world.dfdr.HP)/lengthsecs, 
            debug_world.atkr.total_energy_gained/lengthsecs)) 
    print()
    debug_world.dfdr.printstatus()
    print("time: %.2f seconds" % lengthsecs)



def manualuse():
    fmovedata, cmovedata, speciesdata, CPMultiplier, typeadvantages = importAllGM()
    print("Simulating. For each answer, you can just press 'y' for the default.")
    ans0 = input("Do you want to simulate a raid (of identical attackers)?\n"
        + "r = raid, g = gym battle: ").strip()
    
    if ans0 in ["r", "y"]: battle_type = "raid"
    elif ans0 == "g": battle_type = "gym"
    else: invalidInputError(ans0)

    ans1 = input("What's the attacking pokemon's name or dex number? ").lower()
    if ans1=="y": ans1="alakazam"
    ans1 = (((ans1.replace('_',' '))).replace('-'," ")).replace(',',' ')
    atkrDexNumber = getPokedexNumber(ans1, speciesdata)
    atkr_species = speciesdata[atkrDexNumber]
    atkr_name = atkr_species.name
    
    ans2 = input("And what's the defending pokemon's name or number? ").lower()
    if ans2=="y": ans2="machamp"
    ans2 = ans1 = (((ans2.replace('_',' '))).replace('-',' ')).replace(',',' ')
    dfdrDexNumber = getPokedexNumber(ans2, speciesdata)
    dfdr_species = speciesdata[dfdrDexNumber]
    dfdr_name = dfdr_species.name

    ans3 = input("Default is level 39 with 14, 14, 14 IV. Is that OK? y/n: ").lower()
    if ans3 in ["no", "n", "no."]:
        ans4 = input("OK Mr. Picky. Tell me the level and atk/def/sta IVs of the atkr " \
            "in this format: \n'32.5, 14, 15, 14' without the quotes: ")
        if not (battle_type == 'raid'):
            ans5 = input("Now also tell me the level and atk/def/sta IVs of the dfdr " \
                "in the same format: ")
    else:
        # self, pokemonspecies, IVs, CPM, fmove, cmove):
        ans4 = "39, 14, 14, 14"
        ans5 = "39, 14, 14, 14"
    ans4 = ans4.split(',')
    try: atkrlvl, atkrIVs = float(ans4[0]), [int(x.strip()) for x in ans4[1:]]
    except ValueError: invalidInputError(ans4)
    if not battle_type == 'raid':
        ans5 = ans5.split(',')
        try: dfdrlvl, dfdrIVs = float(ans5[0]), [int(x.strip()) for x in ans5[1:]]
        except ValueError: invalidInputError(ans5)

    ans6 = input("What moves does the attacker have? 'y' for default.\n" \
        "Example: '%s, %s': " % (atkr_species.fmoves[0].name,
            atkr_species.cmoves[0].name)).lower()
    ans7 = input("What moves does the defender have? 'y' for default.\n" \
        "Example: '%s, %s': " % (dfdr_species.fmoves[0].name,
            dfdr_species.cmoves[0].name)).lower()
    if 'y' == ans6: 
        ans6 = ('%s, %s' % 
            (atkr_species.fmoves[0].name, atkr_species.cmoves[0].name))
    if 'y' == ans7:
        ans7 = ('%s, %s' % 
            (dfdr_species.fmoves[0].name, dfdr_species.cmoves[0].name))
    ans6 = ans6.split(',')
    ans7 = ans7.split(',')
    ans6 = [(((x.replace('_',' '))).replace('-'," ")).replace(',',' ').strip() for x in ans6]
    ans7 = [(((x.replace('_',' '))).replace('-'," ")).replace(',',' ').strip() for x in ans7]
    try: atkr_fmove = fmovedata[ans6[0]]
    except KeyError: invalidInputError(ans6[0])
    try: atkr_cmove = cmovedata[ans6[1]]
    except KeyError: invalidInputError(ans6[1])
    try: dfdr_fmove = fmovedata[ans7[0]]
    except KeyError: invalidInputError(ans7[0])
    try: dfdr_cmove = cmovedata[ans7[1]]
    except KeyError: invalidInputError(ans7[1])

    # if raid: how many other players should attack in the background?
    if battle_type == 'raid':
        ans8 = input("How many other players should attack in the background? ")
        if ans8=="y": ans8 = 0
        nOtherPlayers = int(ans8)
    
    ans9 = input("Dodge cmoves if free? y/n: ").strip()
    if ans9 == "y":
        dodgeCMovesIfFree = True
    else: 
        dodgeCMovesIfFree = False
        print("Okay, attacker will not dodge at all.")

    ans10 = input("Let CPU use randomness, as in the real game? "
        + "This also adds a random element to background damage. y/n: ").strip()
    if ans10 == "y":
        randomness = True
    else: 
        randomness = False
        print("Okay, randomness will be replaced by a mean value.")

    ans11 = input("*UPDATE* How's the weather? ")
    while ans11.upper() not in WEATHER_LIST:
        print("That is an invalid weather. Below are the available weather:")
        for w in WEATHER_LIST: print(w)
        ans11 = input("\nNow choose again:")
    weather = ans11.upper()

    # assign atkr and dfdr
    atkr = pokemon(atkr_species, atkrIVs, CPM(atkrlvl, CPMultiplier), 
        atkr_fmove, atkr_cmove, poketype="player")
    if battle_type == "raid": dfdr = pokemon(dfdr_species, 
        [-1,-1,-1], 0, dfdr_fmove, dfdr_cmove, poketype="raid_boss")
    if battle_type == "gym":  dfdr = pokemon(dfdr_species, 
        dfdrIVs, CPM(dfdrlvl, CPMultiplier), 
        dfdr_fmove, dfdr_cmove, poketype="gym_defender")

    print("\nWe're finally done. Time to start the battle...")
    atkr_fDmg = damage(atkr, dfdr, atkr.fmove, typeadvantages, weather)
    atkr_cDmg = damage(atkr, dfdr, atkr.cmove, typeadvantages, weather)
    dfdr_fDmg = damage(dfdr, atkr, dfdr.fmove, typeadvantages, weather)
    dfdr_cDmg = damage(dfdr, atkr, dfdr.cmove, typeadvantages, weather)
    print("For the record, the attacks are:")
    print("       pkmn                   move    dws   duration  energydel  damage STAB*WAB*typadv")
    print("%11s fmove:%16s   %4d       %4d       %4d    %4d       %5g" % (
        atkr.name, atkr.fmove.name, atkr.fmove.dws, 
        atkr.fmove.duration, atkr.fmove.energydelta, atkr_fDmg, 
        damage_multiplier(atkr, dfdr, atkr.fmove, typeadvantages, weather)))
    print("%11s cmove:%16s   %4d       %4d       %4d    %4d       %5g" % (
        atkr.name, atkr.cmove.name, atkr.cmove.dws, 
        atkr.cmove.duration, -atkr.cmove.energydelta, atkr_cDmg, 
        damage_multiplier(atkr, dfdr, atkr.cmove, typeadvantages, weather)))
    print("%11s fmove:%16s   %4d       %4d       %4d    %4d       %5g" % (
        dfdr.name, dfdr.fmove.name, dfdr.fmove.dws, 
        dfdr.fmove.duration, dfdr.fmove.energydelta, dfdr_fDmg, 
        damage_multiplier(dfdr, atkr, dfdr.fmove, typeadvantages, weather)))
    print("%11s cmove:%16s   %4d       %4d       %4d    %4d       %5g" % (
        dfdr.name, dfdr.cmove.name, dfdr.cmove.dws, 
        dfdr.cmove.duration, dfdr.cmove.energydelta, dfdr_cDmg, 
        damage_multiplier(dfdr, atkr, dfdr.cmove, typeadvantages, weather)))
    print()
    if showlog:
        p1name_len = len(atkr.name)
        p1space = 12 - len(atkr.name)
        print(" "*66 + atkr.name + " "*p1space + " "*3 + dfdr.name)
        print(" "*66 + "HP  | energy" + " "*3 + "HP  | energy      t")
    if battle_type == "gym":
        starting_t_ms = TIMELIMIT_GYM_MS
        new_battle_bool = True
        winner, atkr_postbattle, dfdr_postbattle, length_ms, tline = \
            raid_1v1_battle(atkr, dfdr, speciesdata, typeadvantages, battle_type,
                new_battle_bool, dodgeCMovesIfFree, randomness, 0, weather, timeline(), starting_t_ms)
        if atkr_postbattle.HP <=0 and dfdr_postbattle.HP<=0:
            print("It was a tie! Who knows what happens now.")
        if atkr_postbattle.HP <=0:
            print("%s won!" % dfdr_postbattle.name)
        elif dfdr_postbattle.HP <=0:
            print("%s won!" % atkr_postbattle.name)

    if battle_type == "raid":
        atkrs = [pokemon(atkr_species, atkrIVs, CPM(atkrlvl, CPMultiplier), 
        atkr_fmove, atkr_cmove, poketype="player") for n in range(6)]
        raidwinner, atkrs, dfdr, length_ms, tline = \
            raid_singleteam_battle(atkrs, dfdr, speciesdata, typeadvantages, nOtherPlayers,
                dodgeCMovesIfFree, randomness, weather)
        if dfdr.HP<=0:
            print("The attacking team won!")
        else:
            print("The raid boss won!")
        # did not bother to implement tie for this.

    lengthsecs = length_ms/1000
    print("Ending Stats:")
    if battle_type=="raid":
        for atkr in atkrs: atkr.printstatus()
    else:
        atkr.printstatus()
        print("DPS: %.2f    EPS gain: %.2f" % (
            (dfdr_postbattle.maxHP-dfdr_postbattle.HP)/lengthsecs, 
            atkr_postbattle.total_energy_gained/lengthsecs))
    
    print()
    dfdr.printstatus()
    # print("%s: %d/%d HP" % (
    #     dfdr_postbattle.name, dfdr_postbattle.HP, dfdr_postbattle.maxHP))
    # print(" "*len(dfdr_postbattle.name) + "  %d/%d Energy" % (
    #     dfdr_postbattle.energy, dfdr_postbattle.maxenergy))
    # # print("DPS: %.2f    EPS gain: %.2f" % (
    # #     (atkr_postbattle.maxHP-atkr_postbattle.HP)/lengthsecs, dfdr_postbattle.total_energy_gained/lengthsecs))
    print("time: %.2f seconds" % lengthsecs)
    # import ips; ips.ips()
