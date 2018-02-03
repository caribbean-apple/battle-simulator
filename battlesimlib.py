from __future__ import print_function, division
import math
import bisect
import sys
import time
try: input = raw_input
except NameError: pass
import random

from pokelibrary import *
import csvimport as cv
import winsound

"""
TO DO:
-I removed cmove announcements from EnergyDelta event. They should be added to announce event.
This only matters for cmoves with large charge time. The announce events should only be added 
if log options (graphical? showlog?) are on.

-dodge_success_probability and dodgeCMovesIfFree should be party- or even invidual pokemon-dependent?

-TDO for different teams don't add up to raid boss's HP.

-Count lag time in youtube videos (how many fmoves per time?). Add an attacker lag with this.
"""

# NOTE: currently, there is a (somewhat arbitrary) dodge_success_probability,
# defined in battle(). 
#


# the following 2 variables are now only be taken as inputs to be safe:
# dodgeCMovesIfFree = True # this variable will be set False if dodge_success_probability < 0.4
# randomness = True           # Niantic uses randomness. But maybe you won't.
                            # if False, defenders use cmove every other
                            # opportunity, and always wait exactly 2000ms
                            # between attacks

DODGEWINDOW_LENGTH_MS = 700         # how much time you have to dodge after yellow flash (tested)

DODGE_COOLDOWN_MS = 500             # how long after you dodge can you attack again

dodgeDamageReductionPercent = 0.75  # dodged atks do 25% dmg. This variable is from GAME_MASTER.

DODGE_REACTIONTIME_MS = 50          # this is how long in ms that a person takes to react
                                    # to the yellow flash. 
                                    # they will only dodge, say, 50ms
                                    # after the beginning of the yellow flash.
                                    # note that it's not a reaction, because if you are used to
                                    # the enemy move's timing then you can just time it.
                                    
CMOVE_REACTIONTIME_MS = 100         # how long it takes you to react after seeing "Snorlax 
                                    # used Hyper Beam!" or similar message.
                                    
TAP_TIMING_MS = 100                 # This will determine how much of your charge move you can charge during
                                    # the previous fast move. Smaller TAP_TIMING_MS means more charging.
                                    
TAP_PERIOD_MS = 200                 # This was my tap period, for a typical gym battle. It is a "tapping decently fast
                                    # but not as fast as possible" speed. TAP_PERIOD_MS/2 is then the typical time in between
                                    # successive taps, if there is no buffering.
                                    
CMOVE_OVERKILL_CHOICE_PERCENT_THRESHHOLD = 0.30 # if this=0.30, then the attacker will choose to
                                                # use fmove spam rather than a cmove if 30% or more of 
                                                # the cmove's damage would be overkill.
                                                # currently NOT IMPLEMENTED.
                                    
STAB_MULTIPLIER = 1.2               # Same Type Attack Bonus damage multiplier

WAB_MULTIPLIER = 1.2                # Weather boosted Attack Bonus damage multiplier

ATKR_SUBSTITUTE_DELAY_MS_IDEAL = 900    # when switching out atkr or after death, how long until atkrFree?
                                        # found by a combination of frame-counting and game master guesses.
                                        
ATKR_SUBSTITUTE_LAG = 577               # how much lag follows the sub? found by frame-counting.
ATKR_SUBSTITUTE_DELAY_MS = ATKR_SUBSTITUTE_DELAY_MS_IDEAL + ATKR_SUBSTITUTE_LAG

DODGE_FAINT_BUG = True              # the damn dodge glitch. Just celebrated its anniversary
                                    # If set True, to avoid the bug, I will not dodge if I'm within the KO range

MAX_POKEMON_PER_PARTY = 6


# subjective parameter used to determine how much damage other players do
# although 11 is pretty accurate in my experience in NYC and in Munich
nToBarelyBeatLugia = 11
lugia_HP = raidboss_HP[5]
lugia_base_DEF_adj = 323 + raidboss_IVs[1]
lugia_timelimit_s = TIMELIMIT_LEGENDARYRAID_MS//1000
vs_lugia_DPS_per_other_player = (lugia_HP/lugia_timelimit_s)/nToBarelyBeatLugia





'''
    CLASSES
'''

