from __future__ import print_function, division
import math
import bisect
import sys
import time
try: input = raw_input
except NameError: pass
import random

from pokelibrary import *   # to take out "" prefix of many variables for shorter code
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

graphical = False
if graphical: showlog = False # it will show anyway.
else: showlog = True
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
                                    
CMOVE_CHARGETIME_MS = 500           # how long it takes between tap and when the cmove is announced. Not needed after battle UI updated

STAB_MULTIPLIER = 1.2               # Same Type Attack Bonus damage multiplier

WAB_MULTIPLIER = 1.2                # Weather boosted Attack Bonus damage multiplier

ATKR_SUBSTITUTE_DELAY_MS_IDEAL = 900    # when switching out atkr or after death, how long until atkrFree?
                                        # found by a combination of frame-counting and game master guesses.
                                        
ATKR_SUBSTITUTE_LAG = 577               # how much lag follows the sub? found by frame-counting.
ATKR_SUBSTITUTE_DELAY_MS = ATKR_SUBSTITUTE_DELAY_MS_IDEAL + ATKR_SUBSTITUTE_LAG

DODGE_FAINT_BUG = True              # is there still a bug in the game when you dodge a move that would kill you?

DODGE_FAINT_AVOID_PERCENT = 0.5     # to avoid the bug, if BUG=True, I will not dodge if my HP<50%.

# subjective parameter used to determine how much damage other players do
# although 11 is pretty accurate in my experience in NYC and in Munich
nToBarelyBeatLugia = 11
lugia_HP = raidboss_HP[5]
lugia_base_DEF_adj = 323 + raidboss_IVs[1]
lugia_timelimit_s = TIMELIMIT_LEGENDARYRAID_MS//1000
vs_lugia_DPS_per_other_player = (lugia_HP/lugia_timelimit_s)/nToBarelyBeatLugia



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
    # types of event:
    # atkrFree: Attacking pokemon is free to perform another action right now.
    #        If it's an fmove the atkr gains energy at this time
    #        If it's a  cmove the atks might gain energy now, depending on charge time
    #        takes (name, t)
    # dfdrFree: Because the defender chooses each move at the beginning of the previous move,
    #        this event sets up the following move, not the one which is about to begin.
    #        So it puts damage & energy diff events on the timeline for a move which STARTS at 
    #        time = t + duration + rand(1500,2500). This is different from atkrFree, which chooses
    #        a move that starts at time = t.
    #        takes (name, t, current_move_duration, current_move_name)
    # pkmnHurt (pkmn=atkr or dfdr): A pokemon takes damage (and gains energy). Always happens
    #        separately from atkr/dfdrFree bc of the DamageWindowStart delay.
    #        takes (name, t, dmg, move_hurt_by)
    # pkmnEnergyDelta (pkmn=atkr or dfdr): A pokemon gains or loses energy. 
    #        Normally this happens inside 
    #        atkr/dfdrFree, so pEnergyDelta is not necessary, except in 2 situations:
    #              -when there is charge time on the cmove
    #              -when fmove spam is planned
    #        takes (name, t, energy_delta)
    #               energyDelta may be negative.
    # announce: Announce a message to the log at a particular time. This is only used for 
    #        attack announcements that are not made at the same time they were decided.
    #        takes (name, t, 
    # backgroundDmg: The dfdr takes background dmg to emulate a team of attackers.
    #        takes (bgd_dmg_time, background_dmg_per_1000ms)
    # updateLogs: Just update the logs. Used to log the beginning of fmove, cmove for 
    #        defenders because they dont make the decision the same time they start the move.
    #        Currently only works with logs for move start.

    def __init__(self, name, t, dmg=None, energy_delta=None, msg=None, move_hurt_by=None, 
        current_move_duration=None, current_move_name=None, pkmn_usedAtk=None, eventtype=None):
        # the name of the event (dfdrHurt, atkrFree, etc) and the time it happens (ms).
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
        # this is the duration of the move which starts at the event time t.
        self.current_move_duration = current_move_duration
        self.current_move_name = current_move_name
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
        # remove the first (earliest) event and remove it from the queue
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


