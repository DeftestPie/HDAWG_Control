import os
import time
import textwrap
import numpy as np
import zhinst.utils
import tkinter
from tkinter.filedialog import askopenfilename
import csv


# Functions definition

def selectPath():
    path_ = askopenfilename(title='Please choose a file', initialdir='/', filetypes=[('CSV file', '*.csv')])
    path.set(path_)


def doNothing(device_id, server_host: str = "localhost", server_port: int = 8004):
    csv_path = getPath()
    with open(csv_path) as file_name:
        array = np.loadtxt(file_name, delimiter=",")

    server_host: str = "localhost"
    server_port: int = 8004

    apilevel_example = 6

    (daq, device, _) = zhinst.utils.create_api_session(
        device_id, apilevel_example, server_host=server_host, server_port=server_port
    )
    zhinst.utils.api_server_version_check(daq)
    zhinst.utils.disable_everything(daq, device)
    #   2 : 1x8 with HDAWG8.
    daq.setInt(f"/{device}/system/awg/channelgrouping", 2)

    out_channel = 0
    awg_channel = 0
    amplitude = 1.0
    range = 3

    exp_setting = [
        ["/%s/sigouts/%d/on" % (device, out_channel), 1],
        ["/%s/sigouts/%d/on" % (device, 1), 1],
        ["/%s/sigouts/%d/on" % (device, 2), 1],
        ["/%s/sigouts/%d/on" % (device, 3), 1],
        ["/%s/sigouts/%d/range" % (device, out_channel), range],
        ["/%s/sigouts/%d/range" % (device, 1), range],
        ["/%s/sigouts/%d/range" % (device, 2), range],
        ["/%s/sigouts/%d/range" % (device, 3), range],
        ["/%s/awgs/0/outputs/%d/amplitude" % (device, awg_channel), amplitude],
        ["/%s/awgs/0/outputs/%d/amplitude" % (device, 1), amplitude],
        ["/%s/awgs/0/outputs/%d/amplitude" % (device, 2), amplitude],
        ["/%s/awgs/0/outputs/%d/amplitude" % (device, 3), amplitude],

        ["/%s/awgs/0/outputs/0/modulation/mode" % device, 0],
        ["/%s/awgs/0/time" % device, 100],
        ["/%s/awgs/0/userregs/0" % device, 0],
    ]

    daq.set(exp_setting)
    # Ensure that all settings have taken effect on the device before continuing.
    daq.sync()

    # Number of points in AWG waveform
    AWG_N = 2000

    awg_program = textwrap.dedent(
        """\
        const AWG_N = _c1_;
        wave w1 = "wave1";
        wave w2 = "wave2";
        wave w3 = "wave3";
        wave w4 = "wave4";
        while(getUserReg(0) == 0);
        setTrigger(1);
        setTrigger(0);
        playWave(1,w1, 2, w2, 3, w3, 4 , w4);
        """
    )

    firstWave = 20
    waveform_1 = array[..., firstWave]

    waveform_2 = array[..., firstWave + 1]

    waveform_3 = array[..., firstWave + 2]

    waveform_4 = array[..., firstWave + 3]

    awg_program = awg_program.replace("_c1_", str(AWG_N))

    # Create an instance of the AWG Module
    awgModule = daq.awgModule()
    awgModule.set("device", device)
    awgModule.execute()

    # Get the modules data directory
    data_dir = awgModule.getString("directory")
    # All CSV files within the waves directory are automatically recognized by the AWG module
    wave_dir = os.path.join(data_dir, "awg", "waves")
    if not os.path.isdir(wave_dir):
        # The data directory is created by the AWG module and should always exist. If this exception
        # is raised, something might be wrong with the file system.
        raise Exception(
            f"AWG module wave directory {wave_dir} does not exist or is not a directory"
        )
    # Save waveform data to CSV
    csv_file = os.path.join(wave_dir, "wave1.csv")
    np.savetxt(csv_file, waveform_1)
    csv_file = os.path.join(wave_dir, "wave2.csv")
    np.savetxt(csv_file, waveform_2)
    csv_file = os.path.join(wave_dir, "wave3.csv")
    np.savetxt(csv_file, waveform_3)
    csv_file = os.path.join(wave_dir, "wave4.csv")
    np.savetxt(csv_file, waveform_4)

    # Transfer the AWG sequence program. Compilation starts automatically.
    awgModule.set("compiler/sourcestring", awg_program)
    # Note: when using an AWG program from a source file (and only then), the compiler needs to
    # be started explicitly with awgModule.set('compiler/start', 1)
    while awgModule.getInt("compiler/status") == -1:
        time.sleep(0.1)

    if awgModule.getInt("compiler/status") == 1:
        # compilation failed, raise an exception
        raise Exception(awgModule.getString("compiler/statusstring"))

    if awgModule.getInt("compiler/status") == 0:
        print(
            "Compilation successful with no warnings, will upload the program to the instrument."
        )
    if awgModule.getInt("compiler/status") == 2:
        print(
            "Compilation successful with warnings, will upload the program to the instrument."
        )
        print("Compiler warning: ", awgModule.getString("compiler/statusstring"))

    # Wait for the waveform upload to finish
    time.sleep(0.2)
    i = 0
    while (awgModule.getDouble("progress") < 1.0) and (
            awgModule.getInt("elf/status") != 1
    ):
        print(f"{i} progress: {awgModule.getDouble('progress'):.2f}")
        time.sleep(0.2)
        i += 1
    print(f"{i} progress: {awgModule.getDouble('progress'):.2f}")
    if awgModule.getInt("elf/status") == 0:
        print("Upload to the instrument successful.")
    if awgModule.getInt("elf/status") == 1:
        raise Exception("Upload to the instrument failed.")

    # Replace the waveform w3 with a new one.
    waveform_3 = np.sinc(np.linspace(-6 * np.pi, 6 * np.pi, AWG_N))

    print(
        f"Enabling the AWG: Set /{device}/awgs/0/userregs/0 to 1 to trigger waveform playback."
    )
    # This is the preferred method of using the AWG: Run in single mode continuous waveform playback
    # is best achieved by using an infinite loop (e.g., while (true)) in the sequencer program.
    daq.setInt(f"/{device}/awgs/0/userregs/0", 1)

    while True:
        daq.setInt(f"/{device}/awgs/0/single", 1)
        daq.setInt(f"/{device}/awgs/0/enable", 1)