class event:
    # events sit on the timeline and carry instructions / information
    # about what they should change or do.
    #
    # TYPE OF EVENT
    # pkmnEnter: A pokemon (atkr or dfdr) has joined the battle! It can be atkr or dfdr
    # atkrFree: Attacking pokemon is free to perform another action right now.
    #           If it's an fmove the atkr gains energy at this time
    #           If it's a  cmove the atks might gain energy now, depending on charge time
    #           takes (name, t)
    # dfdrFree: Because the defender chooses each move at the beginning of the previous move,
    #           this event sets up the following move, not the one which is about to begin.
    #           So it puts damage & energy diff events on the timeline for a move which STARTS at 
    #           time = t + duration + rand(1500,2500). This is different from atkrFree, which chooses
    #           a move that starts at time = t.
    #           takes (name, t, current_move)
    # pkmnHurt: A pokemon (atkr or dfdr) takes damage (and gains energy). Always happens
    #           separately from atkr/dfdrFree bc of the DamageWindowStart delay.
    #           takes (name, t, dmg, move_hurt_by)
    # pkmnEnergyDelta: A pokemon (atkr or dfdr) gains or loses energy. It may be negative.
    # announce: Announce a message to the log at a particular time. This is only used for 
    #           attack announcements that are not made at the same time they were decided.
    #           takes (name, t)
    # dodge:    Attacker performs a dodge.
    # dodge_failed: Not every dodge will be sucessful.
    # backgroundDmg: The dfdr takes background dmg to emulate a team of attackers.
    #           takes (bgd_dmg_time, background_dmg_per_1000ms)

    def __init__(self, name, t, dmg=None, energy_delta=None, msg=None, move_hurt_by=None, 
        current_move=None, pkmn_usedAtk=None, pkmn_hurt=None):
        # the name(type) of the event (dfdrHurt, atkrFree, etc) and the time it happens (ms).
        self.name = name
        self.t = t
        
        # only for pkmnHurt event:
        self.move_hurt_by = move_hurt_by
        self.dmg = dmg
        self.dodged = False # If True, when actually deduct the damage in event handling, damage gets reduced
        # only for pEnergyDelta event:
        self.energy_delta = energy_delta # this may be negative
        # only for dfdrFree:
        # `current_move is the move which starts at the event time t.
        self.current_move = current_move
        # only for updateLogs event
        self.pkmn_usedAtk = pkmn_usedAtk
        self.pkmn_hurt = pkmn_hurt

    def __lt__(self, other): return self.t < other.t
    def __le__(self, other): return self.t <= other.t
    def __gt__(self, other): return self.t > other.t
    def __ge__(self, other): return self.t >= other.t
    def __eq__(self, other): return self.t == other.t


class timeline:
    # A ordered queue to manage events
    
    def __init__(self):
        self.lst = []

    def __iter__(self):
        return iter(self.lst)

    def add(self, e):
        # add the event at the proper (sorted) spot.
        bisect.insort_left(self.lst, e)

    def pop(self):
        # return the first (earliest) event and remove it from the queue
        return self.lst.pop(0)

    def print(self):
        print("==Timeline== ", end="")
        for e in self.lst:
            print(str(e.t) + ":" + e.name, end=", ")
        print()


class party:
    # A collection of at most MAX_POKEMON_PER_PARTY Pokemon.

    def __init__(self, pkm_list=[]):
        self.lst = []
        self.active_pkm = None
        for pkm in pkm_list:
            self.add(pkm)

    def __iter__(self):
        # So you don't have to write "for pkm in some_party.lst:"
        # Just "for pkm in some_party: " will do
        return iter(self.lst)

    def add(self, pkm):
        # Add pokemon to the party
        if len(self.lst) < MAX_POKEMON_PER_PARTY:
            self.lst.append(pkm)
            pkm.parent_party = self
            if not self.active_pkm:
                self.active_pkm = pkm
        else:
            raise Exception("Failed to add new Pokemon: Exceeding max party size")

    def next_pkmn_up(self):
        # When active Pokemon (active_pkm) faints, this function is called
        # It puts the first alive Pokemon on the field

        for pkm in self:
            if pkm.HP > 0:
                self.active_pkm = pkm
                return
        raise StopIteration("Party exhausted")

    def alive(self):
        # If any of the Pokemon in this party is still alive, returns True. 
        # Otherwise returns False
        for pkm in self:
            if pkm.HP > 0:
                return True
        return False

    def tdo(self):
        return sum(pkm.total_damage_output for pkm in self)



