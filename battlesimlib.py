from __future__ import print_function, division
import math
import bisect
import sys
import time
try: input = raw_input
except NameError: pass
import random

from pokelibrary import *
from ui import *
import csvimport as cv
import winsound

"""
TO DO:
-I removed cmove announcements from EnergyDelta event. They should be added to announce event.
This only matters for cmoves with large charge time. The announce events should only be added 
if log options (graphical? showlog?) are on.

-Count lag time in youtube videos (how many fmoves per time?). Add an attacker lag with this.

-Add a test: do not try to dodge if your HP is more than 1.1x their cmove damage
"""

# NOTE: currently, there is a (somewhat arbitrary) dodge_success_probability,
# defined in raid_1v1_battle. 
#
# If dodge_success_probability < 0.4, the attacker does not even attempt to dodge.


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

# subjective parameter used to determine how much damage other players do
# although 11 is pretty accurate in my experience in NYC and in Munich
nToBarelyBeatLugia = 11
lugia_HP = raidboss_HP[5]
lugia_base_DEF_adj = 323 + raidboss_IVs[1]
lugia_timelimit_s = TIMELIMIT_LEGENDARYRAID_MS//1000
vs_lugia_DPS_per_other_player = (lugia_HP/lugia_timelimit_s)/nToBarelyBeatLugia




def invalidInputError(invalidstr):
    raise Exception("\nTHAT'S AN INVALID INPUT.\n" +
        "Did you even NOTICE that you had entered '%s'???!??!" % 
        invalidstr)



def damage_multiplier(pkmn_usedAtk, pkmn_hurt, atk, typeadvantages, weather):
    STAB = 1
    if atk.dtype in [pkmn_usedAtk.type1, pkmn_usedAtk.type2]:
        STAB = STAB_MULTIPLIER
        
    WAB = 1
    if atk.dtype in WEATHER_BOOSTED_TYPES[weather]:
        WAB = WAB_MULTIPLIER

    typadv1 = typeadvantages[atk.dtype][pkmn_hurt.type1]
    typadv2 = 1 if pkmn_hurt.type2=="none" else typeadvantages[atk.dtype][pkmn_hurt.type2]
    return STAB * WAB * typadv1 * typadv2

def damage(pkmn_usedAtk, pkmn_hurt, atk, typeadvantages, weather = 'EXTREME'):
    mult = damage_multiplier(pkmn_usedAtk, pkmn_hurt, atk, typeadvantages, weather)
    # calculate damage.
    dmg = math.ceil(0.5*pkmn_usedAtk.ATK*atk.power*mult/pkmn_hurt.DEF)
    return dmg



class event:
    # events sit on the timeline and carry instructions / information
    # about what they should change or do.
    #
    # TYPE OF EVENT
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
    # pkmnEnergyDelta: A pokemon (atkr or dfdr) gains or loses energy. 
    #           Normally this happens inside 
    #           atkr/dfdrFree, so pEnergyDelta is not necessary, except in 2 situations:
    #              -when there is charge time on the cmove
    #              -when fmove spam is planned
    #           takes (name, t, energy_delta)
    #               energyDelta may be negative.
    # announce: Announce a message to the log at a particular time. This is only used for 
    #           attack announcements that are not made at the same time they were decided.
    #           takes (name, t, 
    # backgroundDmg: The dfdr takes background dmg to emulate a team of attackers.
    #           takes (bgd_dmg_time, background_dmg_per_1000ms)
    # updateLogs: Just update the logs. Used to log the beginning of fmove, cmove for 
    #           defenders because they dont make the decision the same time they start the move.
    #           Currently only works with logs for move start.

    def __init__(self, name, t, dmg=None, energy_delta=None, msg=None, move_hurt_by=None, 
        current_move=None, pkmn_usedAtk=None, eventtype=None):
        # the name(type) of the event (dfdrHurt, atkrFree, etc) and the time it happens (ms).
        self.name = name
        self.t = t
        # only for pkmnHurt event:
        self.dmg = dmg
        # only for pEnergyDelta event:
        self.energy_delta = energy_delta # this may be negative
        # only for announce event:
        self.msg = msg # this is the text that should be printed for an announce event
        self.move_hurt_by = move_hurt_by
        # only for dfdrFree:
        # `current_move is the move which starts at the event time t.
        self.current_move = current_move
        # only for updateLogs event
        self.pkmn_usedAtk = pkmn_usedAtk
        self.eventtype = eventtype

    def __lt__(self, other): return self.t < other.t
    def __le__(self, other): return self.t <= other.t
    def __gt__(self, other): return self.t > other.t
    def __ge__(self, other): return self.t >= other.t
    def __eq__(self, other): return self.t == other.t



