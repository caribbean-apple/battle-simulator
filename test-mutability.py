from __future__ import print_function

outerlist = [[0],[1]]
innerlist = outerlist[1]
print("innerlist:", innerlist)
print("outerlist:", outerlist)
print("If I now add [2] to innerlist, it adds to outerlist as well:")

innerlist += [2]

print("innerlist     was changed:", innerlist)
print("outerlist     was changed:", outerlist)
print("but if a function adds [3] to innerlist, it does not get added to outerlist - huh?")

def f(lst):
    # holy crap, lst = lst + [3] makes a copy of the lst
    # but lst += [3] does not!
    # so it's not about the function.
    lst = lst + [3]
    return lst
innerlist = f(innerlist)

print("innerlist     was changed:", innerlist)
print("outerlist was not changed: ", outerlist)
print("And to make matters worse, with the function over, "
    +"even adding [4] outside of the function does not change outerlist now!")

innerlist += [4]

print("innerlist     was changed:", innerlist)
print("outerlist was not changed: ", outerlist)
