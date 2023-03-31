function print_run() {
    echo "> " $1
    if [ -z $2 ]
    then
        ${1}
    else
        ${1} > $2 2>&1
    fi
}

sysdiff=`which diff`
function diff() {
    oldstate="$(set +o)"
    set +e
    eval $sysdiff "$@" > /dev/null
    if [ $? -ne 0 ]
    then
        echo diff $@
        eval $sysdiff "$@"
        exit 1
    fi
    eval "$oldstate"
}

function check_exit_code() {
  # Test that exit code is nonzero (if $2 is omitted) or zero (if $2 is -ne)
  # $1 is error message; see default below :)
    if [ $? ${2:--eq} 0 ]
    then
        echo ${1:-"Non-zero exit code expected"}
        exit 1
    fi
}

cd shell_tests
for d in ${1:-*}/
do
    if [ ! -f $d/test.sh ]; then continue; fi

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
else
    echo "Success."
fi
