
import logging
import string
from dataclasses import dataclass
import random
import json
import pydantic

from .. librandeli.trace import tracer as FTRACE 

log_name = "r.l.p.rules"

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

    def __init__(self, log=log_name):
        """
        Policy Rules for how 'words' are to be handled
        """

        self.logger = logging.getLogger(log)
        self.devlog = logging.getLogger("d.devel")

        self.seed = 230522

        self.min_head_len = 1
        self.max_head_len = 4

        self.use_strong_text = True
        self.fallback_font = "Helvetica"
        self.modify_strong_font_size = 0

        self.font_map = {}

        self.use_strong_box = True
        self.strong_box_y_offset = 0
        self.strong_box_height = 0

        self.use_strong_text_color = True
        self.strong_text_color = "#011993"

        self.use_strong_box_color = True
        self.strong_box_color = "#01199320"

        self.min_ocr_image_width = 640
        self.min_ocr_image_height = 480

    def loadRulesFromDict(self, cfg):
        """Reading th dict from external file is done by caller"""

        try:
            if 'policy.use_strong_text' in cfg:
                self.use_strong_text = pydantic.parse_obj_as(bool,cfg['policy.use_strong_text'])

            if 'policy.use_strong_text_color' in cfg:
                self.use_strong_text_color = pydantic.parse_obj_as(bool,cfg['policy.use_strong_text_color'])

            if 'policy.use_strong_box_color' in cfg:
                self.use_strong_box_color = pydantic.parse_obj_as(bool,cfg['policy.use_strong_box_color'])

            if 'policy.strong_text_color' in cfg:
                self.strong_text_color = cfg['policy.strong_text_color']

            if 'policy.seed' in cfg:
                self.seed = cfg['policy.seed']

            if 'policy.font-map-file' in cfg:
                self.font_map_file = cfg['policy.font-map-file']

            if 'policy.fallback-font' in cfg:
                self.fallback_font = cfg['policy.fallback-font']

            if 'policy.min_head_len' in cfg:
                self.min_head_len = int(cfg["policy.min_head_len"])

            if 'policy.max_head_len' in cfg:
                self.max_head_len = int(cfg["policy.max_head_len"])

            if 'policy.min_ocr_image_width' in cfg:
                self.min_ocr_image_width = int(cfg["policy.min_ocr_image_width"])

            if 'policy.min_ocr_image_height' in cfg:
                self.min_ocr_image_height = int(cfg["policy.min_ocr_image_height"])

            if 'policy.modify_strong_font_size' in cfg:
                self.modify_strong_font_size = float(cfg["policy.modify_strong_font_size"])
        except:
            pass

    def saveRulesToDict(self, cfg):
        """Writing dict to file is handled in caller"""

        try:
            cfg["policy"] = {}
            cfg["policy"]["seed"] = self.seed
            cfg["policy"]["use_strong_box"] = self.use_strong_box
            cfg["policy"]["use_strong_text"] = self.use_strong_text
            cfg["policy"]["use_strong_box_color"] = self.use_strong_box_color
            cfg["policy"]["use_strong_text_color"] = self.use_strong_text_color
            cfg["policy"]["strong_text_color"] = self.strong_text_color
            cfg["policy"]["strong_box_color"] = self.strong_box_color
            cfg["policy"]["min_head_len"] = self.min_head_len
            cfg["policy"]["max_head_len"] = self.max_head_len
            cfg["policy"]["min_ocr_image_width"] = self.min_ocr_image_width
            cfg["policy"]["min_ocr_image_height"] = self.min_ocr_image_height
            cfg["policy"]["modify_strong_font_size"] = self.modify_strong_font_size
            cfg["policy"]["fallback-font"] = self.fallback_font
            cfg["policy"]["font-map-file"] = self.font_map_file
        except:
            pass

    def shouldMarkup(self, word) -> bool :
        """Returns if 'word' should be marked up
        (taking into account letters, numbers, etc)"""
        ret = False

        cls = word_classes(word)

        if cls.leading_alphabetic == 0:
            """Does not start with letter -> False"""
            return False

        if  cls.upper_case > 0 and cls.lower_case == 0 and cls.numeric > 0:
            """Only upper-case letters and numbers -> False"""
            # probably an ID of some sort
            return False

        if ( cls.upper_case + cls.lower_case ) > cls.numeric:
            """More letters than numbers -> True"""
            ret = True

        if ( cls.upper_case + cls.lower_case ) > cls.whitespace:
            """More letters than whitespace -> True"""
            ret = True
 
        if ( cls.upper_case + cls.lower_case ) > cls.punctuation:
            """More letters than punctuation -> True"""
            ret = True

        """All other combinations not marked up"""
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
            self.logger.exception(e)

        if base_font_name in self.font_map:
            if fnt in self.font_map[base_font_name]:
                self.devlog.debug(f"Found base font {base_font_name} and {fnt} in mapping")

                return self.font_map[base_font_name][fnt]

        self.devlog.debug(f"Falling back to {self.fallback_font} and {fnt}")
        return self.font_map[self.fallback_font][fnt]
            
    def getStrongFontSize(self, size):
        ### Return negitive number to disable modifying the font"""
        if self.use_strong_text:
            self.devlog.debug(f"Setting (strong) Font size to be {size} + {self.modify_strong_font_size}")
            return size + self.modify_strong_font_size
        else:
            return -1.0


    def getStrongTextColor(self):
        ### return an empty string to disable modifying the color
        if self.use_strong_text_color:
            return self.strong_text_color
        else:
            return ""

    def getStrongBoxColor(self):
        ### return an empty string to disable modifying the color
        if self.use_strong_box_color:
            return self.strong_box_color
        else:
            return ""

    def splitWord(self, word) -> WordDetails:
        """Split a word according to the policy `rules`"""

        head_size = 0
        if len(word) > self.max_head_len:
            head_size = random.randint(1, self.max_head_len)
        else:
            head_size = random.randint(1, len(word))

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
    def strong_font_size_rule(self):
        """Shoehorning bold chars into limited space can
        cause letters to lose their interword spacing, so
        allow overriding of the font-size for the Strong font
        (-1 seems enough)
        """
        return self._strong_font_size_rule

    @strong_font_size_rule.setter
    def strong_font_size_rule(self, value : float):
        self._strong_font_size_rule = value

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
    def strong_text_color(self):
        return self._strong_text_color

    @strong_text_color.setter
    def strong_text_color(self, value):
        self._strong_text_color = value

    @property
    def use_strong_text(self):
        return self._use_strong_text

    @use_strong_text.setter
    def use_strong_text(self, value):
        self._use_strong_text = pydantic.parse_obj_as(bool,value)

    @property
    def use_strong_text_color(self):
        return self._use_strong_color

    @use_strong_text_color.setter
    def use_strong_text_color(self, value):
        self._use_strong_color = pydantic.parse_obj_as(bool,value)


