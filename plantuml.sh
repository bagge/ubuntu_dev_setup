#!/usr/bin/env bash

set -euo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
plantuml_jar="${PLANTUML_JAR:-${script_dir}/plantuml.jar}"

if [[ -n "${PLANTUML_JAVA:-}" ]]; then
    java_bin="${PLANTUML_JAVA}"
elif command -v java >/dev/null 2>&1; then
    java_bin="$(command -v java)"
elif [[ -x /opt/homebrew/opt/openjdk/bin/java ]]; then
    java_bin=/opt/homebrew/opt/openjdk/bin/java
elif [[ -x /usr/local/opt/openjdk/bin/java ]]; then
    java_bin=/usr/local/opt/openjdk/bin/java
else
    echo "plantuml: java not found" >&2
    exit 127
fi

exec "${java_bin}" -jar "${plantuml_jar}" "$@"
