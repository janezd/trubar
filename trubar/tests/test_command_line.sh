function print_run() {
    echo "> " $1
    if [ -z $2 ]
    then
        ${1}
    else
        ${1} > $2
    fi
}

cd shell_tests
for d in */
do
    if [ ! -f $d/test.sh ] ; then continue; fi

    cd $d
    rm -rf tmp
    mkdir tmp
    ( set -e
      . test.sh
    )
    if [ $? -ne 0 ]
    then
         echo ""
         echo "*** FAIL!"
         test ! -z "$FAILED" && FAILED="$FAILED, "
         FAILED=$FAILED${d%/}
    else
         rm -rf tmp
    fi
    cd ..
    echo ""
    echo ""
done
cd ..

if [ ! -z "$FAILED" ]
then
    echo "Failed tests: $FAILED"
    exit 1
fi