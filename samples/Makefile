

SRCs := simple.md bold.md paragraph.md mixed.md alt-font.md
pdfs_ :=$(SRCs:.md=.pdf)
epubs_ :=$(SRCs:.md=.epub)

# improves pandoc's image support
EXTS := "+link_attributes"

PDFs := $(addprefix pdflatex/,$(pdfs_)) $(addprefix xelatex/,$(pdfs_))
EPUBs := $(addprefix epub/,$(epubs_))

all:: $(PDFs) $(EPUBs)

clean::
	rm -f $(PDFs)

real-clean::
	rm -f $(PDFs) augmented/*.pdf

pdflatex/%.pdf: %.md 
	cat $< | sed -e 's/BASEFONT/fontfamily: dejavu/' -e 's/FONTOPTIONS//' -e 's/FONTEXT//' -e 's/UPRIGHTFONT//' -e 's/BOLDFONT//' -e 's/BOLDITALICFONT//' -e 's/ITALICFONT//'  | pandoc --from markdown$(EXTS) --to pdf --pdf-engine pdflatex -o $@

xelatex/%.pdf: %.md 
	cat $< | sed -e 's/BASEFONT/mainfont: DejaVuSerif/' -e 's/FONTOPTIONS/mainfontoptions:/' -e 's/FONTEXT/- Extension=.ttf/' -e 's/UPRIGHTFONT/- UprightFont=*/' -e 's/BOLDFONT/- BoldFont=*-Bold/' -e 's/BOLDITALICFONT/- BoldItalicFont=*-BoldItalic/' -e 's/ITALICFONT/- ItalicFont=*-Italic/' | pandoc --from markdown$(EXTS) --to pdf --pdf-engine xelatex -o $@


epub/%.epub: %.md 
	cat $< | sed -e 's/BASEFONT/fontfamily: dejavu/' -e 's/FONTOPTIONS//' -e 's/FONTEXT//' -e 's/UPRIGHTFONT//' -e 's/BOLDFONT//' -e 's/BOLDITALICFONT//' -e 's/ITALICFONT//'  | pandoc --from markdown$(EXTS) --to epub -o $@

