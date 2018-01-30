from __future__ import division, print_function
import pokelibrary as plib
import math
import battlesimlib as bsl

atkrname = "vaporeon"
atkrIVs = [15, 14, 6]
atkrlvl = 32.5
atkrfmovename = "water gun"
atkrcmovename = "hydro pump"

dfdrname = "charizard"
dfdrIVs = [15, 15, 15]
dfdrlvl = 1
dfdrfmovename = "fire spin"
dfdrcmovename = "dragon claw"
dfdrenergystart = 0

# f, c stand for atkr f and c moves
# F, C stand for dfdr f and c moves.
f, F = 'f', 'F'
c, C = 'c', 'C'

seq1 = "FFFFFFFFCFCFFCFFFCFFFCFFFCFFFFCFFFFCFFCFFFFFCFFCFFFCFFFF"
seq2 = "FFFFFFFFCFCFFCFFFCFFFCFFFCFFFFFFCFFFFCFFCFFFFFCFFCFFFCFFFF"
sequence = [c for c in seq1]


fmovedata, cmovedata, speciesdata, CPMultiplier, typeadvantages = plib.importAllGM()

atkrCPM = plib.CPM(atkrlvl, CPMultiplier)
atkrdex = plib.getPokedexNumber(atkrname, speciesdata)
atkrspecies = speciesdata[atkrdex]
atkrfmove = plib.getFMoveObject(atkrfmovename, fmovedata)
atkrcmove = plib.getCMoveObject(atkrcmovename, cmovedata)
atkr = plib.pokemon(atkrspecies, atkrIVs, atkrCPM, atkrfmove, atkrcmove, 'player')

dfdrCPM = plib.CPM(dfdrlvl, CPMultiplier)
dfdrdex = plib.getPokedexNumber(dfdrname, speciesdata)
dfdrspecies = speciesdata[dfdrdex]
dfdrfmove = plib.getFMoveObject(dfdrfmovename, fmovedata)
dfdrcmove = plib.getCMoveObject(dfdrcmovename, cmovedata)
dfdr = plib.pokemon(dfdrspecies, dfdrIVs, dfdrCPM, dfdrfmove, dfdrcmove, 'raid_boss')


f_energydel = math.ceil(bsl.damage(atkr, dfdr, atkrfmove, typeadvantages)/2)
c_energydel = math.ceil(bsl.damage(atkr, dfdr, atkrcmove, typeadvantages)/2)
F_energydel = dfdr.fmove.energygain
C_energydel = -dfdr.cmove.energycost

print("energy del matrix is:")
print("f    c      %d   %d" % (f_energydel, c_energydel))
print("F    C  =  %d   %d" % (F_energydel, C_energydel))

dfdrenergy = dfdrenergystart
opportunities = 0
cmovesused = 0
for item in sequence:
    if item == "f":
        dfdrenergy += f_energydel
    elif item == "c":
        dfdrenergy += c_energydel
    elif item == "F":
        if dfdrenergy >= dfdr.cmove.energycost: opportunities += 1
        dfdrenergy += F_energydel
    elif item == "C":
        opportunities += 1
        cmovesused += 1
        dfdrenergy += C_energydel
    dfdrenergy = min(100, dfdrenergy)
    if dfdrenergy < 0:
        print("dfdrenergy<0!!!!")
        import ips; ips.ips()

print("Of %d opportunities, %d were cmoves." % (opportunities, cmovesused))
print("or %f percent."%(cmovesused/opportunities))