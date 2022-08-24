import os
import time
import textwrap
import numpy as np
from tkinter import filedialog as fd
from time import sleep

a = 0

while True:
    try:
        sleep(1000)
        if a != 1:
            print("haha!")
    except Exception:
        print("fuck.")