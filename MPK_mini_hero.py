#Embedded file name: /Users/versonator/Jenkins/live/output/mac_64_static/Release/python-bundle/MIDI Remote Scripts/Launchkey/Launchkey.py
from __future__ import with_statement
import Live
from _Framework.Layer import Layer
from _Framework.ControlSurface import ControlSurface
from _Framework.InputControlElement import InputControlElement, MIDI_CC_TYPE, MIDI_NOTE_TYPE
from _Framework.SliderElement import SliderElement
from _Framework.ButtonElement import ButtonElement
from _Framework.EncoderElement import EncoderElement
from _Framework.DeviceComponent import DeviceComponent
from _Framework.SessionComponent import SessionComponent
from _Framework.SessionRecordingComponent import SessionRecordingComponent
from _Framework.ClipCreator import ClipCreator
from _Framework.ViewControlComponent import ViewControlComponent
from _Framework.TransportComponent import TransportComponent
from _Framework.ClipSlotComponent import ClipSlotComponent
from _Framework.SubjectSlot import subject_slot
from Launchpad.ConfigurableButtonElement import ConfigurableButtonElement
from SessionNavigationComponent import SessionNavigationComponent
from TransportViewModeSelector import TransportViewModeSelector
from SpecialMixerComponent import SpecialMixerComponent
from consts import *

# Const values
IS_MOMENTARY = True

PAD_MODE_CC = 0
PAD_MODE_NOTES = 1

# User settings
PADS_CHANNEL = 1
PADS_CC_START = 101
PADS_NOTES_START = 36
SCENES_CHANNEL = 3
SCENES_NOTES_START = 48

# Fixed
PADS_LED_START = 9

# TODO: Get rid of me
def make_configurable_button(cc_no, name, type = MIDI_NOTE_TYPE, channel = 1):
    button = ConfigurableButtonElement(IS_MOMENTARY, type, channel, cc_no)
    button.name = name
    return button

def make_pad_button(pad_mode, pad_no, name):
    if pad_mode is PAD_MODE_CC:
        button = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, PADS_CHANNEL, PADS_CC_START + pad_no)
    else:
        button = ButtonElement(IS_MOMENTARY, MIDI_NOTE_TYPE, PADS_CHANNEL, PADS_NOTES_START + pad_no)
    
    button.name = name
    return button

def make_scene_button(note_no, name):
    button = ButtonElement(IS_MOMENTARY, MIDI_NOTE_TYPE, SCENES_CHANNEL, SCENES_NOTES_START + note_no)
    button.name = name
    return button


def make_encoder(cc_no, name):
    encoder = EncoderElement(MIDI_CC_TYPE, 0, cc_no, Live.MidiMap.MapMode.absolute)
    encoder.set_feedback_delay(-1)
    encoder.name = name
    return encoder


def make_slider(cc_no, name):
    slider = SliderElement(MIDI_CC_TYPE, 0, cc_no)
    slider.set_feedback_delay(-1)
    slider.name = name
    return slider