def player_AI_choose(atkr, dfdr, tline, t, glog, typeadvantages, timelimit_ms, 
    dodge_success_probability, dodgeCMovesIfFree, weather):
    # for now, atkr will always be the player's pokemon.

    # this function chooses which move to use depending on the situation.
    # Here is the decision flow:
    # IF dodgeCMovesIfFree == True and the enemy has announced a cmove:
        ## IF I can kill enemy before being hit by defender's cmove
            ### IF I can kill it with fmove spam
                #### OUTCOME 1: fmove spam until dfdr dies
            ### ELIF I can kill it with cmove, + fmove spam:
                #### OUTCOME 2: cmove, then fmove spam until dfdr dies
        ## ELIF it's already in the dodge window
            ### OUTCOME 3: dodge (even if you have already dodged. dodging takes 500ms and the window is 700ms)
            ### it takes 1 or 2 dodges to do it. With 66% probability you need two dodges.
            ### If after your dodge is over, you are still in the dodge window, then you roll another dodge.
            ### If dodge_success_probability < threshhold, don't even bother dodging.
            ### threshhold = 40% for solo raids, 65% for team raids.
            ### dodge_success_probability is the probability of making a dodge if you are free to dodge.
            ### So the actual dodge probability is lower than dodge_success_probability,
            ### because sometimes you are busy during dodge time.
            ### dodge_success_probability is based on how quick the enemy's atk is (damageWindowStart):
            ### dodge_success_probability = 0.2 + ((1.0-0.2)/(3000-1800))*(dWS - 1800)
            ### the formula is approximate based on my own personal dodge success.
        ## ELIF I need to wait or I will miss my dodge AND it's past cmovereactiontime:
            ### IF I can still fit in an fmove
                #### OUTCOME 4: Use fmove
            #### ELSE
                #### OUTCOME 5: wait until dodge window begins + a short reaction time
        ## ELSE (aka if it's before cmovereactiontime):
            ### OUTCOME 6: just attack as usual
    # ELSE, I will attack:
        ## IF I do not have enough energy for a cmove:
            ### OUTCOME 7: use fmove
        ## ELIF fmove spam would kill before my cmove comes out,
            ### OUTCOME 8: fmove spam
        ## ELSE: I have enough energy for a cmove, so:
            ### OUTCOME 9: use cmove
        
        ##MAYBE TO ADD LATER: ELIF cmove would be very overkill and I have at least 35% HP remaining, use fmove

    atkrdiff, dfdrdiff = pdiff(), pdiff()
    atkr_fDmg = damage(atkr, dfdr, atkr.fmove, typeadvantages, weather)
    atkr_cDmg = damage(atkr, dfdr, atkr.cmove, typeadvantages, weather)
    dfdr_cDmg = damage(dfdr, atkr, dfdr.cmove, typeadvantages, weather)

    if dodgeCMovesIfFree and (DODGE_FAINT_BUG and atkr.HP/atkr.maxHP > DODGE_FAINT_AVOID_PERCENT):
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
                    tAnnounces = [t + n * atkr.fmove.duration for n in range(nFmovesAtkrCanFit)]
                    tEnergyGains = tAnnounces
                    tHurts = [t_ + atkr.fmove.dws for t_ in tAnnounces]
                    for n in range(nFmovesAtkrCanFit):
                        tline.add(event("announce", tAnnounces[n], 
                            msg="%.2f: %s used %s; gained %d energy." % 
                                ((timelimit_ms - tAnnounces[n])/1000, 
                                atkr.name, atkr.fmove.name, atkr.fmove.energygain)))
                        tline.add(event("atkrEnergyDelta", tEnergyGains[n], energy_delta=atkr.fmove.energygain))
                        tline.add(event("dfdrHurt", tAnnounces[n] + atkr.fmove.dws, 
                            dmg=atkr_fDmg, move_hurt_by = atkr.fmove))
                    tFree = tAnnounces[-1] + atkr.fmove.duration
                    tline.add(event("atkrFree", tFree))
                    return atkrdiff, dfdrdiff, tline, glog

                # can I fit in a cmove?
                time_left_if_atkr_cmoves = time_left_before_hurt - atkr.cmove.duration - TAP_TIMING_MS
                if time_left_if_atkr_cmoves > 0 and atkr.energy >= atkr.cmove.energycost:
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
                        # cmove timing depends on length of fmove:
                        if atkr.fmove.duration >= (CMOVE_CHARGETIME_MS + TAP_TIMING_MS):
                            # then you can completely charge your cmove during fmove
                            # so perform cmove in TAP_TIMING_MS seconds, off only by your timing.
                            tUseCmove = t + TAP_TIMING_MS
                        else:
                            # you can only partially charge your cmove during fmove
                            tUseCmove = (t + CMOVE_CHARGETIME_MS 
                                - min(atkr.fmove.duration - TAP_PERIOD_MS, CMOVE_CHARGETIME_MS - TAP_TIMING_MS))
                        tEnergyLoss = tUseCmove + atkr.cmove.dws
                        # first add the cmove to tline
                        tline.add(event("announce", tUseCmove, 
                            msg="%.2f: %s used %s!" % 
                                ((timelimit_ms - tEnergyLoss)/1000, 
                                atkr.name, atkr.cmove.name)))
                        tline.add(event("atkrEnergyDelta", tEnergyLoss,
                            energy_delta = -atkr.cmove.energycost))
                        tline.add(event("dfdrHurt", tEnergyLoss, 
                            dmg = atkr_cDmg, move_hurt_by = atkr.cmove))
                        # then add the fmoves
                        tCMoveOver = tUseCmove + atkr.cmove.duration
                        tAnnounces = [tCMoveOver + n * atkr.fmove.duration for n in range(nFmovesAtkrCanFit)]
                        tDamages = [tAnn + atkr.fmove.dws for tAnn in tAnnounces]
                        tEnergyDeltas = tDamages
                        for n in range(nFmovesAtkrCanFit):
                            tline.add(event("announce", tAnnounces[n], 
                                msg="%.2f: %s used %s!" % 
                                    ((timelimit_ms - tAnnounces[n])/1000, 
                                    atkr.name, atkr.fmove.name)))
                            tline.add(event("atkrEnergyDelta", tEnergyDeltas[n], energy_delta=atkr.fmove.energygain))
                            tline.add(event("dfdrHurt", tDamages[n], 
                                dmg=atkr_fDmg, move_hurt_by = atkr.fmove))
                        
                        tFree = (tAnnounces[-1] + atkr.fmove.duration if nFmovesAtkrCanFit>0 else 
                            tAnnounces[-1] + atkr.cmove.duration)
                        tline.add(event("atkrFree", tFree))
                        return atkrdiff, dfdrdiff, tline, glog
            
            # at this point, if I could have finished him off before hurt, the function has already returned.
            if (tDodgeWindowStart <= t < atkrHurt_cmove_event.t):
                
                ## OUTCOME 3: dodge (even if you have already dodged. dodging takes 500ms and the window is 700ms)
                enemyCmoveIndex = tline.lst.index(atkrHurt_cmove_event)
                # adjust damage to reflect dodging, with a certain probability:
                if (not randomness) or random.uniform(0,1) <= dodge_success_probability:
                    tline.lst[enemyCmoveIndex].dmg = max(
                        math.floor(tline.lst[enemyCmoveIndex].dmg*(1-dodgeDamageReductionPercent)), 1)
                else: 
                    
                    msg = "dodge failed! Dodge success%% =%4.f%%" % (dodge_success_probability*100)
                    if showlog: print(msg)
                    if graphical: glog.add(msg)
                if showlog:
                    update_logs("dodge", t, atkr, dfdr, glog, timelimit_ms, 
                        pkmn_usedAtk=dfdr, pkmn_hurt=atkr)
                if graphical:
                    glog = update_logs("dodge", t, atkr, dfdr, glog, timelimit_ms, 
                        pkmn_usedAtk=dfdr, pkmn_hurt=atkr)

                # attacker cannot move until dodge is over.
                # dodge 1 or 2 times, with 66% chance that it's 2 times.
                tFree = t + DODGE_COOLDOWN_MS * random.choice([1, 2, 2])
                tline.add(event("atkrFree", tFree))
                return atkrdiff, dfdrdiff, tline, glog
            # ELIF it's past cmovereactiontime AND I can still fit in an fmove before dodgewindow ends:
            # (doubled cmovereactiontime here bc it's hard to react to start of cmove sometimes)
            elif t >= tDfdrCMoveStart + 2*CMOVE_REACTIONTIME_MS:
                if t + atkr.fmove.duration < tDodgeWindowStart + DODGEWINDOW_LENGTH_MS:
                    
                    ## OUTCOME 4: Use fmove
                    if showlog: 
                        update_logs("use_fmove", t, atkr, dfdr, glog, timelimit_ms, 
                            pkmn_usedAtk=atkr)
                    if graphical: 
                        glog = update_logs("use_fmove", t, atkr, dfdr, glog, timelimit_ms,
                            pkmn_usedAtk=atkr)
                    atkrdiff.energydelta += atkr.fmove.energygain
                    tFree = t + atkr.fmove.duration
                    tline.add(event("dfdrHurt", t + atkr.fmove.dws, 
                        dmg=atkr_fDmg, move_hurt_by = atkr.fmove))
                    tline.add(event("atkrFree", tFree))
                    return atkrdiff, dfdrdiff, tline, glog
                else:
                    
                    ## OUTCOME 5: wait until dodge window begins + a short reaction time
                    tline.add(event("atkrFree"), tDodgeWindowStart + CMOVE_REACTIONTIME_MS)
                    return atkrdiff, dfdrdiff, tline, glog
            else:
                
                ## OUTCOME 6: just attack as usual, because you didn't notice that
                # the dfdr started a cmove yet. This happens next.
                pass

    # at this point, either dodgeCMovesIfFree == False or I should atk as usual.
    # Other outcomes have already returned.
    if atkr.energy < atkr.cmove.energycost:

        ## OUTCOME 7: use fmove
        if showlog: 
            update_logs("use_fmove", t, atkr, dfdr, glog, timelimit_ms, pkmn_usedAtk=atkr)
        if graphical: 
            glog = update_logs("use_fmove", t, atkr, dfdr, glog, timelimit_ms, pkmn_usedAtk=atkr)
        atkrdiff.energydelta += atkr.fmove.energygain
        tFree = t + atkr.fmove.duration
        tline.add(event("dfdrHurt", t + atkr.fmove.dws, dmg=atkr_fDmg, move_hurt_by = atkr.fmove))    
        tline.add(event("atkrFree", tFree))
        return atkrdiff, dfdrdiff, tline, glog

    # at this point, atkr has enough energy to use a cmove. Can I finish dfdr off faster
    # with fmove spam than with cmove?

    nFmovesAtkrCanFit = 1 + (atkr.cmove.dws + TAP_TIMING_MS - atkr.fmove.dws)//atkr.fmove.duration
    atkr_dmg_done_before_cmovedws = nFmovesAtkrCanFit * atkr_fDmg
    if atkr_dmg_done_before_cmovedws >= dfdr.HP: 

        # ## OUTCOME 8: fmove spam until dfdr dies
        tAnnounces = [t + n * atkr.fmove.duration for n in range(nFmovesAtkrCanFit)]
        tEnergyGains = tAnnounces
        tHurts = [t_ + atkr.fmove.dws for t_ in tAnnounces]
        for n in range(nFmovesAtkrCanFit):
            tline.add(event("announce", tAnnounces[n], 
                msg="%.2f: %s used %s; gained %d energy." % 
                    ((timelimit_ms - tAnnounces[n])/1000, 
                    atkr.name, atkr.fmove.name, atkr.fmove.energygain)))
            tline.add(event("atkrEnergyDelta", tEnergyGains[n], energy_delta=atkr.fmove.energygain))
            tline.add(event("dfdrHurt", tAnnounces[n] + atkr.fmove.dws, 
                dmg=atkr_fDmg, move_hurt_by=atkr.fmove))
        tFree = tAnnounces[-1] + atkr.fmove.duration
        tline.add(event("atkrFree", tFree))
        return atkrdiff, dfdrdiff, tline, glog
    else:

        ## OUTCOME 9: use cmove
        # cmove timing depends on length of fmove:
        if atkr.fmove.duration >= (CMOVE_CHARGETIME_MS + TAP_TIMING_MS):
            # then you can completely charge your cmove during fmove
            # so perform cmove in TAP_TIMING_MS seconds, off only by your timing.
            tUseCmove = t + TAP_TIMING_MS
        else:
            # you can only partially charge your cmove during fmove
            tUseCmove = (t + CMOVE_CHARGETIME_MS 
                - min(atkr.fmove.duration - TAP_PERIOD_MS, CMOVE_CHARGETIME_MS - TAP_TIMING_MS))
        tEnergyLoss = tUseCmove + atkr.cmove.dws
        tline.add(event("announce", tEnergyLoss, 
            msg="%.2f: %s used %s!" % 
                ((timelimit_ms - tEnergyLoss)/1000, 
                atkr.name, atkr.cmove.name)))
        tline.add(event("atkrEnergyDelta", tEnergyLoss, 
            energy_delta = -atkr.cmove.energycost))
        tline.add(event("dfdrHurt", tEnergyLoss, dmg=atkr_cDmg,
            move_hurt_by=atkr.cmove))
        tFree = tUseCmove + atkr.cmove.duration
        tline.add(event("atkrFree", tFree))
        return atkrdiff, dfdrdiff, tline, glog

    # Here is an explanation of the cmove charge timing:
    # supposing TAP_PERIOD_MS ~ 200
    # TAP_TIMING_MS ~ 50

    # fduration >= TAP_PERIOD_MS + chgtime: 
    #         time saved = chgtime - TAP_TIMING_MS
    # chgtime < fduration <  TAP_PERIOD_MS + chgtime: in this regime,  tap as fast as possible, so 
    #     but you should not be able to save ~the full 500ms, so adjust to: 
    #         saved time = min(fduration - TAP_PERIOD_MS, chgtime - TAP_TIMING_MS)
    # if fduration < chgtime, you gain
    #         saved time = fduration - TAP_PERIOD_MS    #         time saved = fduration - TAP_PERIOD_MS
    #     where fduration + TAP_PERIOD_MS was the time saved.

    #     note this could be negative, intentionally so. 
    # So actually there are only 2 cases.

    # Lastly, the time between the end of a quick move and the announcement of the next charge move is 
    # tUntilChgStart = chgtime - time saved
    print("YOU SHOULD NEVER SEE THIS TEXT")
    sys.exit(1)
    return atkrdiff, dfdrdiff, tline, glog