class world:
    # This is used for holding all settings (speciesdata, movedata, user settings),
    # so that the [...] part of player_AI_choose(...) won't be miserably long

    # Part 1: GM file settings - Initialize all these by calling method "importAllGM"
    fmovedata = None
    cmovedata = None
    speciesdata = None
    CPMultiplier = None
    typeadvantages = None

    # Part 2: Pokemon settings  
    atkr_parties = []       # For multi-player mode
    dodge_success_probability = 0
    dodgeCMovesIfFree = False
    
    dfdr_party = party()    # Simulate a gym of six defenders
    randomness = False
    opportunityNum = 0

    # Part 3: Battle parameters variables
    battle_type = None
    raid_tier = 0
    new_battle_bool = True
    nOtherPlayers = 0
    timelimit_ms = 0
    tline = timeline()
    starting_t_ms = -1
    weather = 'EXTREME'
    battle_lengths = []
    elog = []

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def importGM(self, GMFilePath):
        self.fmovedata, self.cmovedata, self.speciesdata, self.CPMultiplier, self.typeadvantages = importGM(GMFilePath)

    def importAllGM(self):
        self.fmovedata, self.cmovedata, self.speciesdata, self.CPMultiplier, self.typeadvantages = importAllGM()

    def reset_stats(self):
        for p in self.atkr_parties:
            for pkm in p:
                pkm.reset_stats()
        for pkm in self.dfdr_party:
            pkm.reset_stats()
        self.elog = []
        self.tline = timeline()
        self.battle_lengths = []

'''
    FUNCTIONS
'''


def damage(pkmn_usedAtk, pkmn_hurt, move, typeadvantages, weather='EXTREME'):
    # calculate damage.
    STAB = STAB_MULTIPLIER if move.dtype in [pkmn_usedAtk.type1, pkmn_usedAtk.type2] else 1
    WAB = WAB_MULTIPLIER if move.dtype in WEATHER_BOOSTED_TYPES[weather] else 1
    typadv1 = typeadvantages[move.dtype][pkmn_hurt.type1]
    typadv2 = 1 if pkmn_hurt.type2=="none" else typeadvantages[move.dtype][pkmn_hurt.type2]    
    mult = STAB * WAB * typadv1 * typadv2
    
    dmg = math.ceil(0.5*pkmn_usedAtk.ATK*move.power*mult/pkmn_hurt.DEF)
    return dmg

def atkr_use_move(pkm, pkm_hurt, move, wd, t):

    dmg = damage(pkm, pkm_hurt, move, wd.typeadvantages, wd.weather)
    wd.tline.add(event("announce", t, pkmn_usedAtk=pkm, move_hurt_by=move))
    wd.tline.add(event("atkrEnergyDelta", t + move.dws, pkmn_usedAtk=pkm, energy_delta=move.energydelta))
    wd.tline.add(event("dfdrHurt", t + move.dws, pkmn_usedAtk=pkm, pkmn_hurt=pkm_hurt, dmg=dmg, move_hurt_by=move))
    wd.tline.add(event("atkrFree", t + move.duration, pkmn_usedAtk=pkm))

def dfdr_use_move(pkm, move, wd, t):
       
    wd.tline.add(event("announce", t, pkmn_usedAtk=pkm, move_hurt_by=move))
    wd.tline.add(event("dfdrEnergyDelta", t + move.dws, pkmn_usedAtk=pkm, energy_delta=move.energydelta))
    
    # Need to make damage to EVERY attacker on the field (multi-player mode)
    for p in wd.atkr_parties:
        dmg = damage(pkm, p.active_pkm, move, wd.typeadvantages, wd.weather)
        wd.tline.add(event("atkrHurt", t + move.dws, pkmn_usedAtk=pkm,
                           pkmn_hurt=p.active_pkm, dmg=dmg, move_hurt_by=move))
    
    # defender makes decision at the beginning of the previous move
    wd.tline.add(event("dfdrFree", t, current_move = move)) 



