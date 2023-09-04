

SRCs := simple.md bold.md paragraph.md
pdfs_ :=$(SRCs:.md=.pdf)

PDFs := $(addprefix latex/,$(pdfs_)) $(addprefix xelatex/,$(pdfs_))

all:: $(PDFs)

latex/%.pdf: %.md 
	cat $< | pandoc --from markdown --to pdf --pdf-engine pdflatex -o $@

xelatex/%.pdf: %.md 
	cat $< | pandoc --from markdown --to pdf --pdf-engine xelatex -o $@