class timeline:
    def __init__(self):
        self.lst = []

    def add(self, event):
        # add the event at the proper (sorted) spot.
        bisect.insort_left(self.lst, event)

    def pop(self):
        # return the first (earliest) event and remove it from the queue
        return self.lst.pop(0)

    def print(self):
        print("==Timeline== ", end="")
        for event in self.lst:
            print(str(event.t) + ":" + event.name, end=", ")
        print()


            
class pdiff:
    def __init__(self):
        self.HPdelta = 0
        self.energydelta = 0 # can be positive or negative!!
    def add(self, pdiff2):
        self.HPdelta += pdiff2.HPdelta
        self.energydelta += pdiff2.energydelta
        return self
    def prnt(self):
        print("HPdelta: %d\nenergydelta: %d" % 
            (self.HPdelta, self.energydelta))


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
    atkr = None
    dodge_success_probability = 0
    dodgeCMovesIfFree = False
    atkrs = []
    teams = [] # To be implemented
    dfdr = None
    randomness = False
    opportunityNum = 0

    # Part 3: Battle parameters variables
    battle_type = None
    new_battle_bool = None
    nOtherPlayers = 0
    timelimit_ms = 0
    tline = timeline()
    starting_t_ms = -1
    glog = graphicallog()
    weather = 'EXTREME'

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def importGM(self, GMFilePath):
        self.fmovedata, self.cmovedata, self.speciesdata, self.CPMultiplier, self.typeadvantages = importGM(GMFilePath)

    def importAllGM(self):
        self.fmovedata, self.cmovedata, self.speciesdata, self.CPMultiplier, self.typeadvantages = importAllGM()




def atkr_use_move(pkm, tline, t, move, dmg, isFreeAfter=True):
    # tline.add(event("announce", t, msg="%s used %s" % (pkm.name, move.name)))
    tline.add(event("atkrEnergyDelta", t + move.dws, energy_delta=move.energydelta))
    tline.add(event("dfdrHurt", t + move.dws, dmg=dmg, move_hurt_by=move))
    if isFreeAfter:
        tline.add(event("atkrFree", t + move.duration))

def dfdr_use_move(pkm, tline, t, move, dmg):
    tline.add(event("updateLogs", t, eventtype=("use_%smove" % move.mtype), pkmn_usedAtk=pkm))
    tline.add(event("dfdrEnergyDelta", t + move.dws, energy_delta=move.energydelta))
    tline.add(event("atkrHurt", t + move.dws, dmg=dmg, move_hurt_by=move))
    # defender makes decision at the beginning of the previous move
    tline.add(event("dfdrFree", t, current_move = move)) 



