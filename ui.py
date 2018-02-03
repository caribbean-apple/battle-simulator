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