def player_AI_choose(wd, atkr, t):
    # This function is the strategy of the attacker.
    # It directly manipulates the timeline object by inserting events.
    # for now, atkr will always be the player's pokemon.
    
    dfdr = wd.dfdr_party.active_pkm
    tline = wd.tline

    atkr_fDmg = damage(atkr, dfdr, atkr.fmove, wd.typeadvantages, wd.weather)
    atkr_cDmg = damage(atkr, dfdr, atkr.cmove, wd.typeadvantages, wd.weather)
    dfdr_cDmg = damage(dfdr, atkr, dfdr.cmove, wd.typeadvantages, wd.weather)

    if wd.dodgeCMovesIfFree and (not DODGE_FAINT_BUG or wd.nOtherPlayers ==0 or atkr.HP > dfdr_cDmg):
        atkrHurt_cmove_events = [x for x in tline.lst if (x.name=='atkrHurt' and x.dmg==dfdr_cDmg)]
        if len(atkrHurt_cmove_events) > 0:
            # At this point, the enemy has announced a cmove.
            atkrHurt_cmove_event = atkrHurt_cmove_events[0]
            tDfdrCMoveStart = atkrHurt_cmove_event.t - dfdr.cmove.dws
            tDodgeWindowStart = atkrHurt_cmove_event.t - DODGEWINDOW_LENGTH_MS + DODGE_REACTIONTIME_MS 
            time_left_before_hurt = atkrHurt_cmove_event.t - t

            # IF I can finish him off before being hurt, do so.
            # can I finish him with just fmoves? First, can I even use one fmove?
            if atkr.fmove.dws < time_left_before_hurt:
                # yes, I can. How many?
                nFmovesAtkrCanFit = 1 + (time_left_before_hurt - atkr.fmove.dws)//atkr.fmove.duration
                atkr_dmg_done_before_hurt = nFmovesAtkrCanFit * atkr_fDmg
                if atkr_dmg_done_before_hurt >= dfdr.HP: 
                    # ## OUTCOME 1: fmove spam until dfdr dies
                    atkr_use_move(atkr, dfdr, atkr.fmove, wd, t)         
                    return

                # can I fit in a cmove?
                time_left_if_atkr_cmoves = time_left_before_hurt - atkr.cmove.duration - TAP_TIMING_MS
                if time_left_if_atkr_cmoves > 0 and atkr.energy + atkr.cmove.energydelta >= 0:
                    # yes, I can.
                    ## OUTCOME 2: cmove, then fmove spam (to be decided in the next function call). 
                    # *UPDATE* after battle UI rework, you can tap the button and use cmove right away
                    # add the cmove to tline
                    atkr_use_move(atkr, dfdr, atkr.cmove, wd, t)
                    return
            
            # at this point, if I could have finished him off before hurt, the function has already returned.
            if tDodgeWindowStart <= t < atkrHurt_cmove_event.t and not atkrHurt_cmove_event.dodged:
                
                ## OUTCOME 3: dodge (even if you have already dodged. dodging takes 500ms and the window is 700ms)
                # Set the "dodged" flag to True, with a certain probability:
                if (not wd.randomness) or random.uniform(0,1) <= wd.dodge_success_probability:
                    atkrHurt_cmove_event.dodged = True
                    wd.elog.append(event("dodge", t, pkmn_usedAtk=atkr))
                else: 
                    wd.elog.append(event("dodge_failed", t, pkmn_usedAtk=atkr))

                # attacker cannot move until dodge is over.
                # dodge 1 or 2 times, with 66% chance that it's 2 times.
                tFree = t + DODGE_COOLDOWN_MS * random.choice([1, 2, 2])
                tline.add(event("atkrFree", tFree, pkmn_usedAtk=atkr))
                return
            

    # at this point, either dodgeCMovesIfFree == False or I should atk as usual.
    # Other outcomes have already returned.
    if atkr.energy + atkr.cmove.energydelta < 0:
        ## OUTCOME 6/7: use fmove
        atkr_use_move(atkr, dfdr, atkr.fmove, wd, t) 
        return

    # at this point, atkr has enough energy to use a cmove. Can I finish dfdr off faster
    # with fmove spam than with cmove?
    nFmovesAtkrCanFit = 1 + (atkr.cmove.dws + TAP_TIMING_MS - atkr.fmove.dws)//atkr.fmove.duration
    atkr_dmg_done_before_cmovedws = nFmovesAtkrCanFit * atkr_fDmg
    if atkr_dmg_done_before_cmovedws >= dfdr.HP: 
        # ## OUTCOME 8: fmove spam until dfdr dies
        atkr_use_move(atkr, dfdr, atkr.fmove, wd, t)      
        return
    else:
        ## OUTCOME 9: use cmove
        atkr_use_move(atkr, dfdr, atkr.cmove, wd, t)
        return