def player_AI_choose(wd, t):
    # for now, atkr will always be the player's pokemon.
    atkr = wd.atkr
    dfdr = wd.dfdr
    tline = wd.tline

    atkrdiff, dfdrdiff = pdiff(), pdiff()
    atkr_fDmg = damage(atkr, dfdr, atkr.fmove, wd.typeadvantages, wd.weather)
    atkr_cDmg = damage(atkr, dfdr, atkr.cmove, wd.typeadvantages, wd.weather)
    dfdr_cDmg = damage(dfdr, atkr, dfdr.cmove, wd.typeadvantages, wd.weather)

    if wd.dodgeCMovesIfFree and (not DODGE_FAINT_BUG or wd.nOtherPlayers ==0 or atkr.HP > dfdr_cDmg):
        atkrHurt_cmove_events = [x for x in tline.lst if (x.name=='atkrHurt' and x.dmg==dfdr_cDmg)]
        if len(atkrHurt_cmove_events) > 0:
            # At this point, the enemy has announced a cmove.
            atkrHurt_cmove_event = atkrHurt_cmove_events[0]
            tDfdrCMoveStart = \
                atkrHurt_cmove_event.t - dfdr.cmove.dws
            tDodgeWindowStart = \
                atkrHurt_cmove_event.t - DODGEWINDOW_LENGTH_MS + DODGE_REACTIONTIME_MS 
            time_left_before_hurt = atkrHurt_cmove_event.t - t

            # IF I can finish him off before being hurt, do so.
            # can I finish him with just fmoves? First, can I even use one fmove?
            if atkr.fmove.dws < time_left_before_hurt:
                # yes, I can. How many?
                nFmovesAtkrCanFit = 1 + (time_left_before_hurt - atkr.fmove.dws)//atkr.fmove.duration
                atkr_dmg_done_before_hurt = nFmovesAtkrCanFit * atkr_fDmg
                if atkr_dmg_done_before_hurt >= dfdr.HP: 
                    # ## OUTCOME 1: fmove spam until dfdr dies
                    for n in range(nFmovesAtkrCanFit):
                        atkr_use_move(atkr, tline, tAnnounces[n], atkr.fmove, atkr_fDmg, False)                      
                    tFree = tAnnounces[-1] + atkr.fmove.duration
                    tline.add(event("atkrFree", tFree))
                    
                    return atkrdiff, dfdrdiff

                # can I fit in a cmove?
                time_left_if_atkr_cmoves = time_left_before_hurt - atkr.cmove.duration - TAP_TIMING_MS
                if time_left_if_atkr_cmoves > 0 and atkr.energy + atkr.cmove.energydelta >= 0:
                    # yes, I can. Add up (so far) the damage I can do:
                    atkr_dmg_done_before_hurt = atkr_cDmg
                    # how many fmoves can I still fit in after the cmove, by spam-tapping?
                    if atkr.fmove.dws >= time_left_if_atkr_cmoves: 
                        nFmovesAtkrCanFit = 0
                    else:
                        nFmovesAtkrCanFit = 1 + (time_left_if_atkr_cmoves - atkr.fmove.dws)//atkr.fmove.duration
                        atkr_dmg_done_before_hurt += nFmovesAtkrCanFit * atkr_fDmg
                    # is this enough to finish off the defender before he gets off the cmove?
                    if atkr_dmg_done_before_hurt >= dfdr.HP: 

                        ## OUTCOME 2: cmove, then fmove spam. 
                        # *UPDATE* after battle UI rework, you can tap the button and use cmove right away
                        tUseCmove = t

                        # first add the cmove to tline
                        atkr_use_move(atkr, tline, tUseCmove, atkr.cmove, atkr_cDmg)

                        # then add the fmoves
                        tCMoveOver = tUseCmove + atkr.cmove.duration
                        tAnnounces = [tCMoveOver + n * atkr.fmove.duration for n in range(nFmovesAtkrCanFit)]
                        for n in range(nFmovesAtkrCanFit):
                            atkr_use_move(atkr, tline, tAnnounces[n], atkr.fmove, atkr_fDmg, False)
                        
                        tFree = (tAnnounces[-1] + atkr.fmove.duration if nFmovesAtkrCanFit>0 else 
                            tAnnounces[-1] + atkr.cmove.duration)
                        tline.add(event("atkrFree", tFree))
                        return atkrdiff, dfdrdiff
            
            # at this point, if I could have finished him off before hurt, the function has already returned.
            if (tDodgeWindowStart <= t < atkrHurt_cmove_event.t):
                
                ## OUTCOME 3: dodge (even if you have already dodged. dodging takes 500ms and the window is 700ms)
                enemyCmoveIndex = tline.lst.index(atkrHurt_cmove_event)
                # adjust damage to reflect dodging, with a certain probability:
                if (not wd.randomness) or random.uniform(0,1) <= wd.dodge_success_probability:
                    tline.lst[enemyCmoveIndex].dmg = max(
                        math.floor(tline.lst[enemyCmoveIndex].dmg*(1-dodgeDamageReductionPercent)), 1)
                else: 
                    msg = "dodge failed! Dodge success%% =%4.f%%" % (wd.dodge_success_probability*100)
                    if showlog: print(msg)
                    if graphical: wd.glog.add(msg)
                if showlog or graphical:
                    update_logs(wd, t, "dodge", pkmn_usedAtk=dfdr, pkmn_hurt=atkr)

                # attacker cannot move until dodge is over.
                # dodge 1 or 2 times, with 66% chance that it's 2 times.
                tFree = t + DODGE_COOLDOWN_MS * random.choice([1, 2, 2])
                tline.add(event("atkrFree", tFree))
                return atkrdiff, dfdrdiff
            # ELIF it's past cmovereactiontime AND I can still fit in an fmove before dodgewindow ends:
            # (doubled cmovereactiontime here bc it's hard to react to start of cmove sometimes)
            elif t >= tDfdrCMoveStart + 2*CMOVE_REACTIONTIME_MS:
                if t + atkr.fmove.duration < tDodgeWindowStart + DODGEWINDOW_LENGTH_MS:
                    
                    ## OUTCOME 4: Use fmove
                    if showlog or graphical: 
                        update_logs(wd, t, "use_fmove", pkmn_usedAtk=atkr)
                    atkr_use_move(atkr, tline, t, atkr.fmove, atkr_fDmg)
                    
                    return atkrdiff, dfdrdiff
                else:
                    
                    ## OUTCOME 5: wait until dodge window begins + a short reaction time
                    tline.add(event("atkrFree", tDodgeWindowStart + CMOVE_REACTIONTIME_MS))
                    return atkrdiff, dfdrdiff
            else:
                
                ## OUTCOME 6: just attack as usual, because you didn't notice that
                # the dfdr started a cmove yet. This happens next.
                pass

    # at this point, either dodgeCMovesIfFree == False or I should atk as usual.
    # Other outcomes have already returned.
    if atkr.energy + atkr.cmove.energydelta < 0:

        ## OUTCOME 7: use fmove
        if showlog or graphical: 
            update_logs(wd, t, "use_fmove", pkmn_usedAtk=atkr)
        atkr_use_move(atkr, tline, t, atkr.fmove, atkr_fDmg)
        
        return atkrdiff, dfdrdiff

    # at this point, atkr has enough energy to use a cmove. Can I finish dfdr off faster
    # with fmove spam than with cmove?

    nFmovesAtkrCanFit = 1 + (atkr.cmove.dws + TAP_TIMING_MS - atkr.fmove.dws)//atkr.fmove.duration
    atkr_dmg_done_before_cmovedws = nFmovesAtkrCanFit * atkr_fDmg
    if atkr_dmg_done_before_cmovedws >= dfdr.HP: 

        # ## OUTCOME 8: fmove spam until dfdr dies
        tAnnounces = [t + n * atkr.fmove.duration for n in range(nFmovesAtkrCanFit)]
        for n in range(nFmovesAtkrCanFit):         
            atkr_use_move(atkr, tline, tAnnounces[n], atkr.fmove, atkr_fDmg, False)
        tline.add(event("atkrFree", tAnnounces[-1] + atkr.fmove.duration))
        
        return atkrdiff, dfdrdiff
    else:

        ## OUTCOME 9: use cmove
        atkr_use_move(atkr, tline, t, atkr.cmove, atkr_cDmg)

        return atkrdiff, dfdrdiff

    print("YOU SHOULD NEVER SEE THIS TEXT")
    sys.exit(1)
    return atkrdiff, dfdrdiff



