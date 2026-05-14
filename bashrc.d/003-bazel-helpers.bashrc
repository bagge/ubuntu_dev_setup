#!/usr/bin/env bash

bazel_sha256 () {(
    set -e

    usage () {(
        echo -e "Function to calculate a sha256 formatted for bazel"
        echo -e "i.e. base64 encoded and with \"sha256-\" prefixed."
        echo -e "Usage: bazel_sha256 [-h] <path>"
        echo -e "        -h: prints this message"
        echo -e "    <path>: path to the file to calculate checksum for"
    )}

    local OPTIND opt
    while getopts ":h" opt ; do
        case "${opt}" in
            h) usage
               exit 0
                ;;
            ?) echo -e "Invalid option."
               usage
               exit 1
                ;;
        esac
    done
    shift $((OPTIND-1))

    if [ -z "${1:-}" ]; then
        echo "No path specified"
        usage
        exit 1
    fi

    sha256sum "$1" | cut -d' ' -f1 | xxd -r -p | base64 | sed 's/^/sha256-/'
)}

regenerate_bazel_completion () {(
    set -e

    usage () {(
        echo -e "Function to regenerate bazel tab completion"
        echo -e "Usage: regenerate_bazel_completion [-h] [-v version] <path>"
        echo -e "        -h: prints this message"
        echo -e "-v version: version of bazel to use"
        echo -e "    <path>: path to a directory containing a .bazelversion file"
        echo -e "            (not used if -v is used)"
    )}

    local OPTIND opt VERSION
    while getopts ":hv:" opt ; do
        case "${opt}" in
            h) usage
               exit 0
                ;;
            v) VERSION=${OPTARG}
                ;;
            ?) echo -e "Invalid option."
               usage
               exit 1
                ;;
        esac
    done
    shift $((OPTIND-1))

    if [ -z "${VERSION:-}" ]; then
        if [ -z "${1:-}" ]; then
            echo "No path or version specified"
            usage
            exit 1
        fi
        if [ ! -f "$1/.bazelversion" ]; then
            echo "Missing .bazelversion file in $1"
            exit 1
        fi
        VERSION=$(cat "$1/.bazelversion")
    fi

    rm -f "${HOME}/.bazelcomplete"

    {
        curl -fsSL "https://raw.githubusercontent.com/bazelbuild/bazel/${VERSION}/scripts/bazel-complete-header.bash"
        curl -fsSL "https://raw.githubusercontent.com/bazelbuild/bazel/${VERSION}/scripts/bazel-complete-template.bash"
        bazel help completion
    } >> "${HOME}/.bazelcomplete"
    # shellcheck source=/dev/null
    source "${HOME}/.bazelcomplete"
)}

show_path () {(
    set -e

    usage () {(
        echo -e "Show the dependency path between two bazel targets as a graph."
        echo -e "Usage: show_path [-h] [-a] <target1> <target2>"
        echo -e "        -h: prints this message"
        echo -e "        -a: use allpaths instead of somepath"
        echo -e "  <target1>: the starting bazel target"
        echo -e "  <target2>: the ending bazel target"
    )}

    local OPTIND opt query_func="somepath"
    while getopts ":ha-:" opt ; do
        case "${opt}" in
            h) usage
               exit 0
                ;;
            a) query_func="allpaths"
                ;;
            -) case "${OPTARG}" in
                   all) query_func="allpaths" ;;
                   *) echo "Invalid option: --${OPTARG}"
                      usage
                      exit 1 ;;
               esac
                ;;
            ?) echo "Invalid option: -${OPTARG}"
               usage
               exit 1
                ;;
        esac
    done
    shift $((OPTIND-1))

    local missing=0
    for cmd in bazel dot kitten; do
        if ! command -v "$cmd" > /dev/null 2>&1; then
            echo "Required command not found: $cmd"
            missing=1
        fi
    done
    if [ "$missing" -eq 1 ]; then
        exit 1
    fi

    if [ -z "${1:-}" ] || [ -z "${2:-}" ]; then
        echo "Two bazel targets are required"
        usage
        exit 1
    fi

    if ! bazel info workspace > /dev/null 2>&1; then
        echo "Not inside a bazel workspace"
        exit 1
    fi

    local target1="$1" target2="$2"
    local bazel_stderr bazel_stdout
    bazel_stderr=$(mktemp)
    bazel_stdout=$(mktemp)
    trap 'rm -f "$bazel_stderr" "$bazel_stdout"' EXIT
    if ! bazel query "${query_func}(${target1}, ${target2})" --output graph >"$bazel_stdout" 2>"$bazel_stderr"; then
        echo "bazel query failed:" >&2
        cat "$bazel_stderr" >&2
        exit 1
    fi

    dot -Tpng < "$bazel_stdout" | kitten icat
)}

if [ -f "${HOME}/.bazelcomplete" ]; then
    # shellcheck source=/dev/null
    source "${HOME}/.bazelcomplete"
fi
