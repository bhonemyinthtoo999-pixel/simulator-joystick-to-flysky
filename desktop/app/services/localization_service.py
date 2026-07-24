from __future__ import annotations

from dataclasses import replace
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractButton,
    QComboBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QWidget,
)

from .readiness_service import ReadinessItem, ReadinessReport


SUPPORTED_LANGUAGES: tuple[tuple[str, str], ...] = (
    ("en", "English"),
    ("my", "မြန်မာ"),
)


def normalize_language(value: object) -> str:
    clean = str(value or "en").strip().casefold()
    return "my" if clean in {"my", "mm", "burmese", "myanmar", "မြန်မာ"} else "en"


NAVIGATION_LABELS: dict[str, dict[str, str]] = {
    "Dashboard": {"my": "ပင်မစာမျက်နှာ"},
    "Joystick Monitor": {"my": "Joystick ကြည့်ရှုရန်"},
    "Channel Mapping": {"my": "Channel ချိတ်ဆက်မှု"},
    "Calibration": {"my": "ချိန်ညှိမှု"},
    "Profiles": {"my": "Profile များ"},
    "Adapter / Firmware": {"my": "Adapter / Firmware"},
    "Diagnostics": {"my": "စစ်ဆေးချက်များ"},
    "Settings": {"my": "ဆက်တင်များ"},
}