def gymdfdr_AI_choose(atkr, dfdr, tline, t, current_move_duration, current_move_name, 
    glog, typeadvantages, timelimit_ms, opportunityNum, randomness, weather):
    # in this function, atkr is always the attacker (player).
    # this is called when it is the defender's turn to start an atk,
    # it chooses what to use NEXT (so not at time=t, but at time=t+duration+delay)
    # based on the energy it WILL have AFTER the current move.

    t = tline.lst[0].t
    atkrdiff = pdiff()
    dfdrdiff = pdiff()
    
    if current_move_name == dfdr.fmove.name:
        projected_dfdr_energy = dfdr.energy + dfdr.fmove.energygain
    else:
        projected_dfdr_energy = dfdr.energy - dfdr.cmove.energycost

    # if you have enough energy, use a cmove 50% of time:
    use_cmove = False
    if projected_dfdr_energy + dfdr.cmove.energycost >= 0:
        if randomness:
            if random.random()<0.5:
                use_cmove = True
        else:
            # print("opportunity = %d" % opportunityNum)
            if opportunityNum==1:
                use_cmove = True
            opportunityNum = 1 - opportunityNum # switches 0 to 1 and vice versa,
                                                # causing cmove to be used every other opportunity.

    # choose when to begin the next move
    if not randomness:
        t_next_move = t + current_move_duration + 2000
    else:
        t_next_move = t + current_move_duration + random.randint(1500,2500)

    if use_cmove:
        # subtract energy cost at DWS
        t_energy_loss = t_next_move + dfdr.cmove.dws
        tline.add(event("dfdrEnergyDelta", t_energy_loss, energy_delta = -dfdr.cmove.energycost))

        # deal cmove damage to player at DWS
        t_player_hurt = t_next_move + dfdr.cmove.dws
        dmg = damage(dfdr, atkr, dfdr.cmove, typeadvantages, weather)
        tline.add(event("atkrHurt", t_player_hurt, dmg=dmg, move_hurt_by = dfdr.cmove))

        # set up next free time:
        tFree = t_next_move
        tline.add(event("dfdrFree", t_next_move, 
            current_move_duration = dfdr.cmove.duration, current_move_name = dfdr.cmove.name))

        # add logs to announce move
        tline.add(event("updateLogs", t_next_move, eventtype="use_cmove", pkmn_usedAtk=dfdr))
        
    # if not use a cmove, then use an fmove
    else:
        # add energy gain at DWS
        t_energy_gain = t_next_move + dfdr.fmove.dws
        tline.add(event("dfdrEnergyDelta", t_energy_gain, energy_delta = dfdr.fmove.energygain))

        # deal cmove damage to player at DWS
        t_player_hurt = t_next_move + dfdr.fmove.dws
        dmg = damage(dfdr, atkr, dfdr.fmove, typeadvantages, weather)
        tline.add(event("atkrHurt", t_player_hurt, dmg = dmg, move_hurt_by = dfdr.fmove))

        # set up next free time:
        tFree = t_next_move
        tline.add(event("dfdrFree", t_next_move, 
            current_move_duration = dfdr.fmove.duration, current_move_name = dfdr.fmove.name))

        # add logs to announce move
        tline.add(event("updateLogs", t_next_move, eventtype="use_fmove", pkmn_usedAtk=dfdr))
    
    return atkrdiff, dfdrdiff, tline, glog, opportunityNum

