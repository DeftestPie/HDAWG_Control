import os
import time
import textwrap
import numpy as np
from tkinter import filedialog as fd
filename = fd.askopenfilename()
import csv
with open(filename,"r") as file_name:
    array = np.loadtxt(file_name, delimiter=",")

wave_form1 = array[..., 20]

out_channel = 0
awg_channel = 0
amplitude = 1.0
device = "dev8259"
Range = 1.2
timeScaleMultiplier = 10

exp_setting = [
        ["/%s/sigouts/%d/on" % (device, out_channel), 1],
        ["/%s/sigouts/%d/on" % (device, 1), 1],
        ["/%s/sigouts/%d/on" % (device, 2), 1],
        ["/%s/sigouts/%d/on" % (device, 3), 1],
        ["/%s/sigouts/%d/range" % (device, out_channel), Range],
        ["/%s/sigouts/%d/range" % (device, 1), Range],
        ["/%s/sigouts/%d/range" % (device, 2), Range],
        ["/%s/sigouts/%d/range" % (device, 3), Range],
        ["/%s/awgs/0/outputs/%d/amplitude" % (device, awg_channel), amplitude],
        ["/%s/awgs/0/outputs/%d/amplitude" % (device, 1), amplitude],
        ["/%s/awgs/0/outputs/%d/amplitude" % (device, 2), amplitude],
        ["/%s/awgs/0/outputs/%d/amplitude" % (device, 3), amplitude],

        ["/%s/awgs/0/outputs/0/modulation/mode" % device, 0],
        ["/%s/system/clocks/sampleclock/freq" % device, 100000000],
        ["/%s/awgs/0/time" % device, timeScaleMultiplier],
        ["/%s/awgs/0/userregs/0" % device, 0],
    ]

# for i in range(16):
#     print(exp_setting[i])

print("------------")
print(wave_form1)