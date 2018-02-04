from battlesimlib import *
from ui import *
import copy



def debug():

    debug_world = world()
    debug_world.importAllGM()
    
    debug_world.starting_t_ms = TIMELIMIT_GYM_MS
    debug_world.new_battle_bool = True

    # assign (single) atkr and dfdr
    atkr = pokemon(debug_world.speciesdata[getPokedexNumber('golem', debug_world.speciesdata)], [15,15,15],
                    CPM(40, debug_world.CPMultiplier), debug_world.fmovedata['mud slap'],
                    debug_world.cmovedata['earthquake'], poketype="player")
##    atkr2 = pokemon(debug_world.speciesdata[getPokedexNumber('dragonite', debug_world.speciesdata)], [15,15,15],
##                    CPM(40, debug_world.CPMultiplier), debug_world.fmovedata['dragon tail'],
##                    debug_world.cmovedata['dragon claw'], poketype="player")
    
    dfdr = pokemon(debug_world.speciesdata[getPokedexNumber('jolteon', debug_world.speciesdata)], [15,15,15],
                    CPM(40, debug_world.CPMultiplier), debug_world.fmovedata['thunder shock'], 
                    debug_world.cmovedata['thunder'], poketype="raid_boss", raid_tier=3)
    
    debug_world.atkr_parties.append(party([copy.deepcopy(atkr) for _ in range(6)]))
    
##    debug_world.atkr_parties.append(party([copy.deepcopy(atkr2) for _ in range(6)]))
    
    debug_world.dfdr_party.add(dfdr)
 
    debug_world.battle_type = 'raid'
    debug_world.raid_tier = 3
    debug_world.dodgeCMovesIfFree = False
    debug_world.randomness = True
    debug_world.weather = 'EXTREME'

    for n in range(1):
        print("simulation #", n+1)
        debug_world.reset_stats()
        winner = battle(debug_world)
        length_ms = debug_world.battle_lengths[0]
        
    

    if 0:
        for msg in generate_glog(debug_world):
            print(msg)
        print()
    
    if winner == -1:
        print("It was a tie! Who knows what happens now.")
    elif winner == 1:
        print("Attacker won!")
    elif winner == 2:
        print("Defender won!")
    lengthsecs = length_ms/1000
    print("Ending Stats:\n")
    
    print("time: %.2f seconds" % lengthsecs)
    
    debug_world.dfdr_party.active_pkm.printstatus()
    print()

    for p in debug_world.atkr_parties:
        print("Team",p,"TDO:",p.tdo())
        for atkr in p:
            atkr.printstatus()
            print("DPS: %.2f    EPS gain: %.2f" % (atkr.total_damage_output/lengthsecs,
                                                   atkr.total_energy_gained/lengthsecs)) 
    
    