def gymdfdr_AI_choose(wd, t, current_move):
    # in this function, atkr is always the attacker (player).
    # this is called when it is the defender's turn to start an atk,
    # it chooses what to use NEXT (so not at time=t, but at time=t+duration+delay)
    # based on the energy it WILL have AFTER the current move.

    atkr = wd.atkr
    dfdr = wd.dfdr
    tline = wd.tline

    t = tline.lst[0].t
    atkrdiff = pdiff()
    dfdrdiff = pdiff()
    
    projected_dfdr_energy = dfdr.energy + current_move.energydelta


    # decide fmove or move to use next.
    next_move = dfdr.fmove
    if projected_dfdr_energy + dfdr.cmove.energydelta >= 0:
        # if you have enough energy, use a cmove 50% of time:
        if wd.randomness:
            if random.random()<0.5:
                next_move = dfdr.cmove
        else:
            # print("opportunity = %d" % opportunityNum)
            if wd.opportunityNum == 1:
                next_move = dfdr.cmove
            wd.opportunityNum = 1 - wd.opportunityNum # switches 0 to 1 and vice versa,
                                                # causing cmove to be used every other opportunity.
    # calculate damage
    dmg = damage(dfdr, atkr, next_move, wd.typeadvantages, wd.weather)

    # choose when to begin the next move
    if not wd.randomness:
        t_next_move = t + current_move.duration + 2000
    else:
        t_next_move = t + current_move.duration + random.randint(1500,2500)

    # finally, pend events to timeline
    dfdr_use_move(dfdr, tline, t_next_move, next_move, dmg)
    
    return atkrdiff, dfdrdiff



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