MYANMAR_TEXT: dict[str, str] = {
    # Main product navigation and dashboard.
    "Simulator Joystick to FlySky": "Simulator Joystick မှ FlySky သို့",
    "USB flight controls → safe AETR mapping → detected adapter → FlySky trainer port": "USB flight control → လုံခြုံသော AETR ချိတ်ဆက်မှု → adapter → FlySky trainer port",
    "SYSTEM READINESS": "စနစ် အသင့်ဖြစ်မှု",
    "CHECKING SETUP…": "ဆက်တင်များ စစ်ဆေးနေသည်…",
    "Detecting controls and adapter hardware.": "Control များနှင့် adapter hardware ကို ရှာဖွေနေသည်။",
    "Continue setup": "ဆက်လက်ပြင်ဆင်ရန်",
    "Setup guide": "စတင်ပြင်ဆင်မှု လမ်းညွှန်",
    "Adapter board": "Adapter board",
    "Scanning…": "ရှာဖွေနေသည်…",
    "Looking for an Arduino or ESP32 serial adapter": "Arduino သို့မဟုတ် ESP32 serial adapter ကို ရှာဖွေနေသည်",
    "Flight controls": "လေယာဉ်ထိန်းချုပ်ကိရိယာများ",
    "Stick, throttle, pedals and auxiliary USB devices": "Stick၊ throttle၊ pedal နှင့် အခြား USB ကိရိယာများ",
    "Active profile": "လက်ရှိ profile",
    "Default": "မူလ",
    "Multi-device calibration, mapping and failsafe settings": "ကိရိယာများစွာအတွက် calibration၊ mapping နှင့် failsafe ဆက်တင်များ",
    "Setup checklist": "ပြင်ဆင်မှု စစ်ဆေးစာရင်း",
    "Live RC channel output": "လက်ရှိ RC channel output",
    "Failsafe armed: output is clamped to the active profile limits.": "Failsafe အသင့်ဖြစ်သည်။ Output ကို လက်ရှိ profile သတ်မှတ်ချက်အတွင်း ကန့်သတ်ထားသည်။",
    "READY": "အသင့်ဖြစ်ပြီ",
    "ACTION NEEDED": "လုပ်ဆောင်ရန်လိုသည်",
    "FLIGHT BRIDGE STATUS": "Flight bridge အခြေအနေ",
    "SETUP ASSISTANT": "ပြင်ဆင်မှု အကူအညီ",
    "READY TO USE": "အသုံးပြုရန် အသင့်ဖြစ်ပြီ",
    "SETUP REQUIRED": "ပြင်ဆင်ရန် လိုအပ်သည်",

    # Live transmitter monitor.
    "Live transmitter monitor": "လက်ရှိ transmitter ကြည့်ရှုမှု",
    "Read-only view of the final AETR values. Opening this monitor never disconnects Arduino or interrupts FlySky trainer PPM.": "နောက်ဆုံး AETR တန်ဖိုးများကိုသာ ကြည့်ရှုနိုင်သည်။ ဤ monitor ကိုဖွင့်ခြင်းကြောင့် Arduino ချိတ်ဆက်မှု သို့မဟုတ် FlySky trainer PPM မရပ်ပါ။",
    "Connect and identify a physical adapter to view the live trainer output path.": "လက်ရှိ trainer output ကိုကြည့်ရန် physical adapter ကိုချိတ်ပြီး identify လုပ်ပါ။",
    "AETR LIVE": "AETR လက်ရှိ",
    "THROTTLE / YAW": "THROTTLE / YAW",
    "PITCH / ROLL": "PITCH / ROLL",
    "Mode 2 visualization • final output sent to the active adapter": "Mode 2 ပုံရိပ် • active adapter ဆီပို့နေသော နောက်ဆုံး output",
    "LIVE HARDWARE": "HARDWARE လက်ရှိ",
    "FAILSAFE": "FAILSAFE",
    "OUTPUT PAUSED": "OUTPUT ခဏရပ်ထားသည်",
    "OFFLINE SIMULATOR": "OFFLINE SIMULATOR",
    "OFFLINE": "ချိတ်ဆက်မထားပါ",

    # Setup wizard.
    "Set up Simulator Joystick to FlySky": "Simulator Joystick မှ FlySky သို့ ပြင်ဆင်ရန်",
    "Get ready to fly": "အသုံးပြုရန် ပြင်ဆင်မည်",
    "Connect your controls and adapter, install firmware, calibrate, map AETR and verify safety.": "Control နှင့် adapter ကိုချိတ်ပါ၊ firmware တင်ပါ၊ calibration နှင့် AETR mapping လုပ်ပြီး လုံခြုံရေးစစ်ဆေးပါ။",
    "Welcome": "ကြိုဆိုပါတယ်",
    "Adapter firmware": "Adapter firmware",
    "Calibration & mapping": "Calibration နှင့် mapping",
    "Ready check": "အသင့်ဖြစ်မှု စစ်ဆေးရန်",
    "Setup progress is saved automatically.": "ပြင်ဆင်မှုအခြေအနေကို အလိုအလျောက်သိမ်းထားသည်။",
    "Back": "နောက်သို့",
    "Next": "ရှေ့သို့",
    "Finish later": "နောက်မှဆက်မည်",
    "Finish setup": "ပြင်ဆင်မှု ပြီးဆုံးမည်",
    "This assistant turns the engineering setup into a short guided flow. You can leave and return without losing profiles or calibration.": "နည်းပညာဆိုင်ရာ ပြင်ဆင်မှုများကို အဆင့်လိုက်လမ်းညွှန်ပေးမည်။ ထွက်ပြီးပြန်ဝင်လည်း profile နှင့် calibration မပျောက်ပါ။",
    "What you will complete": "လုပ်ဆောင်မည့်အဆင့်များ",
    "No account is required. Joystick data, profiles and calibration stay on this computer.": "Account မလိုပါ။ Joystick data၊ profile နှင့် calibration များကို ဤကွန်ပျူတာထဲတွင်သာ သိမ်းထားသည်။",
    "Connect flight controls": "Flight control များကို ချိတ်ပါ",
    "Connect the stick, throttle and optional pedals directly to Windows. The app combines them into one AETR output.": "Stick၊ throttle နှင့် pedal များကို Windows သို့တိုက်ရိုက်ချိတ်ပါ။ App က ၎င်းတို့ကို AETR output တစ်ခုအဖြစ် ပေါင်းပေးမည်။",
    "Scanning USB controls…": "USB control များကို ရှာဖွေနေသည်…",
    "Open Joystick Monitor": "Joystick Monitor ဖွင့်ရန်",
    "Install adapter firmware": "Adapter firmware တင်ရန်",
    "For Arduino bridges the application can install the tested PPM firmware without Arduino IDE. Select the exact board and COM port before continuing.": "Arduino bridge အတွက် စမ်းသပ်ပြီးသော PPM firmware ကို Arduino IDE မလိုဘဲ တင်နိုင်သည်။ Board နှင့် COM port ကိုမှန်ကန်စွာရွေးပါ။",
    "No physical adapter identified yet.": "Physical adapter ကို မသိရှိရသေးပါ။",
    "Refresh COM ports": "COM port များ ပြန်ရှာရန်",
    "I confirmed the selected board and removed aircraft/motor power.": "ရွေးထားသော board မှန်ကန်ပြီး လေယာဉ်/မော်တာ power ဖြုတ်ထားကြောင်း အတည်ပြုသည်။",
    "Install firmware": "Firmware တင်ရန်",
    "Cancel installation": "တင်နေမှု ပယ်ဖျက်ရန်",
    "Firmware installation messages will appear here.": "Firmware တင်နေမှုစာများ ဤနေရာတွင် ပေါ်လာမည်။",
    "Open Adapter / Firmware page": "Adapter / Firmware စာမျက်နှာဖွင့်ရန်",
    "Calibrate and map AETR": "Calibration နှင့် AETR mapping လုပ်ရန်",
    "Calibrate each physical device separately, then assign Roll, Pitch, Throttle and Yaw. The setup assistant will update automatically.": "Physical device တစ်ခုစီကို သီးခြား calibration လုပ်ပြီး Roll၊ Pitch၊ Throttle နှင့် Yaw သတ်မှတ်ပါ။ အခြေအနေကို အလိုအလျောက် update လုပ်မည်။",
    "Calibration status is being checked.": "Calibration အခြေအနေကို စစ်ဆေးနေသည်။",
    "Mapping status is being checked.": "Mapping အခြေအနေကို စစ်ဆေးနေသည်။",
    "Open Calibration": "Calibration ဖွင့်ရန်",
    "Open Channel Mapping": "Channel Mapping ဖွင့်ရန်",
    "All required items must be ready before the setup can be marked complete. Hardware testing should still be done without propellers or motor power.": "လိုအပ်ချက်အားလုံး အသင့်ဖြစ်မှ ပြင်ဆင်မှုကိုပြီးဆုံးနိုင်သည်။ Hardware test ကို propeller နှင့် motor power ဖြုတ်ထားပြီးသာ လုပ်ပါ။",
    "Complete the checklist below.": "အောက်ပါစစ်ဆေးစာရင်းကို ပြီးစီးအောင်လုပ်ပါ။",
    "Open final hardware test": "နောက်ဆုံး hardware test ဖွင့်ရန်",
    "Installing firmware. Do not disconnect USB.": "Firmware တင်နေသည်။ USB ကိုမဖြုတ်ပါနှင့်။",
    "Everything is ready. Finish setup to use the dashboard.": "အားလုံးအသင့်ဖြစ်ပြီ။ Dashboard အသုံးပြုရန် ပြင်ဆင်မှုကိုပြီးဆုံးပါ။",

    # Joystick monitor and calibration.
    "Joystick Monitor": "Joystick ကြည့်ရှုရန်",
    "Scanning for compatible devices...": "အသုံးပြုနိုင်သော ကိရိယာများကို ရှာဖွေနေသည်…",
    "Axes": "Axis များ",
    "Buttons": "ခလုတ်များ",
    "Hat switches / D-pad": "Hat switch / D-pad",
    "No compatible joystick is connected. Enable Demo Controller in Settings to test without hardware.": "အသုံးပြုနိုင်သော joystick မချိတ်ထားပါ။ Hardware မရှိဘဲစမ်းရန် Settings ထဲတွင် Demo Controller ကိုဖွင့်ပါ။",
    "Joystick Calibration": "Joystick ချိန်ညှိမှု",
    "Calibration learns the real minimum, center and maximum of every axis. This removes offset, uneven travel and old-controller range errors before RC channel mapping.": "Calibration က axis တစ်ခုစီ၏ minimum၊ center နှင့် maximum အစစ်ကိုမှတ်ယူပြီး RC channel mapping မလုပ်မီ offset နှင့် range အမှားများကို လျှော့ချပေးသည်။",
    "No joystick selected": "Joystick မရွေးထားပါ",
    "Not calibrated": "Calibration မလုပ်ရသေးပါ",
    "Start": "စတင်ရန်",
    "Move every control": "Control အားလုံး လှုပ်ရန်",
    "Release to neutral": "Neutral သို့ပြန်ထားရန်",
    "Save": "သိမ်းရန်",
    "Start calibration": "Calibration စတင်ရန်",
    "Capture neutral / center": "Neutral / center မှတ်ယူရန်",
    "Save calibration": "Calibration သိမ်းရန်",
    "Reset saved calibration": "သိမ်းထားသော calibration ဖျက်ရန်",
    "Connect and select a joystick first.": "Joystick ကိုအရင်ချိတ်ပြီး ရွေးပါ။",
    "Calibration saved": "Calibration သိမ်းပြီး",
    "Axis": "Axis",
    "Live position": "လက်ရှိနေရာ",
    "Raw": "Raw",
    "Minimum": "အနိမ့်ဆုံး",
    "Center": "အလယ်",
    "Maximum": "အမြင့်ဆုံး",
    "Captured range": "မှတ်ယူထားသော range",
    "Saved calibration loaded. Start again only when you want to replace it.": "သိမ်းထားသော calibration ကိုအသုံးပြုနေသည်။ ပြန်အစားထိုးလိုမှသာ အသစ်စတင်ပါ။",
    "Ready. Start calibration, then move every axis through its full physical range.": "အသင့်ဖြစ်သည်။ Calibration စပြီး axis အားလုံးကို အပြည့်အဝလှုပ်ပါ။",

    # Mapping.
    "Channel Mapping": "Channel ချိတ်ဆက်မှု",
    "Bind each USB controller to a logical role, then combine stick, throttle, pedals and auxiliary controls into one RC output.": "USB controller တစ်ခုစီကို role သတ်မှတ်ပြီး stick၊ throttle၊ pedal နှင့် auxiliary control များကို RC output တစ်ခုအဖြစ်ပေါင်းပါ။",
    "No active profile": "Active profile မရှိပါ",
    "Auto-map AETR": "AETR အလိုအလျောက်ချိတ်ရန်",
    "Save changes": "ပြောင်းလဲမှုများ သိမ်းရန်",
    "Reset AETR defaults": "AETR မူလဆက်တင်ပြန်ထားရန်",
    "Cross-device auto mapping is ready.": "Device များအကြား auto mapping အသင့်ဖြစ်သည်။",
    "The wizard watches every role-bound device and never assigns the same role/axis pair twice.": "Wizard က role သတ်မှတ်ထားသော device အားလုံးကိုကြည့်ပြီး role/axis တစ်ခုတည်းကို နှစ်ကြိမ်မသတ်မှတ်ပါ။",
    "Device role binding": "Device role သတ်မှတ်မှု",
    "Auto-detect works for most HOTAS sets. Bind exact devices when the stick and throttle arrive as separate USB controllers.": "HOTAS အများစုကို auto-detect လုပ်နိုင်သည်။ Stick နှင့် throttle သီးခြား USB device ဖြစ်ပါက device ကိုတိတိကျကျသတ်မှတ်ပါ။",
    "Not resolved": "မသတ်မှတ်ရသေးပါ",
    "Strict AETR failsafe: if any Roll/Pitch/Throttle/Yaw source disappears, set all CH1–CH4 to failsafe": "Strict AETR failsafe: Roll/Pitch/Throttle/Yaw source တစ်ခုခုပျောက်ပါက CH1–CH4 အားလုံးကို failsafe သို့ပြောင်းမည်",
    "Combined RC Channels": "ပေါင်းစပ် RC Channel များ",
    "Every row shows device role, input source and live output.": "Row တစ်ခုစီတွင် device role၊ input source နှင့် live output ကိုပြမည်။",
    "Select a channel": "Channel တစ်ခုရွေးပါ",
    "Channel and source": "Channel နှင့် source",
    "Channel name": "Channel အမည်",
    "Learn Input": "Input ကိုလေ့လာရန်",
    "Choose a role-bound source manually or use Learn Input.": "Role သတ်မှတ်ထားသော source ကိုရွေးပါ သို့မဟုတ် Learn Input သုံးပါ။",
    "Centered stick (-1 to +1)": "Centered stick (-1 မှ +1)",
    "Throttle / slider (low to high)": "Throttle / slider (အနိမ့်မှ အမြင့်)",
    "Reverse direction": "ဦးတည်ချက် ပြောင်းပြန်လုပ်ရန်",
    "Input behavior": "Input အပြုအမူ",
    "Quick setup": "အမြန်ပြင်ဆင်မှု",
    "Centered stick": "Centered stick",
    "Throttle": "Throttle",
    "Two-position switch": "နှစ်နေရာ switch",
    "Output endpoints and safety": "Output endpoint နှင့် လုံခြုံရေး",
    "Normally 1000 µs": "ပုံမှန် 1000 µs",
    "Normally 1500 µs": "ပုံမှန် 1500 µs",
    "Normally 2000 µs": "ပုံမှန် 2000 µs",
    "Used when source is missing": "Source ပျောက်သွားချိန် သုံးမည်",
    "Failsafe": "Failsafe",
    "Response tuning": "တုံ့ပြန်မှု ချိန်ညှိရန်",
    "Trim": "Trim",
    "Expo": "Expo",
    "Smoothing": "Smoothing",
    "Live combined preview": "ပေါင်းစပ် output အကြိုကြည့်ရှုမှု",
    "Raw input: waiting for role-bound device data": "Raw input: role-bound device data ကိုစောင့်နေသည်",
    "Input": "Input",
    "Device": "Device",
    "Select a device and one of its inputs, or use Learn Input.": "Device နှင့် input တစ်ခုရွေးပါ သို့မဟုတ် Learn Input သုံးပါ။",
    "Disabled — use failsafe": "ပိတ်ထားသည် — failsafe သုံးမည်",
    "Constant low": "တည်ငြိမ် အနိမ့်",
    "Constant center": "တည်ငြိမ် အလယ်",
    "Constant high": "တည်ငြိမ် အမြင့်",

    # Profiles.
    "Profiles": "Profile များ",
    "New profile": "Profile အသစ်",
    "Create": "ဖန်တီးရန်",
    "Active profile: —": "လက်ရှိ profile: —",
    "Profile name": "Profile အမည်",
    "Device GUID (* = universal)": "Device GUID (* = အားလုံး)",
    "Save details": "အသေးစိတ် သိမ်းရန်",
    "Set active": "Active အဖြစ်သတ်မှတ်ရန်",
    "Duplicate": "မိတ္တူပွားရန်",
    "Delete": "ဖျက်ရန်",
    "Import JSON": "JSON ထည့်သွင်းရန်",
    "Export JSON": "JSON ထုတ်ယူရန်",

    # Adapter and firmware.
    "Adapter & Hardware Test": "Adapter နှင့် Hardware စမ်းသပ်မှု",
    "Connection & Firmware": "ချိတ်ဆက်မှုနှင့် Firmware",
    "Refresh": "ပြန်ရှာရန်",
    "Connect COM": "COM ချိတ်ရန်",
    "Test simulator": "Simulator စမ်းရန်",
    "Offline simulator": "Offline simulator",
    "Disconnect": "ချိတ်ဆက်မှုဖြုတ်ရန်",
    "Disconnected": "ချိတ်ဆက်မထားပါ",
    "No adapter identified": "Adapter ကိုမသိရှိရသေးပါ",
    "Identify board": "Board သိရှိရန်",
    "Refresh status": "အခြေအနေ ပြန်စစ်ရန်",
    "Upload ESP32 profile": "ESP32 profile တင်ရန်",
    "Reboot adapter": "Adapter restart လုပ်ရန်",
    "ESP32 bootloader": "ESP32 bootloader",
    "Detected board": "သိရှိထားသော board",
    "Not connected": "မချိတ်ထားပါ",
    "Waiting for handshake": "Handshake ကိုစောင့်နေသည်",
    "Desktop stream": "Desktop stream",
    "Stopped": "ရပ်ထားသည်",
    "No live channel packets": "Live channel packet မရှိပါ",
    "PPM output": "PPM output",
    "Unknown": "မသိရှိပါ",
    "Connect and identify a board": "Board ကိုချိတ်ပြီး identify လုပ်ပါ",
    "Adapter status": "Adapter အခြေအနေ",
    "No status packet received": "Status packet မရသေးပါ",
    "Desktop target → firmware received": "Desktop target → firmware လက်ခံရရှိမှု",
    "CHANNEL": "CHANNEL",
    "FUNCTION": "လုပ်ဆောင်ချက်",
    "DESKTOP": "DESKTOP",
    "ADAPTER": "ADAPTER",
    "RESULT": "ရလဒ်",
    "Guided communication failsafe verification": "ဆက်သွယ်မှု failsafe စမ်းသပ်မှု",
    "I confirm that the propeller is removed and motor/aircraft power is disconnected.": "Propeller ဖြုတ်ထားပြီး motor/aircraft power ဖြုတ်ထားကြောင်း အတည်ပြုသည်။",
    "Run failsafe test": "Failsafe စမ်းသပ်ရန်",
    "Abort & restore stream": "ရပ်ပြီး stream ပြန်ဖွင့်ရန်",
    "Firmware details & protocol messages": "Firmware အသေးစိတ်နှင့် protocol စာများ",
    "No device information yet.": "Device အချက်အလက် မရှိသေးပါ။",
    "Offline simulator active": "Offline simulator အသုံးပြုနေသည်",
    "Offline simulator — disconnect hardware first": "Offline simulator — hardware ကိုအရင်ဖြုတ်ပါ",

    # Settings and diagnostics.
    "Settings": "ဆက်တင်များ",
    "Language": "ဘာသာစကား",
    "Enable built-in Demo Flight Joystick": "Built-in Demo Flight Joystick ဖွင့်ရန်",
    "Low-latency flight output (recommended for FlySky trainer control)": "Low-latency flight output (FlySky trainer အတွက် အကြံပြုသည်)",
    "Realtime output limit": "Realtime output အမြန်နှုန်း",
    "UI refresh rate": "UI refresh အမြန်နှုန်း",
    "Default serial baud": "မူလ serial baud",
    "Automatically detect and identify Arduino / ESP32 adapter boards": "Arduino / ESP32 adapter board များကို အလိုအလျောက်ရှာရန်",
    "Prefer the last successful serial port": "နောက်ဆုံးအောင်မြင်ခဲ့သော serial port ကိုဦးစားပေးရန်",
    "Diagnostics level": "Diagnostics အဆင့်",
    "Save settings": "ဆက်တင်များ သိမ်းရန်",
    "Diagnostics": "စစ်ဆေးချက်များ",
}


