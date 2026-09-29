#!/usr/bin/env bash
# Vercel Ignored Build Step.
# Exit 0: skip the build. Exit 1: run the build.
# Production and main always build. Anything that is not generated parcel
# data builds. If the diff cannot be determined, build.

set -uo pipefail

build() {
  echo "vercel-ignore-build: build ($*)"
  exit 1
}

skip() {
  echo "vercel-ignore-build: skip ($*)"
  exit 0
}

# Paths taken from parcel-batch pull requests #88–#92 (and the same layout
# on earlier batches): county tiles and geojson, county.json, lookup.json,
# market meta.json, coverage.md, index.json, rural-oz-retry-result.json,
# the county catalog, and the state parcel-card folders those batches update.
# Orlando uses the same tile/geojson output. public/data/ is the static
# data prefix. App config under data/ (zoning-config.json, flu-config.json,
# source catalogs) is not in this list, so those changes build.
is_data_only_path() {
  case "$1" in
    data/fixtures/market-parcels | data/fixtures/market-parcels/*)
      return 0
      ;;
    data/fixtures/orlando-parcels | data/fixtures/orlando-parcels/*)
      return 0
      ;;
    data/market-parcel-counties.json)
      return 0
      ;;
    data/al-parcel-cards | data/al-parcel-cards/*)
      return 0
      ;;
    data/ga-parcel-cards | data/ga-parcel-cards/*)
      return 0
      ;;
    data/nc-parcel-cards | data/nc-parcel-cards/*)
      return 0
      ;;
    data/sc-parcel-cards | data/sc-parcel-cards/*)
      return 0
      ;;
    data/tn-parcel-cards | data/tn-parcel-cards/*)
      return 0
      ;;
    public/data | public/data/*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

# Read a NUL-delimited --name-status stream.
# 0: every path is data-only (or the diff is empty)
# 1: a non-data path was found
# 2: the status stream could not be read
classify_diff() {
  local file="$1"
  local status path oldpath found=0
  while true; do
    if ! IFS= read -r -d '' status; then
      break
    fi
    found=1
    case "$status" in
      R*|C*)
        IFS= read -r -d '' oldpath || return 2
        IFS= read -r -d '' path || return 2
        if ! is_data_only_path "$oldpath" || ! is_data_only_path "$path"; then
          echo "vercel-ignore-build: non-data change ${oldpath} -> ${path}"
          return 1
        fi
        ;;
      [AMDTCUXB])
        IFS= read -r -d '' path || return 2
        if ! is_data_only_path "$path"; then
          echo "vercel-ignore-build: non-data change ${path}"
          return 1
        fi
        ;;
      *)
        echo "vercel-ignore-build: unrecognized diff status ${status}"
        return 2
        ;;
    esac
  done <"$file"
  if [ "$found" -eq 0 ]; then
    echo "vercel-ignore-build: diff is empty"
  fi
  return 0
}

if [ "${VERCEL_ENV:-}" = "production" ] || [ "${VERCEL_GIT_COMMIT_REF:-}" = "main" ] || [ "${VERCEL_GIT_COMMIT_REF:-}" = "refs/heads/main" ]; then
  build "VERCEL_ENV=${VERCEL_ENV:-unset} VERCEL_GIT_COMMIT_REF=${VERCEL_GIT_COMMIT_REF:-unset}"
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  build "not a git checkout"
fi

have_origin_main() {
  git rev-parse --verify --quiet origin/main >/dev/null 2>&1
}

# Vercel clones shallowly, so origin/main is often missing or too thin for a
# merge-base. Fetch a bounded history, then fall back to a two-dot diff of
# the tips, which does not need a merge-base.
if ! have_origin_main || ! git merge-base origin/main HEAD >/dev/null 2>&1; then
  echo "vercel-ignore-build: fetching origin/main"
  git fetch --no-tags --depth=100 origin main || echo "vercel-ignore-build: fetch origin main failed"
  if have_origin_main && ! git merge-base origin/main HEAD >/dev/null 2>&1; then
    git fetch --no-tags --deepen=400 origin main || true
    git fetch --no-tags --deepen=400 origin || true
  fi
fi

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

if have_origin_main; then
  if git merge-base origin/main HEAD >/dev/null 2>&1; then
    echo "vercel-ignore-build: diff origin/main...HEAD"
    if ! git diff -z --name-status origin/main...HEAD >"$tmp"; then
      build "git diff against origin/main failed"
    fi
  else
    echo "vercel-ignore-build: no merge-base; diff origin/main HEAD"
    if ! git diff -z --name-status origin/main HEAD >"$tmp"; then
      build "git diff against origin/main failed"
    fi
  fi
elif [ -n "${VERCEL_GIT_PREVIOUS_SHA:-}" ]; then
  sha="${VERCEL_GIT_PREVIOUS_SHA}"
  if ! git cat-file -e "${sha}^{commit}" >/dev/null 2>&1; then
    git fetch --no-tags --depth=50 origin "$sha" || echo "vercel-ignore-build: fetch previous SHA failed"
  fi
  if ! git cat-file -e "${sha}^{commit}" >/dev/null 2>&1; then
    build "cannot resolve VERCEL_GIT_PREVIOUS_SHA"
  fi
  echo "vercel-ignore-build: diff ${sha} HEAD"
  if ! git diff -z --name-status "$sha" HEAD >"$tmp"; then
    build "git diff against VERCEL_GIT_PREVIOUS_SHA failed"
  fi
else
  build "cannot determine diff base"
fi

classify_diff "$tmp"
class=$?
if [ "$class" -eq 0 ]; then
  skip "every changed file is generated parcel data"
fi
if [ "$class" -eq 1 ]; then
  build "code, config, test, or other non-data change"
fi
build "diff could not be read"