def gymdfdr_AI_choose(wd, t, current_move):
    
    # this function is called when it is the defender's turn to start an atk,
    # it chooses what to use NEXT (so not at time=t, but at time=t+duration+delay)
    # based on the energy it WILL have AFTER the current move.

    dfdr = wd.dfdr_party.active_pkm
    tline = wd.tline
 
    projected_dfdr_energy = dfdr.energy + current_move.energydelta
    # decide fmove or move to use next.
    next_move = dfdr.fmove
    if projected_dfdr_energy + dfdr.cmove.energydelta >= 0:
        # if you have enough energy, use a cmove 50% of time:
        if wd.randomness:
            if random.random()<0.5:
                next_move = dfdr.cmove
        else:
            if wd.opportunityNum == 1:
                next_move = dfdr.cmove
            wd.opportunityNum = 1 - wd.opportunityNum # switches 0 to 1 and vice versa,
                                                # causing cmove to be used every other opportunity.
    # choose when to begin the next move
    t_next_move = t + current_move.duration + random.randint(1500,2500) if wd.randomness else 2000

    dfdr_use_move(dfdr, next_move, wd, t_next_move)



def otherplayers_DPS_profile(t):
    # this function gives the percent of the average DPS that is done as a function of time.
    # So if the average dps is (say) 50 throughout the battle, 
    # then the instantaneous DPS done at (say) t=120s is 50*otherplayers_DPS_profile(120).

    # You might think this function should be normalized so that the average value is 1.
    # However, this would lead to superficially low damage being dealt for short battles.
    # To adjust for this, scale the function so that its integral up to 250s is 1.
    # This is equivalent to scaling it by 1.112. Terminology stolen from cosmology.

    scalefactor = 1

    time_pts = [0,     25,   180,   250,   300]
    dps_pts  = [0, 1.2158, 1.094, 0.973, 0.365]
    slopes   = [(dps_pts[n]-dps_pts[n-1])/(time_pts[n]-time_pts[n-1]) for n in range(1,len(time_pts))]
    
    # print("integral of otherplayers_DPS_profile with scalefactor = %f:" % scalefactor)
    # totaldmg = sum([(time_pts[n]-time_pts[n-1])*(dps_pts[n]+dps_pts[n-1])/2 for n in range(1,len(time_pts))])
    # avgdps = totaldmg / 300
    # print("totaldmg",totaldmg)
    # print("avgdps",avgdps)
    # import ips; ips.ips()

    if t < 0:
        return 0

    elif 0 <= t < time_pts[1]:
        return scalefactor * (dps_pts[0] + slopes[0] * (t - time_pts[0]))

    elif time_pts[1] <= t < time_pts[2]:
        return scalefactor * (dps_pts[1] + slopes[1] * (t - time_pts[1]))

    elif time_pts[2] <= t < time_pts[3]:
        return scalefactor * (dps_pts[2] + slopes[2] * (t - time_pts[2]))

    elif time_pts[3] <= t < time_pts[4]:
        return scalefactor * (dps_pts[3] + slopes[3] * (t - time_pts[3]))

    else: return 0




