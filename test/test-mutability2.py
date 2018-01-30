from __future__ import print_function
# case 1: modify a copy of 'a' within a function.
# a will be modified!
# a = [[1],2]
# def f2(a):
#     a += [3]
#     return
# f2(a)
# print("case 1:")
# print(a)
# print()

# case 2: modify a list which happens to be in another list, in a function.
# the sublist gets "hi" added to it, but the main list does not.
outerlist = [[0],[1]]
innerlist = outerlist[1]
innerlist += [2]

def f(a):
    a = a + [3]
    return a
innerlist = f(innerlist)

print("case 2:")
print("f added 3 to innerlist:")
print(innerlist)
print("...but even though innerlist = a[0], which is a mutable object, the list a is unchanged:")
print(outerlist)
print("If I had directly added to innerlist by uncommenting the code, a would be changed.")
print("But if I do it after the function call, a is unchanged!")
innerlist += [1.66]
print(outerlist)