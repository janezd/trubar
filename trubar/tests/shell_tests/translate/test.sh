echo "Translate"

cp -r exp/si_translated/ tmp/si_translated_copy/
print_run 'trubar translate -s ../test_project -d tmp/si_translated translations.yaml -q'
diff -r tmp/si_translated exp/si_translated
diff -r exp/si_translated tmp/si_translated_copy
rm -r tmp/si_translated

echo "... with pattern"
mkdir tmp/si_translated
cp ../test_project/__init__.py tmp/si_translated/__init__.py
print_run 'trubar translate -s ../test_project -d tmp/si_translated translations.yaml -p submodule -q'
diff -r tmp/si_translated/submodule exp/si_translated/submodule
diff tmp/si_translated/__init__.py ../test_project/__init__.py
diff -r exp/si_translated tmp/si_translated_copy
rm -r tmp/si_translated

echo "... with static files"
mkdir tmp/si_translated
print_run 'trubar translate -s ../test_project -d tmp/si_translated translations.yaml -p submodule -q --static static_files_lan'
diff -r tmp/si_translated/a static_files_lan/a
rm -r tmp/si_translated

echo "... dry run"
print_run 'trubar translate -s ../test_project -d tmp/si_translated translations.yaml -q -n --static static_files_lan'
diff -r exp/si_translated tmp/si_translated_copy
if [ -d tmp/si_translated ]
then
  echo "Not dry."
  exit 1
fi
rm -r tmp/si_translated_copy

echo "... verbosity"
print_run 'trubar translate -s ../test_project -d si_translated_half translations.yaml -n -v 3' tmp/verb_output
diff tmp/verb_output exp/verbose3.txt
print_run 'trubar translate -s ../test_project -d si_translated_half translations.yaml -n -v 2' tmp/verb_output
diff tmp/verb_output exp/verbose2.txt
print_run 'trubar translate -s ../test_project -d si_translated_half translations.yaml -n -v 1' tmp/verb_output
diff tmp/verb_output exp/verbose1.txt
print_run 'trubar translate -s ../test_project -d si_translated_half translations.yaml -n -v 0' tmp/verb_output
if [[ ! -z $(cat tmp/verb_output) ]] ; then
    echo "not quiet"
    exit 1
fi
print_run 'trubar translate -s ../test_project -d si_translated_half translations.yaml -n -q' tmp/verb_output
if [[ ! -z $(cat tmp/verb_output) ]] ; then
    echo "not quiet"
    exit 1
fi
print_run 'trubar translate -s ../test_project -d exp/si_translated translations.yaml -n -v 1' tmp/verb_output
diff tmp/verb_output exp/verbose_no_changes.txt
print_run 'trubar translate -s ../test_project -d exp/si_translated translations.yaml -n -v 0' tmp/verb_output
if [[ ! -z $(cat tmp/verb_output) ]] ; then
    echo "not quiet"
    exit 1
fi
rm tmp/verb_output