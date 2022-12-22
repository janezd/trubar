echo "Template"

print_run 'trubar template translations.jaml -o tmp/template.jaml'
diff tmp/template.jaml exp/template.jaml
rm tmp/template.jaml
