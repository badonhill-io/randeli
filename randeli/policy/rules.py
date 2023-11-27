
import json
import pprint
import random
import string
from dataclasses import dataclass

import pydantic

from randeli import LOGGER

KEYS={
    'policy.box_x_scale' : {
        "type" : "float",
        "default" : 1.0
    },
    'policy.box_y_scale' : {
        "type" : "float",
        "default" : 1.0
    },
    'policy.box_x_offset' : {
        "type" : "int",
        "default" : 0
    },
    'policy.box_y_offset' : {
        "type" : "int",
        "default" : 0
    },
    'policy.fallback-font' : {
        "type" : "str",
        "default" : "CMU Serif"
    },
    'policy.font-map-file' : {
        "type" : "str",
        "default" : None
    },
    'policy.max_head_len' : {
        "type" : "int",
        "default" : 4
    },
    'policy.min_head_len' : {
        "type" : "int",
        "default" : 1
    },
    'policy.min_lines_in_para' : {
        "type" : "int",
        "default" : 1
    },
    'policy.min_ocr_image_height': {
        "type" : "int",
        "default" : 320
    },
    'policy.min_ocr_image_width' : {
        "type" : "int",
        "default" : 480
    },
    'policy.min_words_in_line' : {
        "type" : "int",
        "default" : 5
    },
    'policy.modify_strong_font_size' : {
        "type" : "int",
        "default" : 0
    },
    'policy.seed' : {
        "type" : "int",
        "default" : 230901
    },
    'policy.colored_text_color' : {
        "type" : "str",
        "default" : "#011993"
    },
    'policy.strong_box_color' : {
        "type" : "str",
        "default" : "#01199330"
    },
    'policy.strong_box_height' : {
        "type" : "float",
        "default" : 0.0
    },
    'policy.strong_box_shape' : {
        "type" : "str",
        "default" : "box" # "box", "underbar", "overbar"
    },
    'policy.use_strong_text' : {
        "type" : "bool",
        "default" : True
    },
    'policy.use_colored_text' : {
        "type" : "bool",
        "default" : True
    },
    'policy.use_strong_box' : {
        "type" : "bool",
        "default" : False
    },
}

@dataclass
class WordDetails:
    head : str = ""
    tail : str = ""

@dataclass(frozen=False, slots=True)
class WordInfo:
    txt : str = ""
    upper_case: int = 0
    lower_case: int = 0
    numeric: int = 0
    punctuation: int = 0
    whitespace: int = 0
    leading_alphabetic:  int = 0

def word_classes(txt):
    """Return the number of characters in the word in each of the following classes
        - upper_case
        - lower_case
        - numeric (includes numbers with embedded comma and period)
        - punctuation
        - whitespace

    periods and commas that are embedded in numbers (i.e 10.3 or 123,456.78) are ONLY
    counted as numeric NOT punctuation
    """
    winfo = WordInfo()

    if not txt:
        return winfo

    winfo.txt = txt

    for i in range(len(txt)):
        if txt[:i].isalpha():
            winfo.leading_alphabetic = i
        if txt[i].isupper():
            winfo.upper_case = winfo.upper_case + 1
        elif txt[i].islower():
            winfo.lower_case = winfo.lower_case + 1
        elif txt[i].isspace():
            winfo.whitespace = winfo.whitespace + 1
        elif txt[i].isdigit():
            winfo.numeric = winfo.numeric + 1
        elif txt[i] in string.punctuation:
            if ( ( i > 0 ) and txt[i-1].isdigit() ) and ( ( i < len(txt)-1 ) and txt[i+1].isdigit() ) :
                winfo.numeric = winfo.numeric + 1
            else:
                winfo.punctuation = winfo.punctuation + 1

    return winfo


