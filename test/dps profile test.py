import battlesimlib as bsl
import matplotlib.pyplot as plt

xvals = range(300)
yvals = [bsl.otherplayers_DPS_profile(xval) for xval in xvals]

plt.plot(xvals, yvals)
plt.show()