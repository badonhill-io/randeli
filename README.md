Randeli
=======

Modify PDFs to help make them easier to read and understand for
people with ADD/ADHD.

This is primarily targeted at academic papers and patents.

Modifying Patents
-----------------

PDFs downloaded from http://patents.google.com may have alreay been
regnerated compared to the original national patent office (i.e.
USPTO).

More success has been obtained using PDFs downloaded idirectly from USPTO
and using OCR.


Understanding PDFs
==================

PDF is an unstructured format that is a stream of binary (optionally
compressed) elements. An element can be an image, text etc.

Text can be a single character, word or line.

Some PDFs are the result of scanning a paper or other PDF - so any
text has been rendered into an image.

Well formed DPFs
----------------

If the PDF was created from LaTeX or other document processor (i.e.
Word) then reasonable results should be obtained using

    `randeli update --read=PDF --write-to=DIR`

(LaTeX and Word both create well structured PDF and typically use
standard fonts which makes it easy to enbolden automatically.

PDFs generated from XeLaTeX are still a WIP.)

If the input document uses custom fonts that are not installed on
the system running `randeli` then the font used to bolden the
characters will use a fallback font and it may be too distracting
when compared to the rest of the document. In this case you may
want either load the fonts onto the system and re-run `randeli map-fonts`
or use `randeli update` with the flag `--boxify`.

Scanned PDFs
------------

Scanned PDFs have no information to order to markup the text (no
font information) so we need to use OCR to extract text from images
and then add highlighted boxes at the appropriate position on the
page using

    `randeli update --read=PDF --write-to=DIR --ocr`

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


Getting Started
===============


1) Create the inital configuration file

```
randeli setup
```

2) Configure the Apryse token - this is required to use the PDF
parsing library. Visit https://dev.apryse.com/ to get a key

```
randeli config set --key apryse.token --value "demo:1684698886167:....."
```

3) (optional) Set your preferred fallback font.

A lot of my papers are from LaTeX so prefer to use the Computer Modern font as a fallback.

```
randeli config set --key policy.fallback-font --value "CMU Serif"
```

4) (one off) Index all the fonts on your system - required before updating any PDFs

``` 
randeli map-fonts \
    --font-map-file fonts.json \
    --font-dir ~/Library/Fonts/ \
    --font-dir /Library/Fonts/ \
    --font-dir /System/Library/Fonts/ \
    --update-config
```