def initial_dfdr_events(wd):
    # add the starting times of atkr(s) and dfdr.

    dfdr = wd.dfdr_party.active_pkm
    tline = wd.tline
    tline.add(event("dfdrEnter", 0, pkmn_usedAtk=dfdr))
    for a_party in wd.atkr_parties:
        atkr = a_party.active_pkm
        dfdr_fDmg = damage(dfdr, atkr, dfdr.fmove, wd.typeadvantages, wd.weather)
        tline.add(event("atkrHurt", 1000 + dfdr.fmove.dws, pkmn_usedAtk=dfdr, pkmn_hurt=atkr,
                        dmg=dfdr_fDmg, move_hurt_by=dfdr.fmove))
        tline.add(event("atkrHurt", 2000 + dfdr.fmove.dws, pkmn_usedAtk=dfdr, pkmn_hurt=atkr,
                        dmg=dfdr_fDmg, move_hurt_by=dfdr.fmove))
    tline.add(event("dfdrEnergyDelta", 1000 + dfdr.fmove.dws, pkmn_usedAtk=dfdr, energy_delta=dfdr.fmove.energydelta))
    tline.add(event("dfdrFree",        2000, current_move = dfdr.fmove))
    tline.add(event("dfdrEnergyDelta", 2000 + dfdr.fmove.dws, pkmn_usedAtk=dfdr, energy_delta=dfdr.fmove.energydelta))
    dfdr.nonbackground_damage_taken = 0
    


def battle(wd):
    # This function is the core that controls the simulation.
    
    # This function can start a new battle or continue an existing one,
    # depending on whether new_battle_bool = True. 
    # if "new_battle_bool", it will start from after GO! disappears, so dfdr will do the many starting fmoves.
    # in this case one must pass:
    #   -time_remaining_ms as the time left in the battle
    # time_remaining_ms defaults to -1 because it will always be set in a new_battle_bool, based on battle_type.

    dfdr = wd.dfdr_party.active_pkm
    tline = wd.tline

    if wd.new_battle_bool:
        t = 0
        initial_dfdr_events(wd)
        for p in wd.atkr_parties:
            atkr = p.active_pkm
            tline.add(event("atkrEnter", 0, pkmn_usedAtk=atkr))
            tline.add(event("atkrFree", 0, pkmn_usedAtk=atkr))
    else:
        t = wd.starting_t_ms
##        if len(tline.lst)==0 or wd.starting_t_ms==-1:
##            raise Exception("\nFor battles which start in the middle, "
##                + "you must input starting_t_ms and timeline.\n")

        
    if wd.battle_type == "raid":
        wd.timelimit_ms = ( TIMELIMIT_LEGENDARYRAID_MS if wd.raid_tier == 5
            else TIMELIMIT_NORMALRAID_MS )
    elif wd.battle_type == "gym":
        wd.timelimit_ms = TIMELIMIT_GYM_MS

    # define the dodge success probability linearly, based on:
    # move          dws     dodge probability (guessing based on my experience)
    # zap cannon    3000    1.0
    # thunderbolt   1800    0.2
    wd.dodge_success_probability = 0.2 + ((1.0-0.2)/(3000-1800))*(dfdr.cmove.dws - 1800)
    wd.dodge_success_probability = max(min(wd.dodge_success_probability, 1),0)
    wd.dodge_success_probability = 1 # Temp

    # Don't give up. Life is hard.
    
    # opportunityNum is changed from 0 to 1 each time the dfdr could have used a charge move. 
    # if opportinityNum == 1, and randomness is off, then dfdr will use a charge move.
    wd.opportunityNum = 0

    
    # do all the events in order.
    while any([p.alive() for p in wd.atkr_parties]) and wd.dfdr_party.alive() and t < wd.timelimit_ms:
        # handle first event on tline and remove current event from the timeline so it only gets handled once.
        this_event = tline.pop()
        t = this_event.t
        
        # case 1: a pokemon is free to decide on a move
        if "Free" in this_event.name:
            if "atkr" in this_event.name: # atkrFree
                # let AI handle this case (more complex)
                # player_AI_choose will also assign all new events to the timeline.
                player_AI_choose(wd, this_event.pkmn_usedAtk, t)
            else: # dfdrFree
                gymdfdr_AI_choose(wd, t, this_event.current_move)

        # case 2: a pokemon takes damage
        elif "Hurt" in this_event.name:
            # Below are two important formulas
            if this_event.dodged:
                this_event.dmg = max(math.floor(this_event.dmg*(1-dodgeDamageReductionPercent)), 1)
            hurtEnergyGain = math.ceil(this_event.dmg/2)
            
            # inflict the damage to the pkmn which was attacked
            # also give it the corresponding energy gain
            dmg_taker = this_event.pkmn_hurt
            dmg_taker.HP -= this_event.dmg
            dmg_taker.energy = min(dmg_taker.energy + hurtEnergyGain, dmg_taker.maxenergy)
            dmg_taker.total_energy_gained += hurtEnergyGain

            dmg_giver = this_event.pkmn_usedAtk
            dmg_giver.total_damage_output += this_event.dmg

            if "atkr" in this_event.name: # atkrHurt extra handling
                if dmg_taker.HP <= 0:
                    dmg_giver.total_damage_output += this_pkm.HP
            else: # dfdrHurt extra handling
                dmg_taker.nonbackground_damage_taken += this_event.dmg
                if dmg_taker.HP <= 0: 
                    dmg_taker.nonbackground_damage_taken += this_pkm.HP
                    dmg_giver.total_damage_output += this_pkm.HP
                    wd.battle_lengths.append(t)
        
        # case 3: a pokemon gains/loses energy
        elif "EnergyDelta" in this_event.name:
            this_pkm = this_event.pkmn_usedAtk
            this_pkm.energy = min(this_pkm.energy + this_event.energy_delta, this_pkm.maxenergy)

        # case 4: dfdr (raid boss) takes background dmg to emulate a team of atkrs.
        elif this_event.name == "backgroundDmg":
            if randomness:
                this_event.dmg = round(this_event.dmg * random.uniform(0.7, 1.3))
            hurtEnergyGain = math.ceil(this_event.dmg/2)
            # do not add to total_nonbackground_damage_taken because I do not count backgroundDmg.
            dfdr.total_energy_gained += hurtEnergyGain
            this_event.pkmn_hurt = dfdr

        # case 5: a pokemon enters
        elif "Enter" in this_event.name:
            this_event.pkmn_usedAtk.t_enter_ms = t


        # Add this event the log
        wd.elog.append(this_event)

        # for debug
