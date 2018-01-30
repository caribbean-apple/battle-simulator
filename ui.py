graphical = False
showlog = True

class graphicallog:
    def __init__(self):
        self.l = []
        self.capacity = 8

    def prnt(self):
        print()
        if len(self.l) < self.capacity:
            print("\n"*(self.capacity - len(self.l)))
        for msg in self.l:
            print(msg)

    def add(self, msg):
        if len(self.l) < self.capacity:
            self.l += [msg]
        else:
            self.l = self.l[1:] + [msg]





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
    #dfdr may go past 100E, then just show it as full with 100:
    dfdrenergy = min(dfdr.energy, 100)
    # ^this does NOT actually change dfdr's energy, just the visuals.

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



def update_logs(wd, t, eventtype, pkmn_usedAtk=None, pkmn_hurt=None,
    damage=None, hurtEnergyGain=None, move_hurt_by=None):
    
    msg2 = ""
    
    if eventtype == "use_fmove":
        # takes in pkmn_usedAtk
        msg = ("%.2f: %s used %s!" % (
            (wd.timelimit_ms - t)/1000, pkmn_usedAtk.name, pkmn_usedAtk.fmove.name))
        msg = "%-45s +  %d HP / +%3d E" % (msg, 0, pkmn_usedAtk.fmove.energydelta)
        
    elif eventtype == "use_cmove":
        # takes in pkmn_usedAtk
        msg = ("%.2f: %s used %s!" % (
            (wd.timelimit_ms - t)/1000, pkmn_usedAtk.name, pkmn_usedAtk.cmove.name))
        msg = "%-45s +  %d HP / %3d E" % (msg, 0, pkmn_usedAtk.cmove.energydelta)

    elif eventtype == "hurt":
        # takes in pkmn_usedAtk, pkmn_hurt, hurtEnergyGain, move_hurt_by
        msg = "%.2f: %s was hurt by %s!" % (
            (wd.timelimit_ms - t)/1000, pkmn_hurt.name, move_hurt_by.name)

        msg = "%-45s -%3d HP / +%3d E" % (msg, damage, hurtEnergyGain)
        timelen = len("%.2f" % ((wd.timelimit_ms - t)/1000)) + 2
        if move_hurt_by.mtype == 'f':
            msg2 = "\n" + " "*timelen + "%s gained %d energy." % (
                pkmn_usedAtk.name, move_hurt_by.energydelta)
        elif move_hurt_by.mtype == 'c':
            msg2 = "\n" + " "*timelen + "%s used up %d energy." % (
                pkmn_usedAtk.name, move_hurt_by.energydelta)

    elif eventtype == "dodge":
        # takes in pkmn_usedAtk, pkmn_hurt
        msg = "%.2f: %s dodged %s!" % (
            (wd.timelimit_ms - t)/1000, pkmn_hurt.name, pkmn_usedAtk.cmove.name)

    elif eventtype == "background_dmg":
        # takes in pkmn_hurt
        msg = "%.2f: %s took background dmg!" % (
            (timelimit_ms - t)/1000, pkmn_hurt.name)
        msg = "%-45s -%3d HP / +%3d E" % (msg, damage, hurtEnergyGain)

    atkrHP, atkrEnergy = str(int(wd.atkr.HP)), str(int(wd.atkr.energy))
    dfdrHP, dfdrEnergy = str(int(wd.dfdr.HP)), str(int(wd.dfdr.energy))

    msg += ( " " * (66-len(msg)) 
        + atkrHP + " "*(4 - len(atkrHP))
        + "| " + atkrEnergy + " "*(6-len(atkrEnergy)) 
        + " "*3 + dfdrHP + " "*(4 - len(dfdrHP))
        + "| %-3d"%wd.dfdr.energy + " "*4 + "%6d" % t )

    msg = msg + msg2

    if showlog:
        print(msg)
        return
    
    if graphical: 
        wd.glog.add(msg)
