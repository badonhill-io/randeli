

SRCs := simple.md bold.md paragraph.md
pdfs_ :=$(SRCs:.md=.pdf)

EXTS := "+link_attributes"

PDFs := $(addprefix latex/,$(pdfs_)) $(addprefix xelatex/,$(pdfs_))

all:: $(PDFs)

latex/%.pdf: %.md 
	cat $< | pandoc --from markdown$(EXTS) --to pdf --pdf-engine pdflatex -o $@

xelatex/%.pdf: %.md 
	cat $< | pandoc --from markdown$(EXTS) --to pdf --pdf-engine xelatex -o $@