# reminder: types of event (atkrFree, dfdrEnergyDelta, etc) are listed earlier in the code.

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

def update_logs(eventtype, t, atkr, dfdr, glog, timelimit_ms,
    pkmn_usedAtk=None, pkmn_hurt=None, damage=None, hurtEnergyGain=None, move_hurt_by=None):
    msg2 = ""
    
    if eventtype == "use_fmove":
        # takes in pkmn_usedAtk
        msg = ("%.2f: %s used %s!" % (
            (timelimit_ms - t)/1000, pkmn_usedAtk.name, pkmn_usedAtk.fmove.name))
        msg = "%-45s +  %d HP / +%3d E" % (msg, 0, pkmn_usedAtk.fmove.energygain)
        
    elif eventtype == "use_cmove":
        # takes in pkmn_usedAtk
        msg = ("%.2f: %s used %s!" % (
            (timelimit_ms - t)/1000, pkmn_usedAtk.name, pkmn_usedAtk.cmove.name))
        msg = "%-45s +  %d HP / %3d E" % (msg, 0, -pkmn_usedAtk.cmove.energycost)

    elif eventtype == "hurt":
        # takes in pkmn_usedAtk, pkmn_hurt, hurtEnergyGain, move_hurt_by
        msg = "%.2f: %s was hurt by %s!" % (
            (timelimit_ms - t)/1000, pkmn_hurt.name, move_hurt_by.name)

        msg = "%-45s -%3d HP / +%3d E" % (msg, damage, hurtEnergyGain)
        timelen = len("%.2f" % ((timelimit_ms - t)/1000)) + 2
        if move_hurt_by is fmove:
            msg2 = "\n" + " "*timelen + "%s gained %d energy." % (
                pkmn_usedAtk.name, move_hurt_by.energygain)
        elif move_hurt_by is cmove:
            msg2 = "\n" + " "*timelen + "%s used up %d energy." % (
                pkmn_usedAtk.name, move_hurt_by.energycost)

    elif eventtype == "dodge":
        # takes in pkmn_usedAtk, pkmn_hurt
        msg = "%.2f: %s dodged %s!" % (
            (timelimit_ms - t)/1000, pkmn_hurt.name, pkmn_usedAtk.cmove.name)

    elif eventtype == "background_dmg":
        # takes in pkmn_hurt
        msg = "%.2f: %s took background dmg!" % (
            (timelimit_ms - t)/1000, pkmn_hurt.name)
        msg = "%-45s -%3d HP / +%3d E" % (msg, damage, hurtEnergyGain)

    atkrHP, atkrEnergy = str(int(atkr.HP)), str(int(atkr.energy))
    dfdrHP, dfdrEnergy = str(int(dfdr.HP)), str(int(dfdr.energy))

    msg += ( " " * (66-len(msg)) 
        + atkrHP + " "*(4 - len(atkrHP))
        + "| " + atkrEnergy + " "*(6-len(atkrEnergy)) 
        + " "*3 + dfdrHP + " "*(4 - len(dfdrHP))
        + "| %-3d"%dfdr.energy + " "*4 + "%6d" % t )

    msg = msg + msg2

    if showlog:
        print(msg)
        return
    if graphical: 
        glog.add(msg)
        return glog

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



