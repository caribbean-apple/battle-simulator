'''
TODO: Basically update everything that takes the event log since multi-attacker
        mode has just been implemented.

'''

def invalidInputError(invalidstr):
    raise Exception("\nTHAT'S AN INVALID INPUT.\n" +
        "Did you even NOTICE that you had entered '%s'???!??!" % 
        invalidstr)



def printgraphicalstart():
    print("\n"*60)
    print("""
       _   _   _   _   _   _   _   _   _   _  
      / \ / \ / \ / \ / \ / \ / \ / \ / \ / \ 
     ( S ( I ( M ( U ( L ( A ( T ( I ( N ( G )
      \_/ \_/ \_/ \_/ \_/ \_/ \_/ \_/ \_/ \_/ 
              _   _   _   _   _   _           
             / \ / \ / \ / \ / \ / \          
            ( B ( A ( T ( T ( L ( E )         
             \_/ \_/ \_/ \_/ \_/ \_/        




            """)
    time.sleep(2)
    print("\n"*60)
    print(
            """



                     _____
                    |__  /
                     /_ < 
                   ___/ / 
                  /____/        




            """)
    time.sleep(1)
    print("\n"*60)
    print(
            """



                     ___ 
                    |__ \\
                    __/ /
                   / __/ 
                  /____/ 




            """)
    time.sleep(1)
    print("\n"*60)
    print(
            """



                     ___
                    <  /
                    / / 
                   / /  
                  /_/         




            """)
    time.sleep(1)
    print("\n"*60)
    print(
            """



               __________  __
              / ____/ __ \/ /
             / / __/ / / / / 
            / /_/ / /_/ /_/  
            \____/\____(_)   
                                                   



            """)
    time.sleep(1)

def printgraphicalstatus(atkr, dfdr):
    windowWidth = 60
    windowHeight = 15
    frameWidth = 2
    barCount = 20
    statusBarWidth = barCount + frameWidth

    atkrname = atkr.name.upper() + " (attacker)"
    dfdr_name = dfdr.name.upper() + " (defender)"

    currentHPBarCount1 = int(math.ceil(barCount*(atkr.HP/atkr.maxHP)))
    currentEBarCount1 = int(math.ceil(barCount*(atkr.energy/atkr.maxenergy)))

    currentHPBarCount2 = int(math.ceil(barCount*(dfdr.HP/dfdr.maxHP)))
    currentEBarCount2 = int(math.ceil(barCount*(dfdrenergy/ATKR_MAX_ENERGY)))

    print("\n"*8)
    print(" "*(windowWidth - len(dfdr_name)) + dfdr_name)
    print(" "*(windowWidth - statusBarWidth - 5) + ("%3dHP|" % dfdr.HP) + 
        "="*currentHPBarCount2 + " "*(barCount - currentHPBarCount2) + "|")
    print(" "*(windowWidth - statusBarWidth - 5) + ("%3dE |" % dfdrenergy) + 
        "="*currentEBarCount2 + " "*(barCount - currentEBarCount2) + "|")

    print("\n"*(windowHeight -6), end="")

    print(atkrname)
    print("|" + "="*currentHPBarCount1 + 
        " "*(barCount - currentHPBarCount1) + "|" + ("%3dHP" % atkr.HP))
    print("|" + "="*currentEBarCount1 + 
        " "*(barCount - currentEBarCount1) + "|" + ("%3dE" % atkr.energy))


def generate_glog(wd):
    glog = []
    for e in wd.elog:
        m = update_logs(wd, e)
        if m:
            glog.append(m)
    return glog


def update_logs(wd, e):
    
    msg2 = ""
    
    if "announce" in e.name:
        # takes in pkmn_usedAtk
        msg = ("%.2f: %s used %s!" % (
            (wd.timelimit_ms - e.t)/1000, e.pkmn_usedAtk.name, e.move_hurt_by.name))


    elif "Hurt" in e.name:
        # takes in pkmn_usedAtk, pkmn_hurt, hurtEnergyGain, move_hurt_by
        msg = "%.2f: %s was hurt by %s!" % (
            (wd.timelimit_ms - e.t)/1000, e.pkmn_hurt.name, e.move_hurt_by.name)

        msg = "%-45s -%3d HP / +%3d E" % (msg, e.dmg, e.dmg//2)
        timelen = len("%.2f" % ((wd.timelimit_ms - e.t)/1000)) + 2
        if e.move_hurt_by.mtype == 'f':
            msg2 = "\n" + " "*timelen + "%s gained %d energy." % (
                e.pkmn_usedAtk.name, e.move_hurt_by.energydelta)
        elif e.move_hurt_by.mtype == 'c':
            msg2 = "\n" + " "*timelen + "%s used up %d energy." % (
                e.pkmn_usedAtk.name, -e.move_hurt_by.energydelta)

    elif e.name == "dodge":
        # takes in pkmn_usedAtk, pkmn_hurt
        msg = "%.2f: %s dodged %s!" % (
            (wd.timelimit_ms - e.t)/1000, e.pkmn_hurt.name, e.move_hurt_by.name)

    elif e.name == "backgroundDmg":
        # takes in pkmn_hurt
        msg = "%.2f: %s took background dmg!" % (
            (timelimit_ms - e.t)/1000, e.pkmn_hurt.name)
        msg = "%-45s -%3d HP / +%3d E" % (msg, e.dmg, e.dmg//2)

    elif "Enter" in e.name:
        msg = "%s entered the field" % e.pkmn_usedAtk.name

    else:
        return ""

    if e.pkmn_usedAtk.poketype == "player":
        atkr, dfdr = e.pkmn_usedAtk, e.pkmn_hurt
    else:
        atkr, dfdr = e.pkmn_hurt, e.pkmn_usedAtk

    if not atkr:
        atkr = dfdr
    if not dfdr:
        dfdr = atkr
        
    atkrHP, atkrEnergy = str(atkr.HP), str(atkr.energy)
    dfdrHP, dfdrEnergy = str(dfdr.HP), str(dfdr.energy)

    msg += ( " " * (66-len(msg)) 
        + atkrHP + " "*(4 - len(atkrHP))
        + "| " + atkrEnergy + " "*(6-len(atkrEnergy)) 
        + " "*3 + dfdrHP + " "*(4 - len(dfdrHP))
        + "| %-3d"%dfdr.energy + " "*4 + "%6d" % e.t )

    msg = msg + msg2

    return msg




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
