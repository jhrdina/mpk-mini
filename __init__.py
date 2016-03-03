#Embedded file name: /Users/versonator/Jenkins/live/output/mac_64_static/Release/python-bundle/MIDI Remote Scripts/Launchkey/__init__.py
from MPK_mini_hero import MPK_mini_hero
from _Framework.Capabilities import *

def get_capabilities():
    return {CONTROLLER_ID_KEY: controller_id(vendor_id=2536, product_ids=[124], model_name='MPK mini'),
     PORTS_KEY: [inport(props=[NOTES_CC]),
                 inport(props=[NOTES_CC, SCRIPT]),
                 outport(props=[NOTES_CC]),
                 outport(props=[NOTES_CC, SCRIPT])]}


def create_instance(c_instance):
    return MPK_mini_hero(c_instance)