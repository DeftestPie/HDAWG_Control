# Updated on 08/24/2022
import os
import time
import textwrap
import numpy as np
import zhinst.utils
import zhinst.ziPython as zi
import tkinter
import tkinter as tk
#from PIL import ImageTK, Image
from tkinter.filedialog import askopenfilename

window = tk.Tk()
window.title('HDAWG Controller')
window.geometry('800x600')
# canvas = tk.Canvas(window, width=400, height=300, bd=0, highlightthickness=0)
# imgpath = 'in-the-lab-2003.gif'
# img = Image.open(imgpath)
# photo = ImageTK.PhotoImage(img)
# canvas.create_image(400, 300, image=photo)
# canvas.pack()
bg = tk.PhotoImage(file="Doctor_Orlov.png")
label1 = tk.Label(window, image=bg)
label1.place(x=0, y=0)

path = tkinter.StringVar()

l = tk.Label(window, textvariable=path, bg='gray', font=('Arial', 12), width=100, height=2)
l.pack()


def selectPath():
    path_ = askopenfilename(title='Please choose a file', initialdir='/', filetypes=[('CSV file', '*.csv')])
    path.set(path_)


button_select_path = tk.Button(window, text='Choose file', width=30, height=2, command=selectPath)
button_select_path.pack()

v = tk.IntVar()
button_square = tk.Radiobutton(window, text='Generate Square Wave', variable=v, value=1)
button_square.pack()
button_sine = tk.Radiobutton(window, text='Generate Sine Wave', variable=v, value=2)
button_sine.pack()
button_file = tk.Radiobutton(window, text='Generate From Chosen File', variable=v, value=3)
button_file.pack()


def run_example(
        array,
        device_id,
        s_rate: int = 12,
        f_wave: int = 20,
        server_host: str = "localhost",
        server_port: int = 8004,
):
    """run the example."""
    # Settings
    apilevel_example = 6  # The API level supported by this example.
    # Call a zhinst utility function that returns:
    # - an API session `daq` in order to communicate with devices via the data server.
    # - the device ID string that specifies the device branch in the server's node hierarchy.
    # - the device's discovery properties.
    (daq, device, _) = zhinst.utils.create_api_session(
        device_id, apilevel_example, server_host=server_host, server_port=server_port
    )
    zhinst.utils.api_server_version_check(daq)

    # Create a base configuration: Disable all available outputs, awgs, demods, scopes,...
    zhinst.utils.disable_everything(daq, device)

    # 'system/awg/channelgrouping' : Configure how many independent sequencers
    #   should run on the AWG and how the outputs are grouped by sequencer.
    #   0 : 4x2 with HDAWG8; 2x2 with HDAWG4.
    #   1 : 2x4 with HDAWG8; 1x4 with HDAWG4.
    #   2 : 1x8 with HDAWG8.
    # Configure the HDAWG to use one sequencer for each pair of output channels
    daq.setInt(f"/{device}/system/awg/channelgrouping", 2)

    # Some basic device configuration to output the generated wave.
    out_channel = 0
    awg_channel = 0
    amplitude = 1.0
    range = 1.2
    # Code below is replaced by s_rate(AKA sampling rate)
    # while True:
    #     try:
    #         timeScaleMultiplier = int(input("Enter sample rate from 1-12 ((100 MHz)/2^n): "))
    #         break
    #
    #     except Exception:
    #         print("Please enter an integer")

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
        ["/%s/system/clocks/sampleclock/freq" % device, 100000000],
        ["/%s/awgs/0/time" % device, s_rate],
        ["/%s/awgs/0/userregs/0" % device, 0],
    ]
    daq.set(exp_setting)
    # Ensure that all settings have taken effect on the device before continuing.
    daq.sync()

    # Number of points in AWG waveform
    AWG_N = 2000

    # Define an AWG program as a string stored in the variable awg_program, equivalent to what would
    # be entered in the Sequence Editor window in the graphical UI.
    # This example demonstrates four methods of definig waveforms via the API
    # - (wave w0) loaded directly from programmatically generated CSV file wave0.csv.
    #             Waveform shape: Blackman window with negative amplitude.
    # - (wave w1) using the waveform generation functionalities available in the AWG Sequencer
    #             language.
    #             Waveform shape: Gaussian function with positive amplitude.
    # - (wave w2) using the vect() function and programmatic string replacement.
    #             Waveform shape: Single period of a sine wave.
    # - (wave w3) directly writing an array of numbers to the AWG waveform memory.
    #             Waveform shape: Sinc function. In the sequencer language, the waveform is
    #             initially defined as an array of zeros. This placeholder array is later
    #             overwritten with the sinc function.

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

    # Define an array of values that are used to write values for wave w0 to a CSV file in the
    # module's data directory

    firstWave = f_wave
    waveform_1 = array[..., firstWave]

    waveform_2 = array[..., firstWave + 1]

    waveform_3 = array[..., firstWave + 2]

    waveform_4 = array[..., firstWave + 3]

    # Fill the waveform values into the predefined program by inserting the array
    # as comma-separated floating-point numbers into awg_program.
    # Warning: Defining waveforms with the vect function can increase the code size
    #          considerably and should be used for short waveforms only.
    # awg_program = awg_program.replace("_w2_", ",".join([str(x) for x in waveform_2]))

    # Fill in the integer constant AWG_N
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
    # Let N be the total number of waveforms and M>0 be the number of waveforms defined from CSV
    # files. Then the index of the waveform to be replaced is defined as following:
    # - 0,...,M-1 for all waveforms defined from CSV file alphabetically ordered by filename,
    # - M,...,N-1 in the order that the waveforms are defined in the sequencer program.
    # For the case of M=0, the index is defined as:
    # - 0,...,N-1 in the order that the waveforms are defined in the sequencer program.
    # Of course, for the trivial case of 1 waveform, use index=0 to replace it.
    # The list of waves given in the Waveform sub-tab of the AWG Sequencer tab can be used to help
    # verify the index of the waveform to be replaced.
    # Here we replace waveform w3, the 4th waveform defined in the sequencer program. Using 0-based
    # indexing the index of the waveform we want to replace (w3, a vector of zeros) is 3:
    # index = 3
    # waveform_native = zhinst.utils.convert_awg_waveform(waveform_3)
    # path = f"/{device:s}/awgs/1/waveform/waves/{index:d}"
    # daq.setVector(path, waveform_native)

    print(
        f"Enabling the AWG: Set /{device}/awgs/0/userregs/0 to 1 to trigger waveform playback."
    )
    # This is the preferred method of using the AWG: Run in single mode continuous waveform playback
    # is best achieved by using an infinite loop (e.g., while (true)) in the sequencer program.
    daq.setInt(f"/{device}/awgs/0/userregs/0", 1)

    while True:
        daq.setInt(f"/{device}/awgs/0/single", 1)
        daq.setInt(f"/{device}/awgs/0/enable", 1)