def navigation_label(key: str, language: object) -> str:
    lang = normalize_language(language)
    if lang == "en":
        return key
    return NAVIGATION_LABELS.get(key, {}).get(lang, key)


def text(key: str, language: object, default: str | None = None, **values: Any) -> str:
    lang = normalize_language(language)
    source = default if default is not None else key
    translated = MYANMAR_TEXT.get(key, source) if lang == "my" else source
    try:
        return translated.format(**values)
    except (KeyError, ValueError):
        return translated


def translate_runtime_text(source: str, language: object) -> str:
    lang = normalize_language(language)
    if lang == "en" or not source:
        return source
    if source in MYANMAR_TEXT:
        return MYANMAR_TEXT[source]

    patterns: tuple[tuple[str, str], ...] = (
        ("Active profile: ", "လက်ရှိ profile: "),
        ("Next: ", "နောက်တစ်ဆင့်: "),
        ("Serial open: ", "Serial ချိတ်ထားသည်: "),
        ("Connected: ", "ချိတ်ဆက်ပြီး: "),
        ("Connected to ", "ချိတ်ဆက်ထားသည်: "),
        ("Latest packet age ", "နောက်ဆုံး packet ကြာချိန် "),
        ("Last valid packet ", "နောက်ဆုံး valid packet "),
        ("Calibration required for ", "Calibration လိုအပ်သည်: "),
        ("Missing or unavailable: ", "ပျောက်နေသည် သို့မဟုတ် အသုံးမပြုနိုင်ပါ: "),
        ("Unmapped channels: ", "Mapping မလုပ်ထားသော channel များ: "),
        ("Firmware installed successfully on ", "Firmware တင်ခြင်းအောင်မြင်သည်: "),
    )
    for prefix, replacement in patterns:
        if source.startswith(prefix):
            return replacement + source[len(prefix):]
    return source


