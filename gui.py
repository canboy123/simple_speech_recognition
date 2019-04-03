# from appJar import gui
# # create a GUI variable called app
# app = gui("Login Window", "400x200")
# # add & configure widgets - widgets get a name, to help referencing them later
# app.addLabel("title", "Welcome to appJar")
# app.setLabelBg("title", "red")
# app.addLabelEntry("Username")
# app.addLabelSecretEntry("Password")
# def press(button):
#     if button == "Cancel":
#         app.stop()
#     else:
#         usr = app.getEntry("Username")
#         pwd = app.getEntry("Password")
#         print("User:", usr, "Pass:", pwd)
#         # link the buttons to the function called press
#
# app.addButtons(["Submit", "Cancel"], press)
# app.setBg("orange")
# app.setFont(18)
# app.go()

# import PySimpleGUIWeb as sg
import PySimpleGUI as sg
import datetime
import os
import speech_recognition as sr
import time
import math
import collections
import audioop

from speech_recognition import Recognizer, AudioData, RequestError, UnknownValueError, AudioSource, WaitTimeoutError
import json

try:  # attempt to use the Python 2 modules
    from urllib import urlencode
    from urllib2 import Request, urlopen, URLError, HTTPError
except ImportError:  # use the Python 3 modules
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen
    from urllib.error import URLError, HTTPError

