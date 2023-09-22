
import logging
import string
from dataclasses import dataclass
import random
import json
import pydantic
import pprint

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
        self.use_colored_text = False
        self.fallback_font = "Helvetica"
        self.modify_strong_font_size = 0
        self.colored_text_color = "#011993"

        self.font_map = {}

        self.use_strong_box = False
        self.box_x_scale = 1.0
        self.box_y_scale = 1.0
        self.box_x_offset = 0
        self.box_y_offset = 0
        self.strong_box_height = 0
        self.strong_box_width = 0


        self.use_strong_box_color = True
        self.strong_box_color = "#01199320"

        self.min_ocr_image_width = 640
        self.min_ocr_image_height = 480

        # these apply when we have additional context, i.e. full page OCR
        self.min_words_in_line = 5
        self.min_lines_in_para = 3

    def __str__(self):

        return pprint.pformat( {
            k: getattr(self, k) for k, v in self.__class__.__dict__.items() if isinstance(v, property)}, indent=1, depth=1 ) ## depth stops the full fonts_map being dumped (its large)


    def loadRulesFromDict(self, cfg):
        """Reading th dict from external file is done by caller"""

        try:
            if 'policy.use_strong_text' in cfg:
                self.use_strong_text = pydantic.parse_obj_as(bool,cfg['policy.use_strong_text'])

            if 'policy.use_colored_text' in cfg:
                self.use_colored_text = pydantic.parse_obj_as(bool,cfg['policy.use_colored_text'])

            if 'policy.use_colored_text' in cfg:
                self.use_colored_text= pydantic.parse_obj_as(bool,cfg['policy.use_colored_text'])

            if 'policy.use_strong_box_color' in cfg:
                self.use_strong_box_color = pydantic.parse_obj_as(bool,cfg['policy.use_strong_box_color'])

            if 'policy.strong_text_color' in cfg:
                self.strong_text_color = cfg['policy.strong_text_color']

            if 'policy.strong_box_color' in cfg:
                self.strong_box_color = cfg['policy.strong_box_color']

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

            if 'policy.min_words_in_line' in cfg:
                self.min_words_in_line = int(cfg["policy.min_words_in_line"])

            if 'policy.min_lines_in_para' in cfg:
                self.min_lines_in_para = int(cfg["policy.min_lines_in_para"])

            if 'policy.box_x_scale' in cfg:
                self.box_x_scale = float(cfg["policy.box_x_scale"])

            if 'policy.box_y_scale' in cfg:
                self.box_y_scale = float(cfg["policy.box_y_scale"])

            if 'policy.box_x_offset' in cfg:
                self.box_x_offset = float(cfg["policy.box_x_offset"])

            if 'policy.box_y_offset' in cfg:
                self.box_y_offset = float(cfg["policy.box_y_offset"])

        except:
            pass

    def saveRulesToDict(self, cfg):
        """Writing dict to file is handled in caller"""

        try:
            cfg["policy"] = {}
            cfg["policy"]["seed"] = self.seed
            cfg["policy"]["use_strong_box"] = self.use_strong_box
            cfg["policy"]["use_strong_text"] = self.use_strong_text
            cfg["policy"]["use_colored_text"] = self.use_colored_text
            cfg["policy"]["use_strong_box_color"] = self.use_strong_box_color
            cfg["policy"]["use_colored_text"] = self.use_colored_text
            cfg["policy"]["strong_text_color"] = self.strong_text_color
            cfg["policy"]["strong_box_color"] = self.strong_box_color
            cfg["policy"]["min_head_len"] = self.min_head_len
            cfg["policy"]["max_head_len"] = self.max_head_len
            cfg["policy"]["min_ocr_image_width"] = self.min_ocr_image_width
            cfg["policy"]["min_ocr_image_height"] = self.min_ocr_image_height
            cfg["policy"]["min_words_in_line"] = self.min_words_in_line
            cfg["policy"]["min_lines_in_para"] = self.min_lines_in_para
            cfg["policy"]["modify_strong_font_size"] = self.modify_strong_font_size
            cfg["policy"]["fallback-font"] = self.fallback_font
            cfg["policy"]["font-map-file"] = self.font_map_file

            cfg["policy"]["box_x_scale"] = self.box_x_scale
            cfg["policy"]["box_y_scale"] = self.box_y_scale
            cfg["policy"]["box_x_offset"] = self.box_x_offset
            cfg["policy"]["box_y_offset"] = self.box_y_offset

        except:
            pass


    def shouldAugment(self, word, words_in_line=0, lines_in_para=0 ) -> bool :
        """Returns if 'word' should be marked up
        (taking into account letters, numbers, etc)

        Advanced context (words_in_line/lines_in_para) improve model
        """
        ret = False

        cls = word_classes(word)


        if cls.leading_alphabetic == 0:
            """Does not start with letter -> False"""
            ret = False
        elif  cls.upper_case > 0 and cls.lower_case == 0 and cls.numeric > 0:
            """Only upper-case letters and numbers -> False"""
            # probably an ID of some sort
            ret = False

        else:
            if ( cls.upper_case + cls.lower_case ) > cls.numeric:
                """More letters than numbers -> True"""
                ret = True

            if ( cls.upper_case + cls.lower_case ) > cls.whitespace:
                """More letters than whitespace -> True"""
                ret = True
            else:
                ret = False

            if ( cls.upper_case + cls.lower_case ) > cls.punctuation:
                """More letters than punctuation -> True"""
                ret = True
            else:
                ret = False

        # the above only look at the characters in a word, now look at
        # context (overriding any Trues above)

        if words_in_line > 0 and words_in_line <= self.min_words_in_line:
            ret = False

        if lines_in_para > 0 and lines_in_para <= self.min_lines_in_para:
            ret = False

        """All other combinations not marked up"""
        self.logger.detail(f"Augment '{word}' ? {ret} | {cls} {words_in_line} {lines_in_para}")
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
                self.devlog.debug(f"Found base font {base_font_name} and {fnt} in mapping italic={italic}")

                return self.font_map[base_font_name][fnt]
            else:
                self.devlog.debug(f"Could not find {fnt} in {base_font_name}")

        self.devlog.debug(f"Could not find {base_font_name} defaulting to {self.fallback_font} and {fnt}")

        return self.font_map[self.fallback_font][fnt]

    def getStrongFontSize(self, size):
        ### Return negitive number to disable modifying the font"""
        if self.use_strong_text:
            self.devlog.debug(f"Setting (strong) Font size to be {size} + {self.modify_strong_font_size}")
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