s_host_input = tk.StringVar()
s_port_input = tk.IntVar()
d_id = tk.StringVar()
s_rate_input = tk.IntVar()
f_wave_input = tk.IntVar()

s_rate_label = tk.Label(window, text="Sample rate from 1-12 ((100 MHz)/2^n): ")
s_rate_label.place(x=50, y=360)
sr_input = tk.Entry(window, textvariable=s_rate_input)
sr_input.place(x=120, y=380)

f_wave_label = tk.Label(window, text="Column Index of first Wave: ")
f_wave_label.place(x=50, y=400)
fw_input = tk.Entry(window, textvariable=f_wave_input)
fw_input.place(x=120, y=420)

s_host_label = tk.Label(window, text="Server Host: ")
s_host_label.place(x=50, y=300)
server_host_input = tk.Entry(window, textvariable=s_host_input)
server_host_input.place(x=120, y=300)

s_port_label = tk.Label(window, text="Server Port: ")
s_port_label.place(x=50, y=320)
server_port_input = tk.Entry(window, textvariable=s_port_input)
server_port_input.place(x=120, y=320)

d_id_label = tk.Label(window, text="Device ID: ")
d_id_label.place(x=50, y=340)
d_id_input = tk.Entry(window, textvariable=d_id)
d_id_input.place(x=120, y=340)


def createSine(device_id, server_host: str = "localhost", server_port: int = 8004,):
    device = device_id
    daq = zi.ziDAQServer(server_host, server_port, 6)
    daq.connectDevice(device, '1GbE')

    # Generate waveform
    LENGTH = 1024
    wave_a = np.sin(np.linspace(0, 10 * np.pi, LENGTH)) * np.exp(np.linspace(0, -5, LENGTH))
    marker_a = np.concatenate([0b11 * np.ones(32), np.zeros(LENGTH - 32)]).astype(int)
    wave_raw_a = zhinst.utils.convert_awg_waveform(wave_a, markers=marker_a)
    set_cmd = (f'/{device:s}/awgs/0/waveform/waves/10', wave_raw_a)
    daq.set(set_cmd)

def generateWave():
    device_id = d_id.get()
    server_host = s_host_input.get()
    server_port = s_port_input.get()
    sampling_rate = s_rate_input.get()
    first_wave_column = f_wave_input.get()
    print("Device ID is: " + device_id)
    print("Server host is: " + server_host)
    print("Server port is: " + str(server_port))
    print("v is: " + str(v.get()))

    if int(v.get()) == 0:
        print("Please choose a wave generating mode!")
    else:
        if v.get() == 1:
            print("Generating square wave!")
        if v.get() == 2:
            print("Generating Sine wave!")
        if v.get() == 3:
            if path.get() != '':
                print("Generating wave from CSV file!")
                with open(path.get(), "r") as file_name:
                    array = np.loadtxt(file_name, delimiter=",")
                run_example(array, device_id, sampling_rate, first_wave_column, server_host, server_port)
            else:
                print("No CSV file is selected!")


button_testWave = tk.Button(window, text='Generate Wave', width=30, height=2, command=generateWave)
button_testWave.pack()


window.mainloop()
