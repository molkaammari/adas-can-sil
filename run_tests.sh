#!/usr/bin/env bash
#
# run_tests.sh — Lance pytest en isolant l'environnement ROS.
#
# Contexte : ROS 2 installe des plugins pytest (launch_testing) qui
#           cassent pytest dans notre venv. On désactive le chargement
#           automatique des plugins externes.

set -e

cd "$(dirname "$0")"

# Activer le venv si nécessaire
if [ -z "$VIRTUAL_ENV" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

# Désactiver le chargement auto des plugins externes
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

# Lancer pytest avec les arguments passés
exec pytest "$@"