def _translate_widget_text(widget: QWidget, language: str) -> None:
    if isinstance(widget, QAbstractButton):
        current = widget.text()
        source = widget.property("simjoyI18nSourceText")
        if language == "en":
            if isinstance(source, str):
                widget.setText(source)
            return
        translated = translate_runtime_text(current, language)
        if translated != current:
            if not isinstance(source, str):
                widget.setProperty("simjoyI18nSourceText", current)
            widget.setText(translated)
        return

    if isinstance(widget, QGroupBox):
        current = widget.title()
        source = widget.property("simjoyI18nSourceTitle")
        if language == "en":
            if isinstance(source, str):
                widget.setTitle(source)
            return
        translated = translate_runtime_text(current, language)
        if translated != current:
            if not isinstance(source, str):
                widget.setProperty("simjoyI18nSourceTitle", current)
            widget.setTitle(translated)
        return

    if isinstance(widget, QLabel):
        current = widget.text()
        source = widget.property("simjoyI18nSourceText")
        if language == "en":
            if isinstance(source, str):
                widget.setText(source)
            return
        translated = translate_runtime_text(current, language)
        if translated != current:
            if not isinstance(source, str):
                widget.setProperty("simjoyI18nSourceText", current)
            widget.setText(translated)
        return

    if isinstance(widget, QLineEdit):
        current = widget.placeholderText()
        source = widget.property("simjoyI18nSourcePlaceholder")
        if language == "en":
            if isinstance(source, str):
                widget.setPlaceholderText(source)
            return
        translated = translate_runtime_text(current, language)
        if translated != current:
            if not isinstance(source, str):
                widget.setProperty("simjoyI18nSourcePlaceholder", current)
            widget.setPlaceholderText(translated)
        return

    if isinstance(widget, QPlainTextEdit):
        current = widget.placeholderText()
        source = widget.property("simjoyI18nSourcePlaceholder")
        if language == "en":
            if isinstance(source, str):
                widget.setPlaceholderText(source)
            return
        translated = translate_runtime_text(current, language)
        if translated != current:
            if not isinstance(source, str):
                widget.setProperty("simjoyI18nSourcePlaceholder", current)
            widget.setPlaceholderText(translated)