def raid_1v1_battle(wd):
    # This function faces one pkmn against one pkmn.
    # this function can start a new battle or continue an existing one after a pokemon died,
    # depending on whether new_battle_bool = True. 

    # if "new_battle_bool", it will start from after GO! disappears, so dfdr will do the many starting fmoves.
    # in this case one must pass:
    #   -time_remaining_ms as the time left in the battle
    #   -tline as the existing timeline... 
    #       -ALREADY WITH THE LOSER'S EVENTS REMOVED!!
    #       -ALREADY WITH THE NEXT POKEMON's NEXT EVENT INCLUDED!!
    # time_remaining_ms defaults to -1 because it will always be set in a new_battle_bool, based on battle_type.

    atkr = wd.atkr
    dfdr = wd.dfdr
    tline = wd.tline

    if wd.new_battle_bool:
        t = 0
        # add the starting times of atkr and dfdr.
        tline.add(event("atkrFree", 0))
        # energy gain happens JUST before the move starts so that the energy can be used
        # in the next defender move, which is chosen at beginning of this move.
        tline.add(event("dfdrEnergyDelta", 1000-1, energy_delta = dfdr.fmove.energydelta))
        tline.add(event("dfdrFree",        1000, current_move = dfdr.fmove))
        dfdr_fDmg = damage(dfdr, atkr, dfdr.fmove, wd.typeadvantages, wd.weather)
        tline.add(event("atkrHurt", 1000 + dfdr.fmove.dws, dmg = dfdr_fDmg, move_hurt_by = dfdr.fmove))
        tline.add(event("dfdrEnergyDelta", 2000-1, energy_delta = dfdr.fmove.energydelta))
        tline.add(event("atkrHurt",2000 + dfdr.fmove.dws, dmg = dfdr_fDmg, move_hurt_by = dfdr.fmove))
        dfdr.nonbackground_damage_taken = 0
    else:
        t = wd.starting_t_ms
        if len(tline.lst)==0 or wd.starting_t_ms==-1:
            raise Exception("\nFor battles which start in the middle, "
                + "you must input starting_t_ms and timeline.\n")

        
    if wd.battle_type == "raid":
        wd.timelimit_ms = ( TIMELIMIT_LEGENDARYRAID_MS if raidboss_dict[dfdr.name]["lvl"] == 5
            else TIMELIMIT_NORMALRAID_MS )
    elif wd.battle_type == "gym":
        wd.timelimit_ms = TIMELIMIT_GYM_MS

    # these diffs will be modified & then added to the pokemons at once 
    # all events at this time have been parsed
    atkrdiff = pdiff()
    dfdrdiff = pdiff()

    # define the dodge success probability linearly, based on:
    # move          dws     dodge probability (guessing based on my experience)
    # zap cannon    3000    1.0
    # thunderbolt   1800    0.2
    wd.dodge_success_probability = 0.2 + ((1.0-0.2)/(3000-1800))*(dfdr.cmove.dws - 1800)
    wd.dodge_success_probability = max(min(wd.dodge_success_probability, 1),0)