##        print("Post-Processing:", t, this_event.name,
##              this_event.pkmn_usedAtk.name if this_event.pkmn_usedAtk else "",
##              this_event.move_hurt_by.name if this_event.move_hurt_by else "",
##              "pkmn_hurt HP:" + str(this_event.pkmn_hurt.HP) if this_event.pkmn_hurt else "")
        
        # Make sure to finish all events at time t before checking battle status
        if len(tline.lst) > 0 and t == tline.lst[0].t:
            continue
        else:
            # Some Pokemon might faint after this round. Handle them
            
            # 1. check and manage defender
            dfdr = wd.dfdr_party.active_pkm
            if dfdr.HP <= 0:
                # This pokemon out
                dfdr.t_leave_ms = t
                dfdr.nonbackground_damage_taken += this_pkm.HP
                wd.battle_lengths.append(t)
                tline.lst = [e for e in tline if dfdr not in (e.pkmn_usedAtk, e.pkmn_hurt)]
                if wd.dfdr_party.alive():
                    # Next defender in
                    wd.dfdr_party.next_pkmn_up()
                    t = 0
                    wd.tline = timeline()
                    tline = wd.tline
                    initial_dfdr_events(wd)
                        
            # 2. check and manage attacker(s)
            for p in wd.atkr_parties:
                if p.active_pkm.HP <= 0 and p.alive():
                    # This pokemon out
                    p.active_pkm.t_leave_ms = t
                    # Bring the next Pokemon to the field
                    p.next_pkmn_up()
                    for e in tline:
                        if e.pkmn_hurt is atkr:
                            # Adjust queued damage to new comer
                            e.pkmn_hurt = p.active_pkm
                            e.dmg = damage(dfdr, p.active_pkm, e.move_hurt_by, wd.typeadvantages, wd.weather)
                    tline.lst = [e for e in tline if e.pkmn_usedAtk is not atkr]
                    tline.add(event("atkrEnter", t + ATKR_SUBSTITUTE_DELAY_MS_IDEAL, pkmn_usedAtk=p.active_pkm))
                    tline.add(event("atkrFree", t + ATKR_SUBSTITUTE_DELAY_MS_IDEAL + 100, pkmn_usedAtk=p.active_pkm))


    # At this point, battle is over. Assign a winner and return
    if not wd.battle_lengths:
        wd.battle_lengths.append(t)
    atkr_alive = any([p.alive() for p in wd.atkr_parties])
    dfdr_alive = wd.dfdr_party.alive()
    if not atkr_alive and not dfdr_alive:
        winner = -1 # tie
    elif atkr_alive:
        winner = 1 # atkr wins
    elif (dfdr_alive or t >= wd.timelimit_ms):
        winner = 2 # dfdr wins
    else: 
        print("THIS TEXT SHOULD NEVER BE SEEN. REPORT TO FELIX!")
        sys.exit(1)

    return winner