def _translate_combo(combo: QComboBox, language: str) -> None:
    sources = combo.property("simjoyI18nComboSources")
    if language == "en":
        if isinstance(sources, list):
            for index, source in enumerate(sources[: combo.count()]):
                combo.setItemText(index, source)
        return

    if not isinstance(sources, list) or len(sources) != combo.count():
        sources = [combo.itemText(index) for index in range(combo.count())]
        combo.setProperty("simjoyI18nComboSources", sources)
    for index, source in enumerate(sources):
        translated = translate_runtime_text(source, language)
        if translated != source:
            combo.setItemText(index, translated)


def _translate_list(widget: QListWidget, language: str) -> None:
    for index in range(widget.count()):
        item = widget.item(index)
        source = item.data(Qt.ItemDataRole.UserRole + 120)
        current = item.text()
        if language == "en":
            if isinstance(source, str):
                item.setText(source)
            continue
        translated = translate_runtime_text(current, language)
        if translated != current:
            if not isinstance(source, str):
                item.setData(Qt.ItemDataRole.UserRole + 120, current)
            item.setText(translated)


def apply_widget_language(root: QWidget, language: object) -> None:
    lang = normalize_language(language)
    widgets: list[QWidget] = [root]
    widgets.extend(root.findChildren(QWidget))
    for widget in widgets:
        _translate_widget_text(widget, lang)
        if isinstance(widget, QComboBox):
            _translate_combo(widget, lang)
        elif isinstance(widget, QListWidget):
            _translate_list(widget, lang)