def raid_1v1_battle(atkr, dfdr, speciesdata, typeadvantages, battle_type,
    new_battle_bool, dodgeCMovesIfFree, randomness, nOtherPlayers, weather, tline=timeline(), starting_t_ms=-1):
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

    if new_battle_bool:
        t = 0
        # add the starting times of atkr and dfdr.
        tline.add(event("atkrFree", 0))
        # energy gain happens JUST before the move starts so that the energy can be used
        # in the next defender move, which is chosen at beginning of this move.
        tline.add(event("dfdrEnergyDelta", 1000-1, energy_delta = dfdr.fmove.energygain))
        tline.add(event("dfdrFree",        1000, current_move_duration = dfdr.fmove.duration,
            current_move_name = dfdr.fmove.name))
        dfdr_fDmg = damage(dfdr,atkr,dfdr.fmove,typeadvantages,weather)
        tline.add(event("atkrHurt",        1000 + dfdr.fmove.dws, 
            dmg = dfdr_fDmg, move_hurt_by = dfdr.fmove))
        tline.add(event("dfdrEnergyDelta", 2000-1, energy_delta = dfdr.fmove.energygain))
        tline.add(event("atkrHurt",        2000 + dfdr.fmove.dws, 
            dmg = dfdr_fDmg, move_hurt_by = dfdr.fmove))
        dfdr.nonbackground_damage_taken = 0
    else:
        t = starting_t_ms
        if len(tline.lst)==0 or starting_t_ms==-1:
            raise Exception("\nFor battles which start in the middle, "
                + "you must input starting_t_ms and timeline.\n")

        
    if battle_type == "raid":
        timelimit_ms = ( TIMELIMIT_LEGENDARYRAID_MS if raidboss_dict[dfdr.name]["lvl"] == 5
            else TIMELIMIT_NORMALRAID_MS )
    if battle_type == "gym":
        timelimit_ms = TIMELIMIT_GYM_MS

    # these diffs will be modified & then added to the pokemons at once 
    # all events at this time have been parsed
    atkrdiff = pdiff()
    dfdrdiff = pdiff()

    # define the dodge success probability linearly, based on:
    # move          dws     dodge probability (guessing based on my experience)
    # zap cannon    3000    1.0
    # thunderbolt   1800    0.2
    dodge_success_probability = 0.2 + ((1.0-0.2)/(3000-1800))*(dfdr.cmove.dws - 1800)
    dodge_success_probability = max(dodge_success_probability, 0)
    dodge_success_probability = min(dodge_success_probability, 1)

    if nOtherPlayers == 0:
        # for solo raids, if dodge success rate < 40%, give up.
        if dodge_success_probability < 0.4: dodgeCMovesIfFree = False
    else:
        # for team raids, if dodge success rate < 65%, gives up.
        if dodge_success_probability < 0.65: dodgeCMovesIfFree = False

    # opportunityNum is changed from 0 to 1 each time the dfdr could have used a charge move. 
    # if opportinityNum == 1, and randomness is off, then dfdr will use a charge move.
    opportunityNum = 0

    glog = graphicallog()
    if graphical: printgraphicalstart()
    
    # do all the events in order.
    while (atkr.HP > 0 and dfdr.HP > 0 and t < timelimit_ms) or t == tline.lst[0].t:

        # handle first event on tline and remove current event from the timeline so it only gets handled once.
        t_prev = t
        this_event = tline.pop()
        t = this_event.t

        # case 1: a pokemon is free to decide on a move
        if "Free" in this_event.name:
            if "atkr" in this_event.name: # atkrFree
                # let AI handle this case (more complex)
                # player_AI_choose will also assign all new events to the timeline.
                atkrdiff_thisevent, dfdrdiff_thisevent, tline, glog = player_AI_choose(
                    atkr, dfdr, tline, t, glog, typeadvantages, timelimit_ms, 
                    dodge_success_probability, dodgeCMovesIfFree)
            else: # dfdrFree
                atkrdiff_thisevent, dfdrdiff_thisevent, tline, glog, opportunityNum = \
                    gymdfdr_AI_choose(atkr, dfdr, tline, t, this_event.current_move_duration, 
                        this_event.current_move_name, glog, typeadvantages, timelimit_ms, 
                        opportunityNum, randomness)
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
                if showlog: 
                    update_logs("hurt", t, atkr, dfdr, glog, timelimit_ms, 
                        pkmn_usedAtk=dfdr, pkmn_hurt=atkr, damage=this_event.dmg, 
                        hurtEnergyGain=hurtEnergyGain, move_hurt_by=this_event.move_hurt_by)
                if graphical: 
                    glog = update_logs("hurt", t, atkr, dfdr, glog, timelimit_ms,
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
                if showlog: 
                    update_logs("hurt", t, atkr, dfdr, glog, timelimit_ms,
                        pkmn_usedAtk=atkr, pkmn_hurt=dfdr, damage=this_event.dmg, 
                        hurtEnergyGain=hurtEnergyGain, move_hurt_by=this_event.move_hurt_by)
                if graphical: 
                    glog = update_logs("hurt", t, atkr, dfdr, glog, timelimit_ms,
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
                glog.add(this_event.msg)

        # case 5: dfdr (raid boss) takes background dmg to emulate a team of atkrs.
        elif this_event.name == "backgroundDmg":
            if randomness: this_event.dmg = this_event.dmg * random.uniform(0.7, 1.3)
            hurtEnergyGain = math.ceil(this_event.dmg/2)
            dfdrdiff.HPdelta -= this_event.dmg
            dfdrdiff.energydelta += hurtEnergyGain
            # do not add to total_nonbackground_damage_taken because I do not count backgroundDmg.
            dfdr.total_energy_gained += hurtEnergyGain

            if showlog: 
                update_logs("background_dmg", t, atkr, dfdr, glog, timelimit_ms, 
                    pkmn_hurt=dfdr, damage=this_event.dmg, hurtEnergyGain=hurtEnergyGain)
            if graphical: 
                glog = update_logs("background_dmg", t, atkr, dfdr, glog, timelimit_ms, 
                    pkmn_hurt=dfdr, damage=this_event.dmg, hurtEnergyGain=hurtEnergyGain)

        # case 6: just update the logs at this time.
        elif this_event.name == "updateLogs":
            eventtype = this_event.eventtype
            pkmn_usedAtk = this_event.pkmn_usedAtk
            if showlog:
                update_logs(eventtype, t, atkr, dfdr, glog, timelimit_ms,
                    pkmn_usedAtk=pkmn_usedAtk)
            if graphical: 
                glog = update_logs(eventtype, t, atkr, dfdr, glog, timelimit_ms,
                    pkmn_usedAtk=pkmn_usedAtk)

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
                glog.prnt()
                time.sleep(abs(t_prev - t)/1000)

    # assign a winner
    if dfdr.HP <= 0 and atkr.HP <= 0: winner = -1 # tie
    elif dfdr.HP <= 0: winner = 1 # atkr wins
    elif (atkr.HP <= 0 or t >= timelimit_ms): winner = 2 # dfdr wins
    else: 
        print("THIS TEXT SHOULD NEVER BE SEEN. REPORT TO FELIX!")
        sys.exit(1)
    return winner, atkr, dfdr, t, tline



def raid_singleteam_battle(atkrs, dfdr, speciesdata, typeadvantages, nOtherPlayers,
    dodgeCMovesIfFree, randomness, weather):
    # battle a raid with just one person's team.
    battle_type = "raid"
    if "ho" in dfdr.name and "oh" in dfdr.name:
        raise Exception("Check that raids_list[5] has atkr.name " 
            + "and consider re-coding ho_oh to work for any intermediate character input")

    timelimit_ms = ( TIMELIMIT_LEGENDARYRAID_MS if raidboss_dict[dfdr.name]["lvl"] == 5
        else TIMELIMIT_NORMALRAID_MS )
    tline = timeline()

    if nOtherPlayers > 0:
        # add some backgroundDPS to simulate other people.
        # Assume the background DPS is so that 10 people would just barely defeat a Lugia
        # then normalize it to nPlayers = nOtherPlayers
        # and scale it to the defender's defense rather than Lugia's.
        dfdr_base_DEF_adj = dfdr.species.base_DEF + raidboss_IVs[1]

        background_atk_interval_s = 2   # this must be reasonably high or else rounding dmg sux
                                        # and reasonably low or else dmg is lost at the end
        
        background_DPS = \
            vs_lugia_DPS_per_other_player * nOtherPlayers * (lugia_base_DEF_adj/dfdr_base_DEF_adj)
        background_dmg = int(round( background_DPS * background_atk_interval_s))
        nBackgroundAtks = timelimit_ms//(background_atk_interval_s*1000)

        for bgd_dmg_time in [1000*background_atk_interval_s*n for n in range(nBackgroundAtks)]:
            # here, I do not use tline.add() because tline is empty and I add in order anyway.
            tline.lst += [event("backgroundDmg", bgd_dmg_time, 
                dmg=background_dmg * otherplayers_DPS_profile(bgd_dmg_time/1000))]
            

    i_atkr = 0 # index of first non-dead atkr
    t = 0
    new_battle_bool = True
    while i_atkr < len(atkrs) and t < timelimit_ms:
        # run the raid until first death
        winner, atkrs[i_atkr], dfdr, t, tline = \
            raid_1v1_battle(atkrs[i_atkr], dfdr, speciesdata, typeadvantages, battle_type,
                new_battle_bool, dodgeCMovesIfFree, randomness, nOtherPlayers,
                tline = tline, starting_t_ms = t)
        new_battle_bool = False

        # continue until next death. If dfdr (raidboss) won:
        if dfdr.HP > 0 and t < timelimit_ms:
            i_atkr += 1
            if i_atkr == len(atkrs): break
            # there is time left. Continue with next pokemon.
            # let events which had already been planned stay on the timeline - I think
            # this is what Niantic does. 
            # Remove atkrFree and put it at ~1s past the time of death:
            tline.lst = [evnt for evnt in tline.lst if evnt.name != "atkrFree"]
            tline.add(event("atkrFree", t + ATKR_SUBSTITUTE_DELAY_MS))
            # Adjust any damage planned on the attacker based on new typeadvantages & def:
            atkrHurt_evnts = [x for x in tline.lst if x.name == "atkrHurt"]

            for atkrHurt_evnt in atkrHurt_evnts:
                atkrHurt_index = tline.lst.index(atkrHurt_evnt)
                # Adjust its damage to the new attacker.
                dmg0 = atkrHurt_evnt.dmg
                if atkrHurt_evnt.move_hurt_by.name == dfdr.fmove.name:
                    dmg1 = math.ceil( dmg0
                        * (damage_multiplier(dfdr, atkrs[i_atkr], dfdr.fmove, typeadvantages, weather)
                        / damage_multiplier(dfdr, atkrs[i_atkr-1], dfdr.fmove, typeadvantages, weather)) 
                        * (atkrs[i_atkr-1].DEF/atkrs[i_atkr].DEF))
                if atkrHurt_evnt.move_hurt_by.name == dfdr.cmove.name:
                    dmg1 = math.ceil( dmg0
                        * (damage_multiplier(dfdr, atkrs[i_atkr], dfdr.cmove, typeadvantages, weather)
                        / damage_multiplier(dfdr, atkrs[i_atkr-1], dfdr.cmove, typeadvantages, weather)) 
                        * (atkrs[i_atkr-1].DEF/atkrs[i_atkr].DEF))
                tline.lst[atkrHurt_index].dmg = dmg1        
            continue
        else:
            # the raidboss is dead
            break

    if t > timelimit_ms or dfdr.HP > 0:
        raidwinner = 2 # pokemon 2 (defender) won
    else:
        raidwinner = 1 # pokemon 1 (attacker) won
    return raidwinner, atkrs, dfdr, t, tline


def invalidInputError(invalidstr):
    raise Exception("\nTHAT'S AN INVALID INPUT.\n" +
        "Did you even NOTICE that you had entered '%s'???!??!" % 
        invalidstr)




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
    if 'y' in ans6: 
        ans6 = ('%s, %s' % 
            (atkr_species.fmoves[0].name, atkr_species.cmoves[0].name))
    if 'y' in ans7:
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
    print("       pkmn                   move    dws   duration  energydel  damage STAB*typadv")
    print("%11s fmove:%16s   %4d       %4d       %4d    %4d       %5g" % (
        atkr.name, atkr.fmove.name, atkr.fmove.dws, 
        atkr.fmove.duration, atkr.fmove.energygain, atkr_fDmg, 
        damage_multiplier(atkr, dfdr, atkr.fmove, typeadvantages, weather)))
    print("%11s cmove:%16s   %4d       %4d       %4d    %4d       %5g" % (
        atkr.name, atkr.cmove.name, atkr.cmove.dws, 
        atkr.cmove.duration, -atkr.cmove.energycost, atkr_cDmg, 
        damage_multiplier(atkr, dfdr, atkr.cmove, typeadvantages, weather)))
    print("%11s fmove:%16s   %4d       %4d       %4d    %4d       %5g" % (
        dfdr.name, dfdr.fmove.name, dfdr.fmove.dws, 
        dfdr.fmove.duration, dfdr.fmove.energygain, dfdr_fDmg, 
        damage_multiplier(dfdr, atkr, dfdr.fmove, typeadvantages, weather)))
    print("%11s cmove:%16s   %4d       %4d       %4d    %4d       %5g" % (
        dfdr.name, dfdr.cmove.name, dfdr.cmove.dws, 
        dfdr.cmove.duration, -dfdr.cmove.energycost, dfdr_cDmg, 
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
