#! /bin/bash
#

THIS_SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

SAMPLEDIR=${THIS_SCRIPT_DIR}/samples
OUTDIR=${SAMPLEDIR}/augmented

FONTMAP=${THIS_SCRIPT_DIR}/fonts.json

if [ ! -r ${FONTMAP} ]
then
    echo "Missing fonts.json. Have you generated it ? (i.e. randeli map-fonts)"
    exit 1
fi

mkdir -p ${OUTDIR}

ARGS="--font-map-file ${FONTMAP}"


function augment()
{
    dir=$1

    for pdf in $dir/*.pdf
    do

        echo "=> Augmenting $pdf"

        base=$(basename $pdf)

        args=""

        if [ "${base}" == "uspto.8539484.pdf" ]
        then
            args="--ocr"
        fi
        
        if [ "${base}" == "mixed.pdf" ]
        then
            args="--ocr --ocr-mode element --ocr-dpi 96"
        fi

        # try this???
        if [ "${dir}" == "xelatex" ]
        then
            args="--ocr --ocr-mode page"
        fi

        echo randeli $ARGS augment --read $pdf --write ${OUTDIR}/$pdf $args
        randeli $ARGS augment --read $pdf --write ${OUTDIR}/$pdf $args

        echo "<="
        echo ""

    done
}

(
    cd ${SAMPLEDIR}

    # xelatex is not working yet
    for dir in 3rdParty pdflatex xelatex
    do
        mkdir -p ${OUTDIR}/$dir
        augment $dir
    done
)
