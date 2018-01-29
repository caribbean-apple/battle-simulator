from __future__ import print_function, division
try: input = raw_input
except NameError: pass

import csv
import sys
#import numpy as np

#CSV importer.
#does not handle commas or newlines within entries.
#scroll to the bottom to enter CSV files to import & clean

# data = importcsv("ivs-dex.csv",
#     typelist=["int", "int", "int", "int"],
#     colsToKeep=[0,1,2,4])
# dataT = transpose(IVdata)

def transpose(data):
    trans = [list(x) for x in zip(*data)]
    return trans

def convertToNestedList(data):
    print("==> Converting data to nested list... ", end="")
    newdata = []
    for n in range(len(data)):
        newdata+=[data[n].split(",")]
    print("done.")
    print("Data has %d rows. Its first, second, and last lines " \
        "have %d, %d, and %d columns, respectively.\n" %
        (len(data), len(data[0]), len(data[1]), len(data[-1])))
    return newdata

def removeEmptyRows(data):
    print("==> Removing empty rows from data... ", end="")
    cleandata=[]
    for m in range(len(data)):
        length = len(data[m])
        for n in range(length):
            if n < length-1 and data[m][n] != '':
                #if there is ANY nonempty stuff, add the whole row.
                cleandata+=[data[m]]
                break
    print("done. \nData had %d empty rows, %d nonempty of %d total. \n" % 
        (len(data)-len(cleandata), len(cleandata), len(data)))
    return cleandata

def keepOnlyTheseColumns(data, colsToKeep):
    #colsToKeep should be the indicies of the desired columns
    #if left blank, keeps all cols
    if colsToKeep == []:
        print("==> Keeping all columns.\n")
        return data
    print("==> Keeping only these columns:")
    for n in range(len(colsToKeep)):
        print("Col "+str(colsToKeep[n])+": "+data[0][n])
    newdata=[]
    print("Working... ", end="")
    for n in range(len(data)):
        addline = []
        for col in colsToKeep:
            addline+=[data[n][col].replace('\n','')]
        newdata+=[addline]
    print("done. \n%d Columns remain of %d columns originally (in 1st line)" %
        (len(newdata[0]), len(data[0])))
    print("First line is now:")
    print(newdata[0])
    print("Second line is now:")
    print(newdata[1])
    print()
    return newdata

def rowLen(row):
    lastfullcol = -1
    for n in range(len(row)):
        if row[n]!='' and row[n]!='\n':
            lastfullcol = n
    return lastfullcol+1

def sanityCheck(data):
    #check 1: find the min and max length of the rows
    print("==> Sanity checking... ", end="")
    minlen=999999999999999999
    maxlen=0
    for n in range(len(data)):
        length = rowLen(data[n])
        if length > maxlen:
            maxlen = length
        if length < minlen:
            minlen = length
    print("done. \nThe number of columns per row ranges from %d to %d\n" %
        (minlen, maxlen))

def txtToNpArray(text):
    text = text.replace("[","")
    text = text.replace("]","")
    # text = text.replace(" ","")
    text = text.split()
    text2=[]
    for n in text:
        # print("converting to float: %s"%n)
        text2+=[float(n)]
    #return np.asarray(text2)
    return text2