class Recognizer2(Recognizer):
    def __init__(self):
        """
        Creates a new ``Recognizer`` instance, which represents a collection of speech recognition functionality.
        """
        super(Recognizer2, self).__init__()

    def recognize_google(self, audio_data, key=None, language="en-US", show_all=False):
        """
        Performs speech recognition on ``audio_data`` (an ``AudioData`` instance), using the Google Speech Recognition API.

        The Google Speech Recognition API key is specified by ``key``. If not specified, it uses a generic key that works out of the box. This should generally be used for personal or testing purposes only, as it **may be revoked by Google at any time**.

        To obtain your own API key, simply following the steps on the `API Keys <http://www.chromium.org/developers/how-tos/api-keys>`__ page at the Chromium Developers site. In the Google Developers Console, Google Speech Recognition is listed as "Speech API".

        The recognition language is determined by ``language``, an RFC5646 language tag like ``"en-US"`` (US English) or ``"fr-FR"`` (International French), defaulting to US English. A list of supported language tags can be found in this `StackOverflow answer <http://stackoverflow.com/a/14302134>`__.

        Returns the most likely transcription if ``show_all`` is false (the default). Otherwise, returns the raw API response as a JSON dictionary.

        Raises a ``speech_recognition.UnknownValueError`` exception if the speech is unintelligible. Raises a ``speech_recognition.RequestError`` exception if the speech recognition operation failed, if the key isn't valid, or if there is no internet connection.
        """
        assert isinstance(audio_data, AudioData), "``audio_data`` must be audio data"
        assert key is None or isinstance(key, str), "``key`` must be ``None`` or a string"
        assert isinstance(language, str), "``language`` must be a string"

        flac_data = audio_data.get_flac_data(
            convert_rate=None if audio_data.sample_rate >= 8000 else 8000,  # audio samples must be at least 8 kHz
            convert_width=2  # audio samples must be 16-bit
        )
        if key is None: key = "AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw"
        url = "http://www.google.com/speech-api/v2/recognize?{}".format(urlencode({
            "client": "chromium",
            "lang": language,
            "key": key,
        }))
        request = Request(url, data=flac_data,
                          headers={"Content-Type": "audio/x-flac; rate={}".format(audio_data.sample_rate)})

        # obtain audio transcription results
        try:
            response = urlopen(request, timeout=self.operation_timeout)
        except HTTPError as e:
            raise RequestError("recognition request failed: {}".format(e.reason))
        except URLError as e:
            raise RequestError("recognition connection failed: {}".format(e.reason))
        response_text = response.read().decode("utf-8")

        # ignore any blank blocks
        actual_result = []
        for line in response_text.split("\n"):
            if not line: continue
            result = json.loads(line)["result"]
            if len(result) != 0:
                actual_result = result[0]
                break

        # return results
        if show_all: return actual_result
        # if not isinstance(actual_result, dict) or len(actual_result.get("alternative", [])) == 0: raise UnknownValueError()
        if not isinstance(actual_result, dict) or len(actual_result.get("alternative", [])) == 0: return 0

        if "confidence" in actual_result["alternative"]:
            # return alternative with highest confidence score
            best_hypothesis = max(actual_result["alternative"], key=lambda alternative: alternative["confidence"])
        else:
            # when there is no confidence available, we arbitrarily choose the first hypothesis.
            best_hypothesis = actual_result["alternative"][0]
        if "transcript" not in best_hypothesis: raise UnknownValueError()
        return best_hypothesis["transcript"]

    def listen(self, source, timeout=None, phrase_time_limit=None, snowboy_configuration=None):
        """
        Records a single phrase from ``source`` (an ``AudioSource`` instance) into an ``AudioData`` instance, which it returns.

        This is done by waiting until the audio has an energy above ``recognizer_instance.energy_threshold`` (the user has started speaking), and then recording until it encounters ``recognizer_instance.pause_threshold`` seconds of non-speaking or there is no more audio input. The ending silence is not included.

        The ``timeout`` parameter is the maximum number of seconds that this will wait for a phrase to start before giving up and throwing an ``speech_recognition.WaitTimeoutError`` exception. If ``timeout`` is ``None``, there will be no wait timeout.

        The ``phrase_time_limit`` parameter is the maximum number of seconds that this will allow a phrase to continue before stopping and returning the part of the phrase processed before the time limit was reached. The resulting audio will be the phrase cut off at the time limit. If ``phrase_timeout`` is ``None``, there will be no phrase time limit.

        The ``snowboy_configuration`` parameter allows integration with `Snowboy <https://snowboy.kitt.ai/>`__, an offline, high-accuracy, power-efficient hotword recognition engine. When used, this function will pause until Snowboy detects a hotword, after which it will unpause. This parameter should either be ``None`` to turn off Snowboy support, or a tuple of the form ``(SNOWBOY_LOCATION, LIST_OF_HOT_WORD_FILES)``, where ``SNOWBOY_LOCATION`` is the path to the Snowboy root directory, and ``LIST_OF_HOT_WORD_FILES`` is a list of paths to Snowboy hotword configuration files (`*.pmdl` or `*.umdl` format).

        This operation will always complete within ``timeout + phrase_timeout`` seconds if both are numbers, either by returning the audio data, or by raising a ``speech_recognition.WaitTimeoutError`` exception.
        """
        assert isinstance(source, AudioSource), "Source must be an audio source"
        assert source.stream is not None, "Audio source must be entered before listening, see documentation for ``AudioSource``; are you using ``source`` outside of a ``with`` statement?"
        assert self.pause_threshold >= self.non_speaking_duration >= 0
        if snowboy_configuration is not None:
            assert os.path.isfile(os.path.join(snowboy_configuration[0], "snowboydetect.py")), "``snowboy_configuration[0]`` must be a Snowboy root directory containing ``snowboydetect.py``"
            for hot_word_file in snowboy_configuration[1]:
                assert os.path.isfile(hot_word_file), "``snowboy_configuration[1]`` must be a list of Snowboy hot word configuration files"

        seconds_per_buffer = float(source.CHUNK) / source.SAMPLE_RATE
        pause_buffer_count = int(math.ceil(self.pause_threshold / seconds_per_buffer))  # number of buffers of non-speaking audio during a phrase, before the phrase should be considered complete
        phrase_buffer_count = int(math.ceil(self.phrase_threshold / seconds_per_buffer))  # minimum number of buffers of speaking audio before we consider the speaking audio a phrase
        non_speaking_buffer_count = int(math.ceil(self.non_speaking_duration / seconds_per_buffer))  # maximum number of buffers of non-speaking audio to retain before and after a phrase

        # read audio input for phrases until there is a phrase that is long enough
        elapsed_time = 0  # number of seconds of audio read
        buffer = b""  # an empty buffer means that the stream has ended and there is no data left to read
        while True:
            frames = collections.deque()

            if snowboy_configuration is None:
                # store audio input until the phrase starts
                while True:
                    # handle waiting too long for phrase by raising an exception
                    elapsed_time += seconds_per_buffer
                    if timeout and elapsed_time > timeout:
                        raise WaitTimeoutError("listening timed out while waiting for phrase to start")

                    buffer = source.stream.read(source.CHUNK)
                    if len(buffer) == 0: break  # reached end of the stream
                    frames.append(buffer)
                    if len(frames) > non_speaking_buffer_count:  # ensure we only keep the needed amount of non-speaking buffers
                        frames.popleft()

                    # detect whether speaking has started on audio input
                    energy = audioop.rms(buffer, source.SAMPLE_WIDTH)  # energy of the audio signal
                    if energy > self.energy_threshold: break

                    # dynamically adjust the energy threshold using asymmetric weighted average
                    if self.dynamic_energy_threshold:
                        damping = self.dynamic_energy_adjustment_damping ** seconds_per_buffer  # account for different chunk sizes and rates
                        target_energy = energy * self.dynamic_energy_ratio
                        self.energy_threshold = self.energy_threshold * damping + target_energy * (1 - damping)
            else:
                # read audio input until the hotword is said
                snowboy_location, snowboy_hot_word_files = snowboy_configuration
                buffer, delta_time = self.snowboy_wait_for_hot_word(snowboy_location, snowboy_hot_word_files, source, timeout)
                elapsed_time += delta_time
                if len(buffer) == 0: break  # reached end of the stream
                frames.append(buffer)

            # read audio input until the phrase ends
            pause_count, phrase_count = 0, 0
            phrase_start_time = elapsed_time
            while True:
                # handle phrase being too long by cutting off the audio
                elapsed_time += seconds_per_buffer
                if phrase_time_limit and elapsed_time - phrase_start_time > phrase_time_limit:
                    break

                buffer = source.stream.read(source.CHUNK)
                if len(buffer) == 0: break  # reached end of the stream
                frames.append(buffer)
                phrase_count += 1

                # check if speaking has stopped for longer than the pause threshold on the audio input
                energy = audioop.rms(buffer, source.SAMPLE_WIDTH)  # unit energy of the audio signal within the buffer
                if energy > self.energy_threshold:
                    pause_count = 0
                else:
                    pause_count += 1
                if pause_count > pause_buffer_count:  # end of the phrase
                    break

            # check how long the detected phrase is, and retry listening if the phrase is too short
            phrase_count -= pause_count  # exclude the buffers for the pause before the phrase
            if phrase_count >= phrase_buffer_count or len(buffer) == 0: break  # phrase is long enough or we've reached the end of the stream, so stop listening

        # obtain frame data
        for i in range(pause_count - non_speaking_buffer_count): frames.pop()  # remove extra non-speaking frames at the end
        frame_data = b"".join(frames)

        return AudioData(frame_data, source.SAMPLE_RATE, source.SAMPLE_WIDTH)