class MPK_mini_hero(ControlSurface):
    """ Script for Novation's Launchkey 25/49/61 keyboards """

    def __init__(self, c_instance, identity_response = SIZE_RESPONSE):
        ControlSurface.__init__(self, c_instance)
        self._identity_response = identity_response
        with self.component_guard():
            self.set_pad_translations(PAD_TRANSLATIONS)
            self._device_selection_follows_track_selection = True
            self._suggested_input_port = 'MPK mini'
            self._suggested_output_port = 'MPK mini'

            self._setup_buttons()
            self._setup_components()

            for component in self.components:
                component.set_enabled(True) # Puvodne False

    def refresh_state(self):
        ControlSurface.refresh_state(self)
        
        # for val in range(127):
        #     self.schedule_message(2, self._send_midi, (144, val, 0))
            
        # self.schedule_message(3, self._send_midi, (144, 9, 127))

    def handle_sysex(self, midi_bytes):
        self._send_midi(LED_FLASHING_ON)
        self._update_mixer_offset()
        for control in self.controls:
            if isinstance(control, InputControlElement):
                control.clear_send_cache()

        for component in self.components:
            component.set_enabled(True)

        self.request_rebuild_midi_map()

    def disconnect(self):
        ControlSurface.disconnect(self)

        self._encoders = None
        self._transport_view_modes = None
        self._send_midi(LED_FLASHING_OFF)
        self._send_midi(LIVE_MODE_OFF)

    def _setup_buttons(self):
        # Pads CC Mode
        self._scene_launch_button = make_pad_button(PAD_MODE_CC, 1, 'Scene_Launch_Button')
        self._overdub_button = make_pad_button(PAD_MODE_CC, 2, 'Session_Overdub_Button')
        self._ffwd_button = make_pad_button(PAD_MODE_CC, 3, 'FFwd_Button')
        self._clip_undo_button = make_pad_button(PAD_MODE_CC, 4, 'Clip_Undo_Button')
        self._prev_track_button = make_pad_button(PAD_MODE_CC, 5, 'Prev_Track_Button')
        self._next_track_button = make_pad_button(PAD_MODE_CC, 6, 'Next_Track_Button')
        self._rwd_button = make_pad_button(PAD_MODE_CC, 7, 'Rwd_Button')
        self._scene_stop_button = make_pad_button(PAD_MODE_CC, 9, 'Scene_Stop_Button')
        self._stop_button = make_pad_button(PAD_MODE_CC, 10, 'Stop_Button')
        self._play_button = make_pad_button(PAD_MODE_CC, 11, 'Play_Button')
        self._loop_button = make_pad_button(PAD_MODE_CC, 12, 'Loop_Button')
        self._rec_button = make_pad_button(PAD_MODE_CC, 13, 'Record_Button')

        # Pads Notes Mode
        self._clip_launch_buttons = [ make_pad_button(PAD_MODE_NOTES, index, 'Clip_Launch_%d' % index) for index in xrange(8) ]
        self._clip_stop_buttons = [ make_pad_button(PAD_MODE_NOTES, 8 + index, 'Clip_Stop_%d' % index) for index in xrange(8) ]

        # Encoders

        self._encoders = tuple([ make_encoder(21 + index, 'Device_Control_%d' % index) for index in xrange(8) ])

        # Scenes

        self._scene_launch_buttons = []
        for key_no in [0,2,4,5,7,9,11,  12,14,16,17,19,21,23,  24]:
            self._scene_launch_buttons.append(make_scene_button(key_no, 'Scene_Launch_%d' % key_no))

    def _setup_components(self):
        
        # Session

        self._session = SessionComponent(8, len(self._scene_launch_buttons))
        self._session.name = 'Session_Control'
        self._session.selected_scene().name = 'Selected_Scene'
        self._session.selected_scene().set_launch_button(self._scene_launch_button)
        self._session.set_stop_all_clips_button(self._scene_stop_button)

        for index in range(8):
            clip_slot = self._session.selected_scene().clip_slot(index)
            clip_slot.set_launch_button(self._clip_launch_buttons[index])
            clip_slot.name = 'Selected_Clip_Slot_' + str(index)

        self._session.set_stop_track_clip_buttons(tuple(self._clip_stop_buttons))

        # Undo

        self._do_undo.subject = self._clip_undo_button;

        # Transport

        transport = TransportComponent()
        transport.name = 'Transport'
        transport.set_stop_button(self._stop_button)
        transport.set_play_button(self._play_button)
        transport.set_record_button(self._rec_button)
        transport.set_loop_button(self._loop_button)

        self._transport_view_modes = TransportViewModeSelector(transport, self._session, self._ffwd_button, self._rwd_button)
        self._transport_view_modes.name = 'Transport_View_Modes'

        session_recording = SessionRecordingComponent(ClipCreator(), ViewControlComponent(), name='Session_Recording', is_enabled=False, layer=Layer(record_button=self._overdub_button))

        # Device

        # device = DeviceComponent()
        # device.name = 'Device_Component'
        # self.set_device_component(device)
        # device.set_parameter_controls(self._encoders)

        # Navigation

        self._session_navigation = SessionNavigationComponent(name='Session_Navigation')
        self._session_navigation.set_next_track_button(self._next_track_button)
        self._session_navigation.set_prev_track_button(self._prev_track_button)

        # Playing
        # self._session.set_scene_launch_buttons(tuple(self._scene_launch_buttons))
        for index in range(len(self._scene_launch_buttons)):
            scene = self._session.scene(index)
            scene.set_launch_button(self._scene_launch_buttons[index])

    @subject_slot('value')
    def _do_undo(self, value):
        if value:
            if self.song().can_undo == 1:
                self.song().undo()
                self.show_message(str('UNDO'))

    def _dummy_listener(self, value):
        pass

    def _on_selected_track_changed(self):
        ControlSurface._on_selected_track_changed(self)
        self._update_mixer_offset()

    def _update_mixer_offset(self):
        all_tracks = self._session.tracks_to_use()
        selected_track = self.song().view.selected_track
        num_strips = self._session.width()
        if selected_track in all_tracks:
            track_index = list(all_tracks).index(selected_track)
            new_offset = track_index - track_index % num_strips
            self._session.set_offsets(new_offset, self._session.scene_offset())