class Rules:

    def __init__(self):
        """
        Policy Rules for how 'words' are to be augmented
        """

        self.font_map = {}

        for k,t in KEYS.items():

            field = k.replace("policy.","_").replace("-", "_")

            if "default" in KEYS[k]:
                setattr(self, field, KEYS[k]["default"])
            else:
                setattr(self, field, None)

    def __str__(self):

        return pprint.pformat( {
            k: getattr(self, k) for k, v in self.__class__.__dict__.items() if isinstance(v, property)}, indent=1, depth=1 ) ## depth stops the full fonts_map being dumped (its large)


    def loadRulesFromDict(self, cfg):
        """Reading the dict from external file is done by caller"""

        try:

            for k,v in cfg.items():

                key = k.replace("policy.","")
                field = k.replace("policy.","").replace("-", "_")

                if k in KEYS:
                    if KEYS[k]["type"] == "int":
                        setattr(self, field, pydantic.parse_obj_as(int,cfg[k]))
                    elif KEYS[k]["type"] == "float":
                        setattr(self, field, pydantic.parse_obj_as(float,cfg[k]))
                    elif KEYS[k]["type"] == "bool":
                        setattr(self, field, pydantic.parse_obj_as(bool,cfg[k]))
                    else:
                        setattr(self, field, cfg[k] )

        except Exception as e:
            LOGGER.exception(e)

    def saveRulesToDict(self, cfg):
        """Writing dict to file is handled in caller"""

        try:
            cfg["policy"] = {}

            for k,t in KEYS.items():
                key = k.replace("policy.","")
                field = k.replace("policy.","").replace("-", "_")

                cfg["policy"][key] = getattr(self, field)

        except Exception as e:
            LOGGER.exception(e)


    def shouldAugment(self, word, words_in_line=0, lines_in_para=0 ) -> bool :
        """Returns if 'word' should be marked up
        (taking into account letters, numbers, etc)

        Advanced context (words_in_line/lines_in_para) improve model
        """
        ret = False

        cls = word_classes(word)


        if cls.leading_alphabetic == 0:
            # Does not start with letter -> False
            ret = False
        elif  cls.upper_case > 0 and cls.lower_case == 0 and cls.numeric > 0:
            # Only upper-case letters and numbers -> False
            # probably an ID of some sort
            ret = False

        else:
            if ( cls.upper_case + cls.lower_case ) > cls.numeric:
                # More letters than numbers -> True
                ret = True

            if ( cls.upper_case + cls.lower_case ) > cls.whitespace:
                # More letters than whitespace -> True
                ret = True
            else:
                ret = False

            if ( cls.upper_case + cls.lower_case ) > cls.punctuation:
                # More letters than punctuation -> True
                ret = True
            else:
                ret = False

        # the above only look at the characters in a word, now look at
        # context (overriding any Trues above)

        if words_in_line > 0 and words_in_line < self.min_words_in_line:
            ret = False

        if lines_in_para > 0 and lines_in_para < self.min_lines_in_para:
            ret = False

        # All other combinations not marked up
        LOGGER.debug(f"Augment '{word}' ? {ret} | {cls} {words_in_line} {lines_in_para}")
        return ret

    def getStrongFontPath(self, base_font_name : str, italic : bool, size : int) -> str:
        """Returns the path to the _strong_ version of base_font_name from the font-map
        or empty to disable font modification
        """

        if self.use_strong_text is False:
            return ""

        fnt = "Bold"

        try:
            if italic:
                if base_font_name in self.font_map:
                    if "Bold Italic" in  self.font_map[base_font_name]:
                        fnt = "Bold Italic"
                    elif "BoldItalic" in  self.font_map[base_font_name]:
                        fnt = "BoldItalic"
                elif self.fallback_font in self.font_map:
                    if "Bold Italic" in  self.font_map[self.fallback_font]:
                        fnt = "Bold Italic"
                    if "BoldItalic" in  self.font_map[self.fallback_font]:
                        fnt = "BoldItalic"

        except Exception as e:
            LOGGER.exception(e)

        if base_font_name in self.font_map:
            if fnt in self.font_map[base_font_name]:
                LOGGER.debug(f"Found base font {base_font_name} and {fnt} in mapping italic={italic}")

                return self.font_map[base_font_name][fnt]
            else:
                LOGGER.debug(f"Could not find {fnt} in {base_font_name}")

        LOGGER.warning(f"Could not find {base_font_name} defaulting to {self.fallback_font} and {fnt}")

        return self.font_map[self.fallback_font][fnt]

    def getStrongFontSize(self, size):
        ### Return negitive number to disable modifying the font"""
        if self.use_strong_text is True:
            LOGGER.debug(f"Setting (strong) Font size to be {size} + {self.modify_strong_font_size}")
            return size + self.modify_strong_font_size
        else:
            return -1.0


    def getColoredTextColor(self):
        ### return an empty string to disable modifying the color
        if self.use_colored_text:
            return self.colored_text_color
        else:
            return ""

    def getStrongBoxColor(self):
        ### return an empty string to disable modifying the color
        if self.use_strong_box is True:
            return self.strong_box_color
        else:
            return ""

    def splitWord(self, word) -> WordDetails:
        """Split a word according to the policy `rules`"""

        head_size = 0
        if len(word) > self.max_head_len:
            head_size = random.randint(1, self.max_head_len) # nosec: B311
        else:
            head_size = random.randint(1, len(word)) # nosec: B311

        return WordDetails( head = word[:head_size], tail = word[head_size:])


    @property
    def font_map(self):
        """dict containing font map"""
        return self._font_map

    @font_map.setter
    def font_map(self, value):
        """dict containing font map"""
        self._font_map = value

    @property
    def font_map_file(self):
        """Map font names to font files"""
        return self._font_map_file

    @font_map_file.setter
    def font_map_file(self, value):
        self._font_map_file = value

        if value is None:
            self.font_map = {}
        else:
            with open( self._font_map_file, "r") as fonts:
                self.font_map = json.load(fonts)

    @property
    def fallback_font(self):
        """Use this font name if the desired font can't be found"""
        return self._fallback_font

    @fallback_font.setter
    def fallback_font(self, value):
        self._fallback_font = value

    @property
    def min_head_len(self):
        """Minimum number of characters of 'head' segment """
        return self._min_head_len

    @min_head_len.setter
    def min_head_len(self, value):
        self._min_head_len = value


    @property
    def max_head_len(self):
        """Minimum number of characters of 'head' segment
        TODO
        - a constant feels wrong - should be based on length of word?
        """
        return self._max_head_len

    @max_head_len.setter
    def max_head_len(self, value):
        self._max_head_len = value

    @property
    def modify_strong_font_size(self):
        """Shoehorning bold chars into limited space can
        cause letters to lose their interword spacing, so
        allow overriding of the font-size for the Strong font
        (-1 seems enough)
        """
        return self._modify_strong_font_size

    @modify_strong_font_size.setter
    def modify_strong_font_size(self, value : float):
        self._modify_strong_font_size = value

    @property
    def seed(self):
        return self._seed

    @seed.setter
    def seed(self, value):
        self._seed = value
        random.seed( self._seed)

    @property
    def strong_box_color(self):
        return self._strong_box_color

    @strong_box_color.setter
    def strong_box_color(self, value):
        self._strong_box_color = value

    @property
    def strong_box_height(self):
        return self._strong_box_height

    @strong_box_height.setter
    def strong_box_height(self, value):
        self._strong_box_height = value

    @property
    def strong_box_shape(self):
        return self._strong_box_shape

    @strong_box_shape.setter
    def strong_box_shape(self, value):
        self._strong_box_shape = value

    @property
    def colored_text_color(self):
        return self._colored_text_color

    @colored_text_color.setter
    def colored_text_color(self, value):
        self._colored_text_color = value

    @property
    def use_strong_text(self):
        return self._use_strong_text

    @use_strong_text.setter
    def use_strong_text(self, value):
        self._use_strong_text = pydantic.parse_obj_as(bool,value)

    @property
    def use_strong_box(self):
        return self._use_strong_box

    @use_strong_box.setter
    def use_strong_box(self, value):
        self._use_strong_box = pydantic.parse_obj_as(bool,value)

    @property
    def use_colored_text(self):
        return self._use_colored_text

    @use_colored_text.setter
    def use_colored_text(self, value):
        self._use_colored_text = pydantic.parse_obj_as(bool,value)

    @property
    def min_words_in_line(self):
        return self._min_words_in_line

    @min_words_in_line.setter
    def min_words_in_line(self, value):
        self._min_words_in_line = value

    @property
    def min_lines_in_para(self):
        return self._min_lines_in_para

    @min_lines_in_para.setter
    def min_lines_in_para(self, value):
        self._min_lines_in_para = value

    @property
    def box_x_scale(self):
        return self._box_x_scale

    @box_x_scale.setter
    def box_x_scale(self, value):
        self._box_x_scale = value

    @property
    def box_x_offset(self):
        return self._box_x_offset

    @box_x_offset.setter
    def box_x_offset(self, value):
        self._box_x_offset = value

    @property
    def box_y_scale(self):
        return self._box_y_scale

    @box_y_scale.setter
    def box_y_scale(self, value):
        self._box_y_scale = value

    @property
    def box_y_offset(self):
        return self._box_y_offset

    @box_y_offset.setter
    def box_y_offset(self, value):
        self._box_y_offset = value

    @property
    def min_ocr_image_height(self):
        return self._min_ocr_image_height

    @min_ocr_image_height.setter
    def min_ocr_image_height(self, value):
        self._min_ocr_image_height = value

    @property
    def min_ocr_image_width(self):
        return self._min_ocr_image_width

    @min_ocr_image_width.setter
    def min_ocr_image_width(self, value):
        self._min_ocr_image_width = value