##    if wd.nOtherPlayers == 0:
##        # for solo raids, if dodge success rate < 40%, give up.
##        if wd.dodge_success_probability < 0.4: wd.dodgeCMovesIfFree = False
##    else:
##        # for team raids, if dodge success rate < 65%, gives up.
##        if wd.dodge_success_probability < 0.65: wd.dodgeCMovesIfFree = False

    # opportunityNum is changed from 0 to 1 each time the dfdr could have used a charge move. 
    # if opportinityNum == 1, and randomness is off, then dfdr will use a charge move.
    wd.opportunityNum = 0

    wd.glog = graphicallog()
    if graphical: printgraphicalstart()
    
    # do all the events in order.
    while (atkr.HP > 0 and dfdr.HP > 0 and t < wd.timelimit_ms) or t == tline.lst[0].t:

        # handle first event on tline and remove current event from the timeline so it only gets handled once.
        t_prev = t
        this_event = tline.pop()
        t = this_event.t

        # case 1: a pokemon is free to decide on a move
        if "Free" in this_event.name:
            if "atkr" in this_event.name: # atkrFree
                # let AI handle this case (more complex)
                # player_AI_choose will also assign all new events to the timeline.
                atkrdiff_thisevent, dfdrdiff_thisevent = player_AI_choose(wd, t)
            else: # dfdrFree
                atkrdiff_thisevent, dfdrdiff_thisevent = gymdfdr_AI_choose(wd, t, this_event.current_move)
            atkrdiff.add(atkrdiff_thisevent)
            dfdrdiff.add(dfdrdiff_thisevent)
            atkr.total_energy_gained += atkrdiff.energydelta
            dfdr.total_energy_gained += dfdrdiff.energydelta

        # case 2: a pokemon takes damage
        elif "Hurt" in this_event.name:
            hurtEnergyGain = math.ceil(this_event.dmg/2)
            # inflict the damage to the pkmn which was attacked
            # also give it the corresponding energy gain
            if "atkr" in this_event.name:
                atkrdiff.HPdelta -= this_event.dmg
                atkrdiff.energydelta += hurtEnergyGain
                atkr.total_energy_gained += hurtEnergyGain
                if showlog or graphica: 
                    update_logs(wd, t, "hurt",  
                        pkmn_usedAtk=dfdr, pkmn_hurt=atkr, damage=this_event.dmg, 
                        hurtEnergyGain=hurtEnergyGain, move_hurt_by=this_event.move_hurt_by)
            else: # dfdrHurt
                dfdrdiff.HPdelta -= this_event.dmg
                dfdrdiff.energydelta += math.ceil(this_event.dmg/2)
                dfdr.total_energy_gained += math.ceil(this_event.dmg/2)
                dfdr.nonbackground_damage_taken += this_event.dmg
                if -dfdrdiff.HPdelta > dfdr.HP: 
                    overkill_dmg = -dfdrdiff.HPdelta - dfdr.HP
                    dfdr.nonbackground_damage_taken -= overkill_dmg
                if showlog or graphical: 
                    update_logs(wd, t, "hurt",
                        pkmn_usedAtk=atkr, pkmn_hurt=dfdr, damage=this_event.dmg, 
                        hurtEnergyGain=hurtEnergyGain, move_hurt_by=this_event.move_hurt_by)

        # case 3: a pokemon loses energy
        elif "EnergyDelta" in this_event.name:
            if "atkr" in this_event.name:
                atkrdiff.energydelta += this_event.energy_delta
            else: #dfdrEnergyDelta
                dfdrdiff.energydelta += this_event.energy_delta

        # case 4: an attack has to be announced (& was not already announced)
        elif this_event.name == "announce":
            if showlog:
                print(this_event.msg)
            if graphical:
                wd.glog.add(this_event.msg)

        # case 5: dfdr (raid boss) takes background dmg to emulate a team of atkrs.
        elif this_event.name == "backgroundDmg":
            if randomness: this_event.dmg = this_event.dmg * random.uniform(0.7, 1.3)
            hurtEnergyGain = math.ceil(this_event.dmg/2)
            dfdrdiff.HPdelta -= this_event.dmg
            dfdrdiff.energydelta += hurtEnergyGain
            # do not add to total_nonbackground_damage_taken because I do not count backgroundDmg.
            dfdr.total_energy_gained += hurtEnergyGain

            if showlog: 
                update_logs("background_dmg", t, atkr, dfdr, wd.glog, wd.timelimit_ms, 
                    pkmn_hurt=dfdr, damage=this_event.dmg, hurtEnergyGain=hurtEnergyGain)
            if graphical: 
                update_logs("background_dmg", t, atkr, dfdr, wd.glog, wd.timelimit_ms, 
                    pkmn_hurt=dfdr, damage=this_event.dmg, hurtEnergyGain=hurtEnergyGain)

        # case 6: just update the logs at this time.
        elif this_event.name == "updateLogs":
            eventtype = this_event.eventtype
            pkmn_usedAtk = this_event.pkmn_usedAtk
            if showlog or graphical:
                update_logs(wd, t, eventtype, pkmn_usedAtk=pkmn_usedAtk)

        # finish all events at this time before applying & resetting pdiffs
        if len(tline.lst) > 0 and tline.lst[0].t == this_event.t:
            continue
        else:
            # now all events at this time are done. Apply diffs.
            atkr.HP += atkrdiff.HPdelta
            atkr.energy = min(atkr.energy + atkrdiff.energydelta, atkr.maxenergy)
            dfdr.HP += dfdrdiff.HPdelta
            dfdr.energy = min(dfdr.energy + dfdrdiff.energydelta, dfdr.maxenergy)

            #reset diffs to 0 in preparation for the next time
            atkrdiff = pdiff()
            dfdrdiff = pdiff()

            if graphical:
                print("\n"*20)
                printgraphicalstatus(atkr, dfdr)
                wd.glog.prnt()
                time.sleep(abs(t_prev - t)/1000)

    # assign a winner
    if dfdr.HP <= 0 and atkr.HP <= 0: winner = -1 # tie
    elif dfdr.HP <= 0: winner = 1 # atkr wins
    elif (atkr.HP <= 0 or t >= wd.timelimit_ms): winner = 2 # dfdr wins
    else: 
        print("THIS TEXT SHOULD NEVER BE SEEN. REPORT TO FELIX!")
        sys.exit(1)
    return winner, t



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
        
        background_DPS = \
            vs_lugia_DPS_per_other_player * nOtherPlayers * (lugia_base_DEF_adj/dfdr_base_DEF_adj)
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
                atkrHurt_index = wd.tline.lst.index(atkrHurt_evnt)
                # Adjust its damage to the new attacker.
                dmg1 = math.ceil(atkrHurt_evnt.dmg
                        * (damage_multiplier(wd.dfdr, wd.atkr, atkrHurt_evnt.move_hurt_by, wd.typeadvantages, wd.weather)
                        / damage_multiplier(wd.dfdr, wd.atkr, atkrHurt_evnt.move_hurt_by, wd.typeadvantages, wd.weather)) 
                        * (wd.atkrs[i_atkr-1].DEF/wd.atkr.DEF))
                tline.lst[atkrHurt_index].dmg = dmg1        
            continue
        else:
            # the raidboss is dead
            break

    if t > wd.timelimit_ms or wd.dfdr.HP > 0:
        raidwinner = 2 # pokemon 2 (defender) won
    else:
        raidwinner = 1 # pokemon 1 (attacker) won
    return raidwinner, t