def printPath():
    print(path.get())


def getPath():
    return path.get()


#
# def run_example(
#         device_id,
#         server_host: str = "localhost",
#         server_port: int = 8004,
# ):
#     """run the example."""
#     # Settings
#     apilevel_example = 6  # The API level supported by this example.
#     (daq, device, _) = zhinst.utils.create_api_session(
#         device_id, apilevel_example, server_host=server_host, server_port=server_port
#     )
#     zhinst.utils.api_server_version_check(daq)
#
#     # Create a base configuration: Disable all available outputs, awgs, demods, scopes,...
#     zhinst.utils.disable_everything(daq, device)
#
#     # 'system/awg/channelgrouping' : Configure how many independent sequencers
#     #   should run on the AWG and how the outputs are grouped by sequencer.
#     #   0 : 4x2 with HDAWG8; 2x2 with HDAWG4.
#     #   1 : 2x4 with HDAWG8; 1x4 with HDAWG4.
#     #   2 : 1x8 with HDAWG8.
#     # Configure the HDAWG to use one sequencer for each pair of output channels
#     daq.setInt(f"/{device}/system/awg/channelgrouping", 2)
#
#     # Some basic device configuration to output the generated wave.
#     out_channel = 0
#     awg_channel = 0
#     amplitude = 1.0
#     range = 3
#
#     exp_setting = [
#         ["/%s/sigouts/%d/on" % (device, out_channel), 1],
#         ["/%s/sigouts/%d/on" % (device, 1), 1],
#         ["/%s/sigouts/%d/on" % (device, 2), 1],
#         ["/%s/sigouts/%d/on" % (device, 3), 1],
#         ["/%s/sigouts/%d/range" % (device, out_channel), range],
#         ["/%s/sigouts/%d/range" % (device, 1), range],
#         ["/%s/sigouts/%d/range" % (device, 2), range],
#         ["/%s/sigouts/%d/range" % (device, 3), range],
#         ["/%s/awgs/0/outputs/%d/amplitude" % (device, awg_channel), amplitude],
#         ["/%s/awgs/0/outputs/%d/amplitude" % (device, 1), amplitude],
#         ["/%s/awgs/0/outputs/%d/amplitude" % (device, 2), amplitude],
#         ["/%s/awgs/0/outputs/%d/amplitude" % (device, 3), amplitude],
#
#         ["/%s/awgs/0/outputs/0/modulation/mode" % device, 0],
#         ["/%s/awgs/0/time" % device, 100],
#         ["/%s/awgs/0/userregs/0" % device, 0],
#     ]
#     daq.set(exp_setting)
#     # Ensure that all settings have taken effect on the device before continuing.
#     daq.sync()
#
#     # Number of points in AWG waveform
#     AWG_N = 2000
#
#     # Define an AWG program as a string stored in the variable awg_program, equivalent to what would
#     # be entered in the Sequence Editor window in the graphical UI.
#     # This example demonstrates four methods of definig waveforms via the API
#     # - (wave w0) loaded directly from programmatically generated CSV file wave0.csv.
#     #             Waveform shape: Blackman window with negative amplitude.
#     # - (wave w1) using the waveform generation functionalities available in the AWG Sequencer
#     #             language.
#     #             Waveform shape: Gaussian function with positive amplitude.
#     # - (wave w2) using the vect() function and programmatic string replacement.
#     #             Waveform shape: Single period of a sine wave.
#     # - (wave w3) directly writing an array of numbers to the AWG waveform memory.
#     #             Waveform shape: Sinc function. In the sequencer language, the waveform is
#     #             initially defined as an array of zeros. This placeholder array is later
#     #             overwritten with the sinc function.
#
#     awg_program = textwrap.dedent(
#         """\
#         const AWG_N = _c1_;
#         wave w1 = "wave1";
#         wave w2 = "wave2";
#         wave w3 = "wave3";
#         wave w4 = "wave4";
#         while(getUserReg(0) == 0);
#         setTrigger(1);
#         setTrigger(0);
#         playWave(1,w1, 2, w2, 3, w3, 4 , w4);
#         """
#     )
#
#     # Define an array of values that are used to write values for wave w0 to a CSV file in the
#     # module's data directory
#     firstWave = 20
#     waveform_1 = array[..., firstWave]
#
#     waveform_2 = array[..., firstWave + 1]
#
#     waveform_3 = array[..., firstWave + 2]
#
#     waveform_4 = array[..., firstWave + 3]
#
#     # Fill the waveform values into the predefined program by inserting the array
#     # as comma-separated floating-point numbers into awg_program.
#     # Warning: Defining waveforms with the vect function can increase the code size
#     #          considerably and should be used for short waveforms only.
#     # awg_program = awg_program.replace("_w2_", ",".join([str(x) for x in waveform_2]))
#
#     # Fill in the integer constant AWG_N
#     awg_program = awg_program.replace("_c1_", str(AWG_N))
#
#     # Create an instance of the AWG Module
#     awgModule = daq.awgModule()
#     awgModule.set("device", device)
#     awgModule.execute()
#
#     # Get the modules data directory
#     data_dir = awgModule.getString("directory")
#     # All CSV files within the waves directory are automatically recognized by the AWG module
#     wave_dir = os.path.join(data_dir, "awg", "waves")
#     if not os.path.isdir(wave_dir):
#         # The data directory is created by the AWG module and should always exist. If this exception
#         # is raised, something might be wrong with the file system.
#         raise Exception(
#             f"AWG module wave directory {wave_dir} does not exist or is not a directory"
#         )
#     # Save waveform data to CSV
#     csv_file = os.path.join(wave_dir, "wave1.csv")
#     np.savetxt(csv_file, waveform_1)
#     csv_file = os.path.join(wave_dir, "wave2.csv")
#     np.savetxt(csv_file, waveform_2)
#     csv_file = os.path.join(wave_dir, "wave3.csv")
#     np.savetxt(csv_file, waveform_3)
#     csv_file = os.path.join(wave_dir, "wave4.csv")
#     np.savetxt(csv_file, waveform_4)
#
#     # Transfer the AWG sequence program. Compilation starts automatically.
#     awgModule.set("compiler/sourcestring", awg_program)
#     # Note: when using an AWG program from a source file (and only then), the compiler needs to
#     # be started explicitly with awgModule.set('compiler/start', 1)
#     while awgModule.getInt("compiler/status") == -1:
#         time.sleep(0.1)
#
#     if awgModule.getInt("compiler/status") == 1:
#         # compilation failed, raise an exception
#         raise Exception(awgModule.getString("compiler/statusstring"))
#
#     if awgModule.getInt("compiler/status") == 0:
#         print(
#             "Compilation successful with no warnings, will upload the program to the instrument."
#         )
#     if awgModule.getInt("compiler/status") == 2:
#         print(
#             "Compilation successful with warnings, will upload the program to the instrument."
#         )
#         print("Compiler warning: ", awgModule.getString("compiler/statusstring"))
#
#     # Wait for the waveform upload to finish
#     time.sleep(0.2)
#     i = 0
#     while (awgModule.getDouble("progress") < 1.0) and (
#             awgModule.getInt("elf/status") != 1
#     ):
#         print(f"{i} progress: {awgModule.getDouble('progress'):.2f}")
#         time.sleep(0.2)
#         i += 1
#     print(f"{i} progress: {awgModule.getDouble('progress'):.2f}")
#     if awgModule.getInt("elf/status") == 0:
#         print("Upload to the instrument successful.")
#     if awgModule.getInt("elf/status") == 1:
#         raise Exception("Upload to the instrument failed.")
#
#     # Replace the waveform w3 with a new one.
#     waveform_3 = np.sinc(np.linspace(-6 * np.pi, 6 * np.pi, AWG_N))
#
#     print(
#         f"Enabling the AWG: Set /{device}/awgs/0/userregs/0 to 1 to trigger waveform playback."
#     )
#     # This is the preferred method of using the AWG: Run in single mode continuous waveform playback
#     # is best achieved by using an infinite loop (e.g., while (true)) in the sequencer program.
#     daq.setInt(f"/{device}/awgs/0/userregs/0", 1)
#
#     while True:
#         daq.setInt(f"/{device}/awgs/0/single", 1)
#         daq.setInt(f"/{device}/awgs/0/enable", 1)
#
#
# def generateWave():
#     import sys
#     from pathlib import Path
#     cli_util_path = Path(__file__).resolve().parent / "../../utils/python"
#     sys.path.insert(0, str(cli_util_path))
#     cli_utils = __import__("cli_utils")
#     cli_utils.run_commandline(run_example, __doc__)
#     sys.path.remove(str(cli_util_path))


# Create root window
root_window = tkinter.Tk()
# Title root window
root_window.title('HD Arbitrary Waveform Generator Controller')
# Set window size
root_window.geometry('800x450')

# Path
path = tkinter.StringVar()
# Label path selection
tkinter.Label(root_window, text="Target file directory:").grid(row=0, column=0)
# Path entry display
tkinter.Entry(root_window, textvariable=path).grid(row=0, column=1)
# Set select file button
tkinter.Button(root_window, text="Choose file", command=selectPath).grid(row=0, column=2)

# Set exit button
button_exit = tkinter.Button(root_window, text="Exit program", command=root_window.quit).grid(row = 1, column = 0)
# Place exit button
#button_exit.pack(side="bottom")

# Set waveform generation button
tkinter.Button(root_window, text='Generate waveform', command=doNothing).grid(row = 1, column = 2)

# Debug buttons
button_path_test = tkinter.Button(root_window, text="Print path", command=printPath).grid(row = 1, column = 1)

if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Loop root window
    root_window.mainloop()
