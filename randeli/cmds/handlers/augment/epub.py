import copy

import bs4.element
import click
from bs4 import BeautifulSoup

import randeli
from randeli import LOGGER


class EPUBEventHandler:

    def __init__(self, ctx=None, backend=None):
        self.overlay_boxes = []

        self.ctx = ctx
        self.backend = backend

        self.policy = randeli.policy.Rules()
        if ctx:
            self.policy.loadRulesFromDict( ctx )

    def beginPageCB(self, msg : randeli.librandeli.notify.BeginPage):

        status = ""

        if self.ctx['page'] != 0 and self.ctx['page'] != msg.page_number:
            status = "(not selected for updating)"

        click.echo(f"Page {msg.page_number} / {msg.page_count} {status}")

        LOGGER.info(f"Page {msg.page_number} / {msg.page_count} {status}")

    def endPageCB(self, msg : randeli.librandeli.notify.EndPage):
        pass

    def elementCB(self, msg : randeli.librandeli.notify.Element):

        if self.ctx['page'] == 0 or self.ctx['page'] == msg.page_number:

            augmented = msg.builder.new_tag("p")

            # just in case there are some attributes on the paragraph
            for k,v in msg.element.attrs.items():
                augmented[k] = v

            orig = copy.copy(msg.element.contents)

            for child in orig:

                if isinstance(child, bs4.element.Tag):

                    augmented.append(child)

                else:
                    self.process_text( child, augmented, builder=msg.builder )

            msg.element.replace_with(augmented)

    def process_text(self, child, output, builder=None):

        words = child.split(' ')

        for idx, word in enumerate(words):

            #if word == '' or word == ' ':
            if idx != 0:
                output.append( " " )

            if self.policy.shouldAugment( word ):
                LOGGER.debug(f"policy will markup {word}")

                splits = self.policy.splitWord( word )

                if self.policy.use_strong_text or self.policy.use_colored_text:

                    span = builder.new_tag("span")

                    # we're not using the class, but this would
                    # make it easy to de-randeli it later...
                    span["class"] = "randeli"
                    span["style"] = ""

                    if self.policy.use_strong_text:
                        span["style"] += "font-weight:bold;"

                    if self.policy.use_colored_text:
                        span["style"] += f"color:{self.policy.getColoredTextColor()};"

                    span.string = splits.head
                    output.append( span)
                    # no leading space
                    output.append(splits.tail)

                else:
                    output.append( word )

            else:
                output.append( word )


# provide a means to call the processing for debugging on small pieces of HTML
if __name__ == "__main__":

    import sys

    h = EPUBEventHandler()

    soup = BeautifulSoup()

    res = soup.new_tag("p")

    h.process_text(sys.argv[1],res, builder=soup)

    print(res)