def convertDataTypes(data, typelist):
    nSuccessfulTypes = 0
    nFailedTypes = 0
    if typelist==[]:
        return data
    #len(typelist) must be number of rows.

    print("==> Converting types. Upon error, leaving as string... ")
    newdata = []
    for n in range(len(data)):
        row = data[n]
        newrow = []
        if len(typelist) != len(data[n]):
            raise IndexError("length of typelist != length data[%d]."
             % n)

        for m in range(len(row)):
            typ = typelist[m].lower()
            typ = typ.replace(" ","")
            oldpt = row[m].lower()

            if typ in ["str", "string", "s"]:
                newrow+=[oldpt]
                nSuccessfulTypes+=1
                continue

            elif typ in ["float", "f"]:
                try:
                    newpt = float(oldpt)
                    newrow+=[newpt]
                    nSuccessfulTypes+=1
                    continue
                except ValueError:
                    nFailedTypes+=1
                    print("ConvertFail %d on row %d: cant cnvt '%s' to type '%s'." % 
                        (nFailedTypes, n, oldpt, typ))
                    newrow+=[oldpt]
                    continue

            elif typ in ["int", "i", "d"]:
                try:
                    newpt = int(oldpt)
                    newrow+=[newpt]
                    nSuccessfulTypes+=1
                    continue
                except ValueError:
                    nFailedTypes+=1
                    print("ConvertFail %d on row %d: cant cnvt '%s' to type '%s'." % 
                        (nFailedTypes, n, oldpt, typ))
                    newrow+=[oldpt]
                    continue

            elif typ in ["bool", "boolean", "b"]:
                truebools_lower = ["1", "true",  "t"]
                falsebools_lower= ["0", "false", "f"]
                if oldpt in truebools_lower:
                    newrow+=[True]
                    nSuccessfulTypes+=1
                    continue
                if oldpt in falsebools_lower:
                    newrow+=[False]
                    nSuccessfulTypes+=1
                    continue
                else:
                    nFailedTypes+=1
                    print("ConvertFail %d on row %d: cant cnvt '%s' to type '%s'." % 
                        (nFailedTypes, n, oldpt, typ))
                    newrow+=[oldpt]
                    continue

            elif typ in ["nparray", "np.array", "numpyarray", 
            "numpy.array", "np"]:
                try:
                    newpt = txtToNpArray(oldpt)
                    newrow+=[newpt]
                    nSuccessfulTypes+=1
                    continue
                except ValueError:
                    nFailedTypes+=1
                    print("ConvertFail %d on row %d: cant cnvt '%s' to type '%s'." % 
                        (nFailedTypes, n, oldpt, typ))
                    newrow+=[oldpt]
                    continue
            else:
                #this should never happen but just in case
                print("YOU SHOULD NEVER SEE THIS")
                newrow+=[oldpt]
                nFailedTypes+=1
        newdata+=[newrow]
    print("...done.\n")
    print("%d of %d (%.3f%%) type conversions were unsuccessful." % (nFailedTypes,
        nSuccessfulTypes+nFailedTypes, 
        100*nFailedTypes/(nSuccessfulTypes+nFailedTypes)))
    if nFailedTypes>0:
        print("Failed conversions were left as a string.")

    return newdata

def importcsv(path, colsToKeep=[], typelist=[]):

    ans = input("""Ready to import from csv. 
        Have you backed up your csv file(s)? y/n: """)
    if not (ans in ["yes", "yy", "y"]):
        print("exiting. Please back up your data first!")
        sys.exit()
    print()

    print("==============================="+"="*len(path))
    print("======IMPORTING/CLEANING %s======" % path)
    print("==============================="+"="*len(path))
    print("Importing... ",end="")
    newdata = []
    with open(path, "r") as f:
        reader = csv.reader(f, delimiter=",")
        for cell in reader:
            newdata += [cell]
        f.close()
    print("done.")
    print("First line is:\n", newdata[0])
    try: print("Second line is:\n", newdata[1])
    except IndexError: print()
    print()


    #check if inputted typelist is valid
    validtypes = ["string", "str", "s", 
    "float", "f", 
    "int", "i", "d", 
    "bool", "boolean","b", 
    "nparray", "np.array", "numpyarray", "numpy.array", "np"]

    typelist = [(x.lower()).replace(" ","") for x in typelist]
    for typ in typelist:
        if not (typ in validtypes):
            print("ERROR: You entered an invalid typename: '%s'." % typ)
            print("Valid type names are:")
            for n in range(len(validtypes)-1):
                print("%s, " % validtypes[n], end="")
            print(validtypes[-1], "\n")
            sys.exit(1)

    sanityCheck(newdata)
    newdata = keepOnlyTheseColumns(newdata, colsToKeep)
    newdata = convertDataTypes(newdata,typelist)
    #newdata = convertToNestedList(newdata) #deprecated: csvreader does it
    newdata = removeEmptyRows(newdata)     #sometimes necessary
    return newdata

# data = importcsv("ivs-dex.csv",
#     typelist=["int", "int", "int", "int"],
#     colsToKeep=[0,1,2,4])
# dataT = transpose(IVdata)