'''
This functions seems to be outdated
'''
'''
def raid_singleteam_battle(wd):
    # battle a raid with just one person's team.
    wd.tline = timeline()

    
    wd.battle_type = "raid"
    if "ho" in wd.dfdr.name and "oh" in wd.dfdr.name:
        raise Exception("Check that raids_list[5] has atkr.name " 
            + "and consider re-coding ho_oh to work for any intermediate character input")

    wd.timelimit_ms = ( TIMELIMIT_LEGENDARYRAID_MS if raidboss_dict[dfdr.name]["lvl"] == 5
        else TIMELIMIT_NORMALRAID_MS )    

    if wd.nOtherPlayers > 0:
        # add some backgroundDPS to simulate other people.
        # Assume the background DPS is so that 10 people would just barely defeat a Lugia
        # then normalize it to nPlayers = nOtherPlayers
        # and scale it to the defender's defense rather than Lugia's.
        dfdr_base_DEF_adj = wd.dfdr.species.base_DEF + raidboss_IVs[1]

        background_atk_interval_s = 2   # this must be reasonably high or else rounding dmg sux
                                        # and reasonably low or else dmg is lost at the end
        
        background_DPS = vs_lugia_DPS_per_other_player * nOtherPlayers * (lugia_base_DEF_adj/dfdr_base_DEF_adj)
        background_dmg = int(round( background_DPS * background_atk_interval_s))
        nBackgroundAtks = wd.timelimit_ms//(background_atk_interval_s*1000)

        for bgd_dmg_time in [1000*background_atk_interval_s*n for n in range(nBackgroundAtks)]:
            wd.tline.add(event("backgroundDmg", bgd_dmg_time, 
                dmg=background_dmg * otherplayers_DPS_profile(bgd_dmg_time/1000)))
            

    i_atkr = 0 # index of first non-dead atkr
    t = 0
    wd.new_battle_bool = True
    while i_atkr < len(wd.atkrs) and t < wd.timelimit_ms:
        # run the raid until first death
        wd.atkr = wd.atkrs[i_atkr]
        wd.starting_t_ms = t
        winner, t = raid_1v1_battle(wd)
        wd.new_battle_bool = False

        # continue until next death. If dfdr (raidboss) won:
        if wd.dfdr.HP > 0 and t < wd.timelimit_ms:
            i_atkr += 1
            if i_atkr == len(atkrs): break
            # there is time left. Continue with next pokemon.
            # let events which had already been planned stay on the timeline - I think
            # this is what Niantic does. 
            # Remove atkrFree and put it at ~1s past the time of death:
            wd.tline.lst = [evnt for evnt in wd.tline.lst if evnt.name != "atkrFree"]
            wd.tline.add(event("atkrFree", t + ATKR_SUBSTITUTE_DELAY_MS))
            
            # Adjust any damage planned on the attacker based on new typeadvantages & def:
            atkrHurt_evnts = [x for x in wd.tline.lst if x.name == "atkrHurt"]
            for atkrHurt_evnt in atkrHurt_evnts:
                atkrHurt_evnt.dmg = damage(wd.dfdr, wd.atkr, atkrHurt_evnt.move_hurt_by, wd.typeadvantages, wd.weather)
            
            continue
        else:
            # the raidboss is dead
            break

    if t > wd.timelimit_ms or wd.dfdr.HP > 0:
        raidwinner = 2 # pokemon 2 (defender) won
    else:
        raidwinner = 1 # pokemon 1 (attacker) won
    return raidwinner, t


'''

