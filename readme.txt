battlesim v2.0 changes:
-Built on Desert's gym-sim modification and fixed a small situational bug. Gym mode can be turned on/off by opening "battlesimlib.py" and changing gymmode =True or =False. If =False it will be attacker vs attacker.
-Individual runs are now run with the command 'python singlesim.py'
-Added a batch CSV mode, where you can get the results of all battles that you put into a CSV very quickly. Run it with 'python batchsim.py', directions will be printed to the command line.
-fixed a bug where some events wouldn't show in log
-fixed a bug where pokemon couldn't tie (can test with identical pokemon for example)
-added the option to have attacker always dodge as long as they were not "busy" during the whole 700ms dodge window. So they will miss a few dodges if they used a long-duration move right before the dodge window for example. Dodges are realistic / 500ms.
-added the option to remove randomness, so that attackers always use charge moves on their 2nd opportunity, and they always wait 2000ms in between attacks instead of random(1500ms,2500ms).
-changed ASCII UI so that attacker is on the bottom left, defender on the top right

how to use:
-individual run, with graphics or log: in cmd prompt, navigate to this folder and type 'python singlesim.py'
-batch run: in cmd prompt, navigate to this folder and type 'python batchsim.py'
-if you move stuff out of the folder, it might not work anymore.
-there are lots of settings that can be changed at the beginning of each file. Open with a text editor and you can change these:
	-in 'battlesimlib.py' graphical = True turns on the ASCII-art battle version.
	-in 'battlesimlib.py' showlog = True shows the log of the battle. It will automatically be on if graphical = True so in that case the value of this variable makes no difference.
	-in 'battlesimlib.py' gymmode = True makes the mechanics work so that the first pokemon chosen is attacker, second is defender, and they battle with real pokemongo mechanics. If False, both pokemon will battle as if they are gym-attackers, simulating a PVP battle.
	-in 'battlesimlib.py' dodgeCMovesIfFree = True means the attacker will dodge ONLY the defender's charge moves. If the attacker was busy during the whole dodge window (like if they used a long charge move at just the wrong time) they will miss the dodge.
	-in 'battlesimlib.py' turnOffRandomness = True makes the defender always use their charge move every other time that they have enough energy. In reality, they just randomly use it 50% of the time when they have enough energy. So turning this on makes the mechanics incorrect but simpler. ALSO, real gym defenders wait between 1500ms and 2500ms randomly between attacks. If turnOffRandomness = True, they will ALWAYS wait 2000ms. Again this is not how gym battles actually work.