def _localize_detail(detail: str, language: str) -> str:
    if language == "en":
        return detail
    exact = translate_runtime_text(detail, language)
    if exact != detail:
        return exact
    if detail.startswith("Profile “") and " has safe endpoints and failsafe values." in detail:
        name = detail[len("Profile “") : detail.index("”")]
        return f"Profile “{name}” တွင် endpoint နှင့် failsafe တန်ဖိုးများ လုံခြုံစွာသတ်မှတ်ထားသည်။"
    if detail.endswith(" channels from active profile"):
        return detail.replace(" channels from active profile", " channel ကို active profile မှ ပို့နေသည်")
    if detail == "Every required AETR device has saved per-device calibration.":
        return "လိုအပ်သော AETR device အားလုံးတွင် သီးခြား calibration သိမ်းထားသည်။"
    if detail == "Connect a USB stick, throttle or pedals. Demo input does not count as flight-ready hardware.":
        return "USB stick၊ throttle သို့မဟုတ် pedal ကိုချိတ်ပါ။ Demo input ကို flight-ready hardware အဖြစ်မတွက်ပါ။"
    if detail == "The test simulator has no physical PPM output. Connect an Arduino or ESP32 adapter.":
        return "Test simulator တွင် physical PPM output မရှိပါ။ Arduino သို့မဟုတ် ESP32 adapter ကိုချိတ်ပါ။"
    if detail == "Connect and identify an Arduino UNO/Nano, Mega 2560 or ESP32-S3 adapter.":
        return "Arduino UNO/Nano၊ Mega 2560 သို့မဟုတ် ESP32-S3 adapter ကိုချိတ်ပြီး identify လုပ်ပါ။"
    if detail == "One or more required AETR sources are missing or invalid. Output is using safe values.":
        return "လိုအပ်သော AETR source တစ်ခု သို့မဟုတ် အများအပြား ပျောက်နေသည်/မမှန်ပါ။ Output သည် safe values ကိုအသုံးပြုနေသည်။"
    if detail == "Roll, pitch, throttle and yaw will move to their configured safe values if a required source disappears.":
        return "လိုအပ်သော source ပျောက်သွားပါက Roll၊ Pitch၊ Throttle နှင့် Yaw သည် သတ်မှတ်ထားသော safe values သို့ပြောင်းမည်။"
    if detail == "Strict grouped failsafe is recommended before connecting an aircraft.":
        return "လေယာဉ်မချိတ်မီ Strict grouped failsafe ကိုဖွင့်ထားရန် အကြံပြုသည်။"
    if detail == "Flight controls, mapping, calibration, adapter and failsafe are ready.":
        return "Flight controls၊ mapping၊ calibration၊ adapter နှင့် failsafe အားလုံးအသင့်ဖြစ်သည်။"
    return detail


