from __future__ import annotations

from .page_help import HelpPage as _BaseHelpPage


class HelpPage(_BaseHelpPage):
    """Help page carrying the public MAHA and BMH product credit."""

    def set_language(self, language: object) -> None:
        super().set_language(language)
        my = self._language == "my"
        credit = (
            "\n\nဤဆော့ဖ်ဝဲကို မြန်မာနိုင်ငံလေကြောင်းဝါသနာရှင်များအသင်း "
            "(Myanmar Aero Hobbyist Association — MAHA) အတွက် BMH မှ ရေးသားဖန်တီးထားခြင်းဖြစ်သည်။"
            if my
            else "\n\nDeveloped by BMH for the Myanmar Aero Hobbyist Association (MAHA)."
        )
        purpose = (
            "\nSimulator joystick နှင့် USB flight control များကို FlySky trainer system နှင့် "
            "ပိုမိုလွယ်ကူလုံခြုံစွာ အသုံးပြုနိုင်ရန် ရည်ရွယ်ထားသည်။"
            if my
            else "\nCreated to make simulator joysticks and USB flight controls easier and safer to use with FlySky trainer systems."
        )
        self.about_text.setText(self.about_text.text() + credit + purpose)
