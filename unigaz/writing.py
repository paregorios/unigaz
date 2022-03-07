#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Languages and writing systems
"""

import aaransia
import cyrtranslit
import ftlangdetect
import langdetect
from language_tags import tags
from slugify import slugify
from textnorm import normalize_space, normalize_unicode
import logging
import pinyin
from py3langid.langid import LanguageIdentifier, MODEL_FILE
import regex
from transliterate import translit, get_available_language_codes
from unigaz.script_codes import REGEX_SCRIPT_CODES

langid = LanguageIdentifier.from_pickled_model(MODEL_FILE, norm_probs=True)
logger = logging.getLogger(__name__)

rx_latin_script = regex.compile(r"^[\s\p{IsLatin}\p{Punctuation}]+$")

rxx_scripts = dict()
for code in REGEX_SCRIPT_CODES:
    rx = r"^[\s\p{Common}\p{" + code + r"}]+$"
    rxx_scripts[code] = regex.compile(rx)


def is_latin_script(s: str):
    """Is string Latn?"""
    if rx_latin_script.match(s):
        return True
    return False


def check_script(s: str):
    for script_code, rx in rxx_scripts.items():
        # logger.debug(f"check_script: {script_code}")
        if rx.match(s):
            return script_code
    return None


def norm(s: str):
    """Normalize space and unicode in string."""
    return normalize_space(normalize_unicode(s))


def codify(language_code=None, script_code=None):
    if language_code:
        lc = language_code
    else:
        lc = "und"
    logger.debug(f"lc={lc}")
    if script_code:
        if lc == "und":
            code = "-".join((lc, script_code))
        else:
            if tags.language(lc).script.format == script_code:
                code = lc
            else:
                code = "-".join((lc, script_code))
    else:
        code = lc
    code = tags.tag(code).format  # ensure proper conventions
    return code


def classify(s: str, language_code=None, script_code=None):
    """Determine language and script and return results."""
    v = norm(s)
    attested = None

    # language
    if language_code:
        language_tag = tags.language(language_code).format
    elif len(v.split()) >= 5:
        threshold = 0.5
        codes = set()
        langid_code, langid_prob = langid.classify(v)
        if langid_prob >= threshold:
            codes.add(langid_code)
        codes.add(langdetect.detect(v))
        ft_result = ftlangdetect.detect(v)
        ft_code = ft_result["lang"]
        ft_prob = ft_result["score"]
        if ft_prob >= threshold:
            codes.add(ft_result["lang"])
        if len(codes) > 1:
            if ft_code != langid_code:
                language_tag = tags.language(
                    ft_code
                )  # langid mis-identifies "uk" as "ru"
            else:
                raise RuntimeError(f"langconflict: {codes}")
        elif len(codes) == 1:
            language_tag = tags.language(list(codes)[0])
        else:
            language_tag = None
    else:
        language_tag = None
    try:
        language_code_final = language_tag.format
    except AttributeError:
        language_code_final = "und"
    logger.debug(f"language_code_final={language_code_final}")

    # script
    script_code_from_string = check_script(s)
    logger.debug(f"script_code_from_string={script_code_from_string}")
    if script_code:
        script_tag = tags.tag(script_code)
    elif script_code_from_string:
        script_tag = tags.tag(script_code_from_string)
    elif language_tag:
        script_tag = language_tag.script
    else:
        script_tag = None
    try:
        script_code_final = script_tag.format
    except AttributeError:
        script_code_final = "und"
    else:
        script_code_final = script_code_final.capitalize()
    logger.debug(f"script_code_final={script_code_final}")

    # language correction
    if script_code_final == "Hani" and language_code_final == "und":
        language_code_final = "zh"

    # attested
    attested = None
    if script_code_final != "Latn":
        attested = v
    elif language_code_final != "und" and script_code_final != "und":
        if tags.language(language_code_final).script.format == script_code_final:
            attested = v

    # romanized
    romanized = set()
    slug = slugify(v, separator=" ", lowercase=False)
    romanized.add(slug)
    if script_code_from_string:
        if script_code_from_string == "Latn":
            romanized.add(v)
    if language_code_final in get_available_language_codes():
        romanized.add(translit(v, language_code_final, reversed=True))
    if language_code_final in ["cmn", "zh"] and script_code_final in ["Hans", "Hant"]:
        romanized.add(pinyin.get(v))
        romanized.add(pinyin.get(v, format="strip", delimiter=" "))
        romanized.add(pinyin.get(v, format="numerical"))
    if script_code_final == "Cyrl" and language_code_final in cyrtranslit.supported():
        romanized.add(cyrtranslit.to_latin(v, language_code_final))
    if language_code_final in aaransia.get_alphabets_codes():
        romanized.add(aaransia.transliterate(v, language_code_final, "en"))

    return (attested, romanized, language_code_final, script_code_final)