"""
  Demonstration of running PySimpleGUI code in repl.it!

  This demo program shows all of the PySimpleGUI Elements that are available for use.  New ones are being added daily.

  Now you can run your PySimpleGUI code in these ways:
  1. tkinter
  2. Qt (pyside2)
  3. WxPython
  4. Web Browser (Remi)
  5. repl.it (Remi)

  You can use repl.it to develop, test and share your code.
  If you want to run your GUI on tkinter, then change the import statement to "import PySimpleGUI".  To run it on WxPython, change it to "import PySimpleGUIWx".

  repl.it opens up an entirely new way of demonstrating problems, solutions, bugs, etc, in a way that doesn't require anything but a web browser.  No need to install a GUI package like tkinter.  No need to install Python for that matter.  Just open the repl link and have fun.

"""
print('Starting up...')

r = Recognizer2()

sg.ChangeLookAndFeel('LightGreen')  # set the overall color scheme
# ------ Column Definition ------ #
column1 = [[sg.Text('Column 1', background_color='#F7F3EC', justification='center', size=(10, 1))],
           [sg.Spin(values=('Spin Box 1', '2', '3'), initial_value='Spin Box 1')],
           [sg.Spin(values=('Spin Box 1', '2', '3'), initial_value='Spin Box 2')],
           [sg.Spin(values=('Spin Box 1', '2', '3'), initial_value='Spin Box 3')]]
