Randeli
=======

Augment EPUB and PDFs to help make them easier to read and understand for
people with ADD/ADHD.

This is primarily targeted at processing academic papers and patents.

Randeli is currently using the commercial Apryse PDF SDK to handle PDFs, a license
key is required. A free demo license is available at https://dev.apryse.com


A couple of examples
-------------------

### US Patent (uses OCR)

[![Patent](https://github.com/badonhill-io/randeli/blob/main/samples/3rdParty/uspto.8539484.png0.png)](https://github.com/badonhill-io/randeli/blob/main/samples/3rdParty/uspto.8539484.pdf)

[![Patent (augmented)](https://github.com/badonhill-io/randeli/blob/main/samples/augmented/3rdParty/uspto.8539484.augmented0.png)](https://github.com/badonhill-io/randeli/blob/main/samples/augmented/3rdParty/uspto.8539484.pdf)


### Academic Paper

[![Academic Paper](https://github.com/badonhill-io/randeli/blob/main/samples/3rdParty/IoTSecurityPaperWF-IOT0.png)](https://github.com/badonhill-io/randeli/blob/main/samples/3rdParty/IoTSecurityPaperWF-IOT.pdf)

[![Augmented Paper (augmented)](https://github.com/badonhill-io/randeli/blob/main/samples/augmented/3rdParty/IoTSecurityPaperWF-IOT.augmented0.png)](https://github.com/badonhill-io/randeli/blob/main/samples/augmented/3rdParty/IoTSecurityPaperWF-IOT.pdf)


### A complete e-book (EPUB)

[![EPUB](https://github.com/badonhill-io/randeli/blob/main/samples/3rdParty/pythonlearn0.png)](samples/3rdParty/pythonlearn.epub)

[![EPUB (augmented)](https://github.com/badonhill-io/randeli/blob/main/samples/augmented/3rdParty/pythonlearn.augmented0.png)](samples/augmented/3rdParty/pythonlearn.epub)

---


Terminology
-----------

"Bionic Reading" is a trademark of Bionic Reading AG aka bionic-reading.com

`randeli` is has been developed independently of any bionic-reading.com
products or non-public information and any patents that "Bionic
Reading" hold are not applicable where this code was developed (UK,
USA, China). The patents that bionic-reading.com filed in the UK and USA
were withdrawn.

To avoid trademark infringement, randeli will use the term "augmented".

A PDF can be augmented using alternate "styles"

* The original "Bionic Reading"[TM] approach use bold fonts - in randeli
terminology "strong-text", and/or colored text.

* For OCR parsed PDFs (and also as a personal preference for well formed
PDFs), `randeli` also supports a "strong-box" style that draws a
colored box around the initial letters of a word.

An EPUB can be augmented using both bold fonts (aka "strong-text") and/or colored text.


Getting Started
===============

0) Install `randeli` and dependencies. `pip install randeli` should work or you can build a Docker image (`./scripts/build-image.sh`)

1) Create the inital configuration file and download required Apryse libraries

```
randeli bootstrap --download
```

2) Configure the Apryse token - this is required to use the PDF
parsing library. Visit https://dev.apryse.com/ to get a key

```
randeli config set --key apryse.token --value "demo:16XXXXXXXX67:....."
```

3) (optional) Set your preferred fallback font.

A lot of my papers are from LaTeX so prefer to use the Computer Modern font as a fallback.

```
randeli config set --key policy.fallback-font --value "CMU Serif"
```

4) (one off) Index all the fonts on your system - required before augment any PDFs (technically only required before using font-based augmentation,  but do it now before you forget)

```
randeli map-fonts --update-config
```

5) Augment a PDF or EPUB, repeat

```
% randeli augment --read=samples/pdflatex/simple.pdf --write-into=DIR
```

Using `write-into` will save the augmented file (PDF or EPUB) into DIR with the same name as the specified input file (i.e. DIR/simple.pdf). It should not allow you to overwrite the input file.

6) Open the augmented file using you normal viewer (i.e. Preview or Books on macOS)



Randeli Usage
=============

```
 ] randeli
Usage: randeli [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

COMMANDS:
     augment - Write an augmented PDF/EPUB
   bootstrap - Initialize randeli configuration
      config - Read and Write configuration values
     inspect - Read a PDF or EPUB and report on its structure
   map-fonts - Create fonts.map from installed fonts

For additional help on a command use

    `randeli <CMD> --help`
or
    `randeli <CMD> --hints`
```


```
 ] randeli --help
Usage: randeli [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --verbose INTEGER     Set system-wide verbosity
  --devel                   Run in development mode (additional logging)
  --cfg PATH                Path to configuration file
  --backend [apryse]        Select backend PDF library
  --apryse-token TOKEN      API Token for Apryse backend
  --font-map-file FILE      Load font map from FILE
  --log-level LOGGER=LEVEL  Override logging level for given logger
  --help                    Show this message and exit.
```

### randeli bootstrap

```
 ] randeli bootstrap --help
Usage: randeli bootstrap [OPTIONS]

  Initialize randeli configuration

Options:
  --download  Download 3rd party components
  --help      Show this message and exit.
```


### randeli augment

```
 ] randeli augment --help
Usage: randeli augment [OPTIONS]

  Write an augmented PDF/EPUB

Options:
  -i, --read PATH            Read PDF/EPUB from PATH  [required]
  --write PATH               Save augmented file to PATH
  --write-into DIR           Save augmented file into DIR (same base filename
                             as input)
  --page INTEGER             Only analyse page PAGE
  --ocr                      Enable OCR (PDF input only)
  --force-ocr                Force (whole page) OCR even if there are text
                             elements
  --ocr-engine [apryse]      Select OCR Engine
  --ocr-mode [page|element]  Select OCR Mode.
  --ocr-dpi INTEGER          (expert) Tune resolution used in OCR word
                             locations
  --override KEY:VALUE       Override config values for this run
  --keep                     Keep intermediate image files extracted by OCR
  --pdfa                     Also write a PDF/A file (PDF input only)
  --is-epub                  Force parsing input as EPUB
  --hints                    Print additional help
  --help                     Show this message and exit.
```

### randeli inspect

```
 ] randeli inspect --help
Usage: randeli inspect [OPTIONS]

  Read a PDF/EPUB and report on its structure

Options:
  -i, --read PATH       [required]
  --fonts               Print per-element font details
  --page NUMBER         Only inspect page NUMBER
  --override KEY:VALUE  Override config values from CLI
  --is-epub             Force parsing input as EPUB
  --hints               Print additional help
  --help                Show this message and exit.
```

### randeli map-fonts
```
 ] map-fonts --help
Usage: randeli map-fonts [OPTIONS]

  Create fonts.map from installed fonts

Options:
  --font-map-file FILE     Save font mapping to FILE
  --font-dir DIR           Parse fonts rooted at DIR  [required]
  --fallback-font NAME     Font NAME if font can't be found mapping
  --computer-modern ALIAS  Alias 'Computer Modern' to ALIAS
  --update-config          Add specified font-map-file into configuration file
  --alias ALIAS:FONTNAME   ALIAS aliased to 'FONTNAME'
  --echo                   Display font names/styles
  --hints
  --help                   Show this message and exit.
```

Docker
======

The docker image already has the Apryse SDK installed into it, but it still needs a license key.

Since this is a short lived executable we use docker's `--rm` flag
to avoid keeping the exited containers around wasting space. But
that requires have a permanant place to store configuration data,
so we mount a host directory onto the `/CFG` mount point in the
container

Create the configuration file on the docker host (just once)

```
docker run -it --rm -v (pwd)/cfg:/CFG randeli bootstrap --force
```

And then add the license key you've obtained.

```
docker run -it --rm -v (pwd)/cfg:/CFG randeli config set --key=apryse.token --value=demo:16xxxxxxxxx67:7da1XXXXXXXXXXXXXXX
demo:16xxxxxxxxx67:7da1XXXXXXXXXXXXXXX
```

Build the fonts map

```
docker run -it -v (pwd)/cfg:/CFG randeli map-fonts --font-map-file=/CFG/fonts.map --update-config
```

As long as you pass `-v (pwd)/cfg:/CFG` into subsequent `docker
run` commands, the configuration is stored outside of the temporary.
If you forget it will use the configuration file that is inside the
container, which will be out of date and not have a valid Apryse
token.


Map the appropriate host directores to `/IN` and `/OUT`, i.e. 

```
docker run -it --rm -v (pwd)/cfg:/CFG -v (pwd)/samples/:/IN:ro -v (pwd)/out:/OUT  randeli augment --read=/IN/pdflatex/simple.pdf --write-into /OUT
```

Samples
=======

The directory `samples` includes both input EPUB/PDFs and the
augmented versions of the inputs so you can quickly see if the
concept works for you.

Don't be too tied to the augmented colors, these are configurable.


Advanced Usage
==============


Augmenting Patents
------------------

PDFs downloaded from http://patents.google.com may have alreay been
regnerated compared to the original national patent office (i.e.
USPTO) and the augmentation isn't very good.

Better success has been obtained using PDFs downloaded directly from USPTO
and using `randeli's` built-in OCR, see
samples/augmented/3rdParty/uspto.8539484.pdf as an example.


:::
PDF Background
--------------

PDF is an unstructured format that is a stream of binary (optionally
compressed) elements. An element can be an image, text etc.

Text can be a single character, word or line. A single word can
be comprised of multiple elements.

Some PDFs are the result of scanning a paper or other PDF - so any
text has been pre-rendered into an embedded image.

:::


Well formed PDFs
----------------

If the PDF was created from LaTeX or other document processor (i.e.
Word) then reasonable results should be obtained using

    `randeli augment --read=PDF --write-into=DIR`

(LaTeX and Word both create well structured PDF and typically use
standard fonts which makes it easy to embolden automatically.

PDFs generated from XeLaTeX are still a WIP as they use a different
font format in the PDF (UTF-8 vs UTF-32).

If the input document uses custom fonts that are not installed on
the system running `randeli` then the font used to strongify the
characters will use a fallback font and it may be too distracting
when compared to the rest of the document. In this case you may
want either load the fonts onto the system and re-run `randeli map-fonts`
or use `randeli augment --override 'policy.use_strong_text=False'
--override 'policy.use_strong_box=True'`.


Scanned PDFs
------------

Scanned PDFs have no information to order to markup the text (no
font information) so we need to use OCR to extract text from images
and then add highlighted boxes at the appropriate position on the
page using

    `randeli augment --read=PDF --write-to=DIR --ocr`

The default OCR assumes that the whole document has been scanned
so performs OCR on the full page. If pages contain a mix of well-formed
text and (in-line) images to be be be OCR'ed, then use `--ocr-mode
element` (rather than the default `--ocr-mode page`).


Font Map
--------

In order to bolden the text in the output PDF using the same fonts
as the rest of the PDF we need to know what fonts are available on
the system.

If you are expecting to read TeX/LaTeX generated PDFs, you probably
want to load the CMU fonts into your Font Library. The license for
the LaTeX standard Compuer Modern fonts requires changing the name
when the format (Type1 (TTF) vs TeX) is changed. We want the
Type1 version as PDF supports that type natively.

https://www.fontsquirrel.com/fonts/computer-modern

Another good set is the "Latin Modern Roman" fonts.

While `randeli` tries its best at updating the fonts in an existing
PDF, it is not perfect and can be visually unpleasing in edge cases
(bolded characters are slight larger than their normal counterparts
so text can run together). If you fond that's the case the suggestion
is try setting `use_strong_text` to `False`
and `use_colored_text` to `True`.

EPUB documents should not be impacted as they typically use standard
HTML fonts.
