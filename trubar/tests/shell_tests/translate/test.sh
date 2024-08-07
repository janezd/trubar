echo "Translate"

cp -r exp/si_translated/ tmp/si_translated_copy/
print_run 'trubar translate -s ../test_project -d tmp/si_translated translations.yaml -q'
diff -r tmp/si_translated exp/si_translated
diff -r exp/si_translated tmp/si_translated_copy
rm -r tmp/si_translated

echo "... in place"
cp -r ../test_project tmp/
print_run 'trubar translate -s tmp/test_project -i translations.yaml -q'
diff -r tmp/test_project exp/si_translated
rm -r tmp/test_project

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

echo "... with multiple static files"
mkdir tmp/si_translated
print_run 'trubar translate -s ../test_project -d tmp/si_translated translations.yaml -p submodule -q --static static_files_lan --static static_files_ban'
diff -r tmp/si_translated/a static_files_lan/a
diff -r tmp/si_translated/pet_podgan.txt static_files_ban/pet_podgan.txt
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

print_run 'trubar --conf multilingual/trubar-config.yaml translate -s ../test_project -d tmp/multilingual translations.jaml' tmp/verb_output
diff -r exp/multilingual tmp/multilingual
rm -r tmp/multilingual

echo "... error: no -d or -i"
set +e
print_run 'trubar translate -s .. translations.yaml' tmp/output.txt
check_exit_code

echo "... error: both -i and -d are given"
set +e
print_run 'trubar translate -s .. -d tmp/si_foo -i translations.yaml' tmp/output.txt
check_exit_code
grep -q "incompatible" tmp/output.txt
check_exit_code "Invalid error message" -ne
set -e
rm tmp/output.txt

echo "... error: static files does not exist"
set +e
print_run 'trubar translate -s .. -d tmp/si_foo translations.yaml --static no_such_static' tmp/output.txt
check_exit_code
grep -q "no_such_static" tmp/output.txt
check_exit_code "Invalid error message" -ne
set -e
rm tmp/output.txt

echo "... error: one of static files does not exist"
set +e
print_run 'trubar translate -s .. -d tmp/si_foo translations.yaml --static static_files_lan --static no_such_static --static static_files_ban' tmp/output.txt
check_exit_code
grep -q "no_such_static" tmp/output.txt
check_exit_code "Invalid error message" -ne
set -e
rm tmp/output.txt

echo "... error: invalid source dir + correction"
set +e
print_run 'trubar translate -s .. -d tmp/si_foo translations.yaml' tmp/output.txt
check_exit_code
grep -q "instead" tmp/output.txt
check_exit_code "No recommendation is given" -ne
set -e
rm tmp/output.txt