# The GUI layout
layout = [
    [sg.Text('Speech Recognition Mini-Application', size=(100, 1), font=('Comic sans ms', 20),
             text_color='red')],
    [sg.Text('This program has been running for... ', size=(30, 1)), sg.Text('', size=(30, 1), key='_DATE_')],
    [sg.Frame('Speech to Text Output',[[sg.Multiline('', size=(80, 8), key='_STO_', font='Courier 12')]]),
     sg.Frame('Configuration',[[
         sg.InputCombo(['Bahasa Indonesia', 'Bahasa Melayu', 'Chinese', 'English', 'Japanese', 'Korean'], default_value='English',
                       auto_size_text=True, key='lang'),
         sg.Button('Speech')]])],
    [sg.Text('', size=(30, 1), key='guide')],
    # [sg.Input('Single Line Input', do_not_clear=True, enable_events=True, size=(30, 1))],
    # [sg.Multiline('Multiline Input', do_not_clear=True, size=(40, 4), enable_events=True)],
    # [sg.MultilineOutput('Multiline Output', size=(80, 8), key='_MULTIOUT_', font='Courier 12')],
    # [sg.Checkbox('Checkbox 1', enable_events=True, key='_CB1_'),
    #  sg.Checkbox('Checkbox 2', default=True, enable_events=True, key='_CB2_')],
    # [sg.Combo(values=['Combo 1', 'Combo 2', 'Combo 3'], default_value='Combo 2', key='_COMBO_', enable_events=True,
    #           readonly=False, tooltip='Combo box', disabled=False, size=(12, 1))],
    # [sg.Listbox(values=('Listbox 1', 'Listbox 2', 'Listbox 3'), size=(10, 3), enable_events=True, key='_LIST_')],
    # [sg.Slider((1, 100), default_value=80, key='_SLIDER_', visible=True, enable_events=True)],
    # [sg.Spin(values=(1, 2, 3), initial_value=2, size=(4, 1))],
]

# create the "Window"
window = sg.Window('My PySimpleGUIWeb Window',
                   default_element_size=(10, 1),
                   font='Helvetica 18',
                   ).Layout(layout)

start_time = datetime.datetime.now()
# event, values = window.Read()  # read with a timeout of 10 ms
#  The "Event loop" where all events are read and processed (button clicks, etc)
listText = []
while True:

    event, values = window.Read()  # read with a timeout of 10 ms
    if event != sg.TIMEOUT_KEY:  # if got a real event, print the info
        print(event, values)
        # also output the information into a scrolling box in the window
        # window.Element('_MULTIOUT_').Update(str(event) + '\n' + str(values), append=True)
    # if the "Exit" button is clicked or window is closed then exit the event loop
    if event in (None, 'Exit'):
        break
    if event in ('Speech'):
        print("event: ", event, "value: ", values)
        print(values['lang'])
        # By default, it is set as English
        # Reference for the language: https://cloud.google.com/speech-to-text/docs/languages
        language = "en-US"
        if values['lang'] == "Bahasa Indonesia":
            language = "id-ID"
        elif values['lang'] == "Bahasa Melayu":
            language = "ms-MY"
        elif values['lang'] == "Chinese":
            language = "zh"
        elif values['lang'] == "English":
            language = "en-US"
        elif values['lang'] == "Japanese":
            language = "ja-JP"
        elif values['lang'] == "Korean":
            language = "ko-KR"
        with sr.Microphone() as source:
            print(source)
            window.Element('guide').Update("Please start your speech.")
            audio = r.listen(source)
            print('Done!')

        try:
            window.Element('guide').Update("Done.")
            text = r.recognize_google(audio, language=language)
            if text == 0:
                print("no text")
                # window.Element('_STO_').Update("\n".join(listText), append=True)
                # window.Element('_STO_').Update(text, append=True)
            else:
                print(text)
                listText.append(text)
                # window.Element('_STO_').Update("\n".join(text), append=True)
                window.Element('_STO_').Update(text+"\n", append=True)
        except:
            print("Error of receiving your speech")
            r = Recognizer2()
            window.Element('guide').Update("No speech has found.")
            # window.Element('_STO_').Update("\n".join(listText), append=True)

    # Output the "uptime" statistic to a text field in the window
    window.Element('_DATE_').Update(str(datetime.datetime.now() - start_time))


# Exiting the program
# window.Close()  # be sure and close the window before trying to exit the program
print('Completed shutdown')

