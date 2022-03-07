#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the unigaz.writing module
"""

import logging
import pinyin
from unigaz.writing import classify


class TestWriting:
    def test_arabic(self):
        s = "قفز الثعلب البني السريع فوق الكلب الكسول."
        attested, romanized, lang_code, script_code = classify(s)
        assert attested == s
        s_romanized = set()
        for r in [
            "qfz lth lb lbny lsry fwq lklb lkswl",
            "qfz alt'lb albny alsry' foq alklb alxol.",
        ]:
            s_romanized.add(r)
        assert romanized == s_romanized
        assert lang_code == "ar"
        assert script_code == "Arab"

    def test_chinese(self):
        s = "敏捷的棕色狐狸跳過了懶惰的狗。"
        attested, romanized, lang_code, script_code = classify(s)
        assert attested == s
        s_romanized = set()
        s_romanized.add(
            "Min Jie De Zong Se Hu Li Tiao Guo Liao Lan Duo De Gou"
        )  # slugify
        # someday hope to have other romaninzation schemes via camel-tools but see README
        assert romanized == s_romanized
        assert lang_code == "zh"
        assert script_code == "Hani"

    def test_english(self):
        s = "The quick brown fox jumped over the lazy dog."
        attested, romanized, lang_code, script_code = classify(s)
        assert attested == s
        s_romanized = set()
        s_romanized.add(s)
        s_romanized.add(s.replace(".", ""))
        s_romanized.add(s.lower())
        assert romanized == s_romanized
        assert lang_code == "en"
        assert script_code == "Latn"

    def test_french(self):
        s = "Le rapide renard brun sauta par dessus le chien paresseux."
        attested, romanized, lang_code, script_code = classify(s)
        assert attested == s
        s_romanized = set()
        s_romanized.add(s)
        s_romanized.add(s.replace(".", ""))
        s_romanized.add(s.lower())
        assert romanized == s_romanized
        assert lang_code == "fr"
        assert script_code == "Latn"

    def test_greek_modern(self):
        s = "Η γρήγορη καφέ αλεπού πήδηξε πάνω από το τεμπέλικο σκυλί."
        attested, romanized, lang_code, script_code = classify(s)
        assert attested == s
        s_romanized = set()
        for r in [
            "h gghhgoghh kafe alepoy phdhxe pano apo to tempeliko skyli.",
            "E gregore kaphe alepou pedexe pano apo to tempeliko skuli",
            "i grigori kafe alepoy pidixe pano apo to tebeliko skuli.",
        ]:
            s_romanized.add(r)
        assert romanized == s_romanized
        assert lang_code == "el"
        assert script_code == "Grek"

    def test_russian(self):
        s = "Быстрая, коричневая лиса, перепрыгнула через ленивого пса."
        attested, romanized, lang_code, script_code = classify(s)
        assert attested == s
        s_romanized = set()
        for r in [
            "Bystraia korichnevaia lisa pereprygnula cherez lenivogo psa",
            "Bystraja, korichnevaja lisa, pereprygnula cherez lenivogo psa.",
        ]:
            s_romanized.add(r)
        assert romanized == s_romanized
        assert lang_code == "ru"
        assert script_code == "Cyrl"

    def test_turkish(self):
        s = "Hızlı kahverengi tilki tembel köpeğin üzerinden atladı."
        attested, romanized, lang_code, script_code = classify(s)
        assert attested == s
        s_romanized = set()
        s_romanized.add(s)
        s_romanized.add("Hizli kahverengi tilki tembel kopegin uzerinden atladi")
        s_romanized.add("hizli kahverengi tilki tembel kopegin uzerinden atladi.")
        assert romanized == s_romanized
        assert lang_code == "tr"
        assert script_code == "Latn"

    def test_ukranian(self):
        s = "Швидкий бурий лис перестрибнув через ледачого пса."
        attested, romanized, lang_code, script_code = classify(s)
        assert attested == s
        s_romanized = set()
        for r in [
            "Shvidkii burii lis perestribnuv cherez ledachogo psa",
            "Shvydkyj buryj lys perestrybnuv cherez ledachoho psa.",
        ]:
            s_romanized.add(r)
        assert romanized == s_romanized
        assert lang_code == "uk"
        assert script_code == "Cyrl"
