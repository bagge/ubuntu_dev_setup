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

if [ -f "${HOME}/.bazelcomplete" ]; then
    # shellcheck source=/dev/null
    source "${HOME}/.bazelcomplete"
fi
