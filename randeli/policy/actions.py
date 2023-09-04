
import random

from dataclasses import dataclass

@dataclass
class WordDetails:
    head : str = ""
    tail : str = ""


class Actions:

    def __init__(self, seed=230522):
        random.seed(seed)

    def splitWord(self, word, rules) -> WordDetails:
        """Split a word according to the policy `rules`"""
        
        head_size = 0
        if len(word) > rules.max_head_len:
            head_size = random.randint(1, rules.max_head_len)
        else:
            head_size = random.randint(1, len(word))

        return WordDetails( head = word[:head_size], tail = word[head_size:])

