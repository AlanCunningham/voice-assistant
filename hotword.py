# import snowboy.snowboydecoder as snowboydecoder
import lights
import bash_scripts
from sam import Sam
import os
import thread
import ConfigParser
import audio_helper
import speech

interrupted = False
previous_command = ''
sam = ''
hotword_detector = ''


def init():
    config = ConfigParser.ConfigParser()
    config.read('config.py')
    # Snowboy hotword has a specific Raspberry Pi library - import if we're
    # running on a Pi
    raspberry_pi = config.get('snowboy', 'raspberry_pi')
    if raspberry_pi == 'True':
        import snowboy_pi.snowboydecoder as snowboydecoder
    else:
        import snowboy_linux.snowboydecoder as snowboydecoder

    global sam
    hotword_models = []
    callbacks = []
    hotword_dict = {}
    main_model_folder = 'hotword_models'
    model_dir = os.listdir('hotword_models')
    sam = Sam()

    # Each voice model is stored in a category folder
    # e.g. hotword_models/weather/whats_the_weather_like.pdml
    # This section finds all categories and models to create a dictionary
    # of commands.
    for category in model_dir:
        cat = os.listdir(main_model_folder + '/' + category)
        # Model inside this category
        for model in cat:
            split_model = model.split('.')[0]
            file_path = main_model_folder + '/' + category + '/' + model
            hotword_dict[split_model] = {
                'category': category,
                'hotword': split_model,
                'file': file_path
            }
            hotword_models.append(file_path)
            callbacks.append(
                lambda model=model: thread.start_new_thread(
                    hotword_callback,
                    (hotword_dict[model.split('.')[0]],)
                )
            )

    sensitivity = [0.4]*len(hotword_models)

    # Setup hotword detector
    global hotword_detector
    hotword_detector = snowboydecoder.HotwordDetector(
        hotword_models,
        sensitivity=sensitivity,
        audio_gain=1
    )

    hotword_detector.start(
        detected_callback=callbacks,
        interrupt_check=interrupt_callback,
        sleep_time=0.003,
    )


# Commands that can be called without initially calling "Okay <assistant>"
# Checks against the keyword's category so we can have multiple keywords
# per category.
def hotword_callback(keyword):
    global hotword_detector
    print('Hotword: %s' % keyword['hotword'])
    play_confirmation_sound()

    # Lights
    if keyword['category'] == 'lights':
        lights.toggle_lights()
    elif keyword['category'] == 'turn_everything_off':
        lights.toggle_lights()
        bash_scripts.touchscreen_display(False)
    elif keyword['category'] == 'dim_the_lights':
        lights.dim_lights()
    elif keyword['category'] == 'full_brightness':
        lights.full_brightness()

    # Bash scripts
    elif keyword['category'] == 'computer':
        bash_scripts.wake_computer()
    elif keyword['category'] == 'screen_on':
        bash_scripts.touchscreen_display(True)

    # Second level responses
    elif keyword['category'] == 'activation':
        # Stop the hotword detector to free up the microphone
        # for normal speech recognition
        hotword_detector.terminate()
        sam.second_level_commands()
        # When finished, restart the hotword detector
        init()

    # Cancel previous commands
    elif keyword['category'] == 'cancel':
        audio_helper.stop_audio()


def play_confirmation_sound():
    audio_helper.play_audio('audio/start.wav')

def signal_handler(signal, frame):
    global interrupted
    interrupted = True


def interrupt_callback():
    global interrupted
    return interrupted


if __name__ == '__main__':
    init()