READINESS_TITLES_MY: dict[str, str] = {
    "Flight controls detected": "Flight control များ တွေ့ရှိသည်",
    "Connect flight controls": "Flight control များ ချိတ်ပါ",
    "AETR device roles assigned": "AETR device role များ သတ်မှတ်ပြီး",
    "Assign AETR controls": "AETR control များ သတ်မှတ်ပါ",
    "Controls calibrated": "Control များ calibration လုပ်ပြီး",
    "Calibrate controls": "Control များ calibration လုပ်ပါ",
    "AETR mapping is valid": "AETR mapping မှန်ကန်သည်",
    "Complete channel mapping": "Channel mapping ပြီးအောင်လုပ်ပါ",
    "Hardware adapter connected": "Hardware adapter ချိတ်ထားသည်",
    "Connect a physical adapter": "Physical adapter ချိတ်ပါ",
    "Connect the trainer adapter": "Trainer adapter ချိတ်ပါ",
    "Failsafe is active": "Failsafe အလုပ်လုပ်နေသည်",
    "Strict AETR failsafe armed": "Strict AETR failsafe အသင့်ဖြစ်သည်",
    "Enable strict AETR failsafe": "Strict AETR failsafe ဖွင့်ပါ",
}


def localize_readiness_report(report: ReadinessReport, language: object) -> ReadinessReport:
    lang = normalize_language(language)
    if lang == "en":
        return report
    items: list[ReadinessItem] = []
    for item in report.items:
        items.append(
            replace(
                item,
                title=READINESS_TITLES_MY.get(item.title, item.title),
                detail=_localize_detail(item.detail, lang),
            )
        )
    headline = text(report.headline, lang)
    summary = _localize_detail(report.summary, lang)
    next_action = READINESS_TITLES_MY.get(report.next_action, report.next_action)
    return replace(
        report,
        headline=headline,
        summary=summary,
        next_action=next_action,
        items=tuple(items),
    )
