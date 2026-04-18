#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
TEMP_DUMP_FILE=""

usage() {
  cat <<'EOF'
Usage:
  NEON_DATABASE_URL="postgresql://user:password@ep-...neon.tech/neondb?sslmode=require" \
  ./scripts/push_local_db_to_neon.sh

Or:
  ./scripts/push_local_db_to_neon.sh "postgresql://user:password@ep-...neon.tech/neondb?sslmode=require"

Notes:
  - Use a Neon direct connection string for restore, not a -pooler host.
  - Local database settings are read from the project's .env file.
EOF
}

cleanup() {
  if [[ -n "${TEMP_DUMP_FILE}" && -f "${TEMP_DUMP_FILE}" ]]; then
    rm -f "${TEMP_DUMP_FILE}"
  fi
}

trap cleanup EXIT

read_env_value() {
  local key="$1"
  local value

  value="$(grep -m1 "^${key}=" "${ENV_FILE}" | cut -d= -f2- || true)"
  value="${value%$'\r'}"
  value="${value#\"}"
  value="${value%\"}"
  value="${value#\'}"
  value="${value%\'}"

  printf '%s' "${value}"
}

ensure_sslmode() {
  local url="$1"

  if [[ "${url}" == *"sslmode="* ]]; then
    printf '%s' "${url}"
    return 0
  fi

  if [[ "${url}" == *"?"* ]]; then
    printf '%s&sslmode=require' "${url}"
  else
    printf '%s?sslmode=require' "${url}"
  fi
}

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Aborting." >&2
  exit 1
fi

TARGET_URL="${NEON_DATABASE_URL:-${1:-}}"

if [[ -z "${TARGET_URL}" ]]; then
  usage
  exit 1
fi

if [[ "${TARGET_URL}" == *"-pooler."* ]]; then
  echo "Use Neon direct connection details for restore, not the pooled (-pooler) host." >&2
  exit 1
fi

for cmd in pg_isready pg_dump pg_restore grep cut; do
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "Missing required command: ${cmd}" >&2
    exit 1
  fi
done

LOCAL_HOST="$(read_env_value "DB_HOST")"
LOCAL_PORT="$(read_env_value "DB_PORT")"
LOCAL_DB="$(read_env_value "DB_DATABASE")"
LOCAL_USER="$(read_env_value "DB_USERNAME")"
LOCAL_PASSWORD="$(read_env_value "DB_PASSWORD")"
TARGET_URL="$(ensure_sslmode "${TARGET_URL}")"
TEMP_DUMP_FILE="$(mktemp /tmp/imagnus-neon-XXXXXX.dump)"

if [[ -z "${LOCAL_HOST}" || -z "${LOCAL_PORT}" || -z "${LOCAL_DB}" || -z "${LOCAL_USER}" ]]; then
  echo "Local database settings are incomplete in ${ENV_FILE}." >&2
  exit 1
fi

echo "Checking local PostgreSQL connection..."
PGPASSWORD="${LOCAL_PASSWORD}" pg_isready \
  -h "${LOCAL_HOST}" \
  -p "${LOCAL_PORT}" \
  -d "${LOCAL_DB}" \
  -U "${LOCAL_USER}" >/dev/null

echo "Creating dump from local database ${LOCAL_DB}..."
PGPASSWORD="${LOCAL_PASSWORD}" pg_dump \
  -h "${LOCAL_HOST}" \
  -p "${LOCAL_PORT}" \
  -U "${LOCAL_USER}" \
  -d "${LOCAL_DB}" \
  --format=custom \
  --no-owner \
  --no-privileges \
  --verbose \
  --file "${TEMP_DUMP_FILE}"

echo "Restoring dump into Neon..."
pg_restore \
  --clean \
  --if-exists \
  --exit-on-error \
  --no-owner \
  --no-privileges \
  --verbose \
  --dbname="${TARGET_URL}" \
  "${TEMP_DUMP_FILE}"

echo "Local PostgreSQL data has been restored into Neon."
