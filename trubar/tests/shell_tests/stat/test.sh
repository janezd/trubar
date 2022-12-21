# to be run from trubar/tests/shell_test_files

echo "Stat"

print_run 'trubar stat translations.yaml' tmp/all.txt
diff tmp/all.txt exp/all.txt

print_run 'trubar stat translations.yaml -p submodule' tmp/submodule.txt
diff tmp/submodule.txt exp/submodule.txt

print_run 'trubar stat translations.yaml -p nomodule' tmp/nomodule.txt
diff tmp/nomodule.txt exp/nomodule.txt