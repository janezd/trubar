echo "Update-table"

print_run 'trubar --conf multilingual/trubar-config.yaml translate -s ../test_project -d tmp translations.jaml' > /dev/null
print_run "trubar --conf multilingual/trubar-config.yaml update-table -o tmp/i18n/Slovenian.json new-translations.jaml" tmp/verb_output
diff -r exp tmp/i18n
