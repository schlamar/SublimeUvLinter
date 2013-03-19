TODO
====

- Remove linter instances `on_close`.
- linter for TODO notes: grep -n -e "TODO\|FIXME" filename
- Elaborate if it makes sense to configure linters in settings instead
  of sub classing. `flake8` would be fine, but others might require more information than subprocess arguments and regex pattern.
