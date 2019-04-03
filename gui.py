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

