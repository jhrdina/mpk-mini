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
IS_MOMENTARY = True

def make_button(cc_no, name):
    button = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 1, cc_no)
    button.name = name
    return button


def make_configurable_button(cc_no, name, type = MIDI_NOTE_TYPE, channel = 1):
    button = ConfigurableButtonElement(IS_MOMENTARY, type, channel, cc_no)
    button.name = name
    return button

def make_toggle_button(cc_no, name, channel = 1):
    button = ConfigurableButtonElement(False, MIDI_CC_TYPE, channel, cc_no)
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


class LaunchkeyControlFactory(object):

    def create_next_track_button(self):
        return make_button(107, 'Next_Track_Button')

    def create_prev_track_button(self):
        return make_button(106, 'Prev_Track_Button')

    def create_scene_launch_button(self):
        return make_configurable_button(102, 'Scene_Launch_Button', MIDI_CC_TYPE)

    def create_scene_stop_button(self):
        return make_configurable_button(110, 'Scene_Stop_Button', MIDI_CC_TYPE)

    def create_clip_launch_button(self, index):
        return make_configurable_button(36 + index, 'Clip_Launch_%d' % index)

    def create_clip_stop_button(self, index):
        return make_configurable_button(44 + index, 'Clip_Stop_%d' % index)

    def create_clip_undo_button(self):
        return make_button(105, 'Clip_Delete_Button')

    def create_clip_duplicate_button(self):
        return make_toggle_button(23, 'Clip_Duplicate_Button')


class MPK_mini_hero(ControlSurface):
    """ Script for Novation's Launchkey 25/49/61 keyboards """

    def __init__(self, c_instance, control_factory = LaunchkeyControlFactory(), identity_response = SIZE_RESPONSE):
        ControlSurface.__init__(self, c_instance)
        self._control_factory = control_factory
        self._identity_response = identity_response
        with self.component_guard():
            self.set_pad_translations(PAD_TRANSLATIONS)
            self._device_selection_follows_track_selection = True
            self._suggested_input_port = 'MPK mini'
            self._suggested_output_port = 'MPK mini'
            self._current_midi_map = None

            self._setup_session()
            self._setup_transport()
            # self._setup_device()
            self._setup_navigation()
            self._setup_clipslot()
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
        self._current_midi_map = None
        self._transport_view_modes = None
        self._send_midi(LED_FLASHING_OFF)
        self._send_midi(LIVE_MODE_OFF)

    def build_midi_map(self, midi_map_handle):
        self._current_midi_map = midi_map_handle
        ControlSurface.build_midi_map(self, midi_map_handle)

    def _setup_session(self):
        scene_launch_button = self._control_factory.create_scene_launch_button()
        scene_stop_button = self._control_factory.create_scene_stop_button()
        self._session = SessionComponent(8, 0)
        self._session.name = 'Session_Control'
        self._session.selected_scene().name = 'Selected_Scene'
        self._session.selected_scene().set_launch_button(scene_launch_button)
        self._session.set_stop_all_clips_button(scene_stop_button)
        clip_launch_buttons = []
        clip_stop_buttons = []
        for index in range(8):
            clip_launch_buttons.append(self._control_factory.create_clip_launch_button(index))
            clip_stop_buttons.append(self._control_factory.create_clip_stop_button(index))
            clip_slot = self._session.selected_scene().clip_slot(index)
            
            clip_slot.set_launch_button(clip_launch_buttons[-1])
            clip_slot.name = 'Selected_Clip_Slot_' + str(index)

        self._session.set_stop_track_clip_buttons(tuple(clip_stop_buttons))

    def _setup_clipslot(self):
        clip_undo_button = self._control_factory.create_clip_undo_button()
        clip_duplicate_button = self._control_factory.create_clip_duplicate_button()

        self._do_undo.subject = clip_undo_button;


        # self._clipslot = ClipSlotComponent()
        # self._clipslot.name = 'Selected_Clip_Slot'
        # self._clipslot.set_delete_button(clip_undo_button)
        # self._clipslot.set_duplicate_button(clip_duplicate_button)
        # self._clipslot.update()

    @subject_slot('value')
    def _do_undo(self, value):
        if value:
            if self.song().can_undo == 1:
                self.song().undo()
                self.show_message(str('UNDO'))

    def _setup_transport(self):
        rwd_button = make_button(108, 'Rwd_Button')
        ffwd_button = make_button(104, 'FFwd_Button')
        stop_button = make_button(111, 'Stop_Button')
        play_button = make_button(112, 'Play_Button')
        loop_button = make_button(113, 'Loop_Button')
        rec_button = make_button(114, 'Record_Button')
        overdub_button = make_button(103, 'Session_Overdub_Button')

        transport = TransportComponent()
        transport.name = 'Transport'
        transport.set_stop_button(stop_button)
        transport.set_play_button(play_button)
        transport.set_record_button(rec_button)
        transport.set_loop_button(loop_button)
        self._transport_view_modes = TransportViewModeSelector(transport, self._session, ffwd_button, rwd_button)
        self._transport_view_modes.name = 'Transport_View_Modes'

        session_recording = SessionRecordingComponent(ClipCreator(), ViewControlComponent(), name='Session_Recording', is_enabled=False, layer=Layer(record_button=overdub_button))
        session_recording.set_enabled(True)

    def _setup_device(self):
        encoders = [ make_encoder(21 + index, 'Device_Control_%d' % index) for index in xrange(8) ]
        self._encoders = tuple(encoders)
        device = DeviceComponent()
        device.name = 'Device_Component'
        self.set_device_component(device)
        device.set_parameter_controls(self._encoders)

    def _setup_navigation(self):
        self._next_track_button = self._control_factory.create_next_track_button()
        self._prev_track_button = self._control_factory.create_prev_track_button()
        self._session_navigation = SessionNavigationComponent(name='Session_Navigation')
        self._session_navigation.set_next_track_button(self._next_track_button)
        self._session_navigation.set_prev_track_button(self._prev_track_button)

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