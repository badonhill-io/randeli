#! /bin/bash
#

THIS_SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

SAMPLEDIR=${THIS_SCRIPT_DIR}/samples
OUTDIR=${SAMPLEDIR}/augmented

FONTMAP=$(randeli config get --key=policy.font-map-file)

if [ ! -r "${FONTMAP}" ]
then
    echo "Missing fonts.json. Have you generated it ? (i.e. randeli map-fonts)"
    exit 1
fi

mkdir -p ${OUTDIR}

ARGS="--font-map-file ${FONTMAP}"


function augment_pdf()
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
            args="--ocr --ocr-mode page --force-ocr --override policy.strong_box_height=0.6"
        fi

        echo randeli $ARGS augment --read $pdf --write ${OUTDIR}/$pdf $args
        randeli $ARGS augment --read $pdf --write ${OUTDIR}/$pdf $args

        echo "<="
        echo ""

    done
}

function augment_epub()
{
    dir=$1
    for epub in $dir/*.epub
    do

        echo "=> Augmenting $epub"

        base=$(basename $epub)

        args=""

        echo randeli $ARGS augment --read $epub --write ${OUTDIR}/$epub $args
        randeli $ARGS augment --read $epub --write ${OUTDIR}/$epub $args

        echo "<="
        echo ""

    done
}

(
    cd ${SAMPLEDIR}

    for dir in 3rdParty pdflatex xelatex
    do
        mkdir -p ${OUTDIR}/$dir
        augment_pdf $dir
    done

    for dir in 3rdParty epub
    do
        mkdir -p ${OUTDIR}/$dir
        augment_epub $dir
    done
)
