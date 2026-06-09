#!/usr/bin/env bash
set -u

BASE_URL="${BASE_URL:-http://localhost:9000}"
ITERACIONES="${ITERACIONES:-5}"
N_RESULTADOS="${N_RESULTADOS:-4}"

tmpfile="$(mktemp)"
trap 'rm -f "$tmpfile"' EXIT

run_case() {
  local nombre="$1"
  local endpoint="$2"
  local payload="$3"

  echo
  echo "=================================================="
  echo "Caso: $nombre"
  echo "Endpoint: $endpoint"
  echo "Iteraciones: $ITERACIONES"
  echo "=================================================="

  : > "$tmpfile"

  for i in $(seq 1 "$ITERACIONES"); do
    tiempo=$(curl -sS -o /dev/null \
      -w "%{time_total}" \
      -X POST "${BASE_URL}${endpoint}" \
      -H "Content-Type: application/json" \
      -d "$payload")

    echo "$tiempo" | tee -a "$tmpfile"
  done

  awk '
    BEGIN {min=999999; max=0; sum=0; n=0}
    {
      x=$1+0;
      if (x < min) min=x;
      if (x > max) max=x;
      sum+=x;
      n+=1;
    }
    END {
      if (n > 0) {
        avg=sum/n;
        printf("min=%.3fs | avg=%.3fs | max=%.3fs | n=%d\n", min, avg, max, n);
      } else {
        print "Sin datos";
      }
    }
  ' "$tmpfile"
}

run_case \
  "Forense" \
  "/forense/consulta" \
  "{\"pregunta\":\"¿Qué es la cadena de custodia?\",\"n_resultados\":${N_RESULTADOS}}"

run_case \
  "Honorarios" \
  "/honorarios/consulta" \
  "{\"pregunta\":\"¿Cómo se regulan los honorarios periciales?\",\"n_resultados\":${N_RESULTADOS}}"

run_case \
  "Operativa" \
  "/operativa/consulta" \
  "{\"pregunta\":\"Redactame un mail para pedir una prórroga en la entrega del informe\",\"n_resultados\":${N_RESULTADOS}}"

run_case \
  "Orquestador forense" \
  "/orquestador/consulta" \
  "{\"pregunta\":\"¿Cómo preservar evidencia digital?\",\"n_resultados\":${N_RESULTADOS}}"

run_case \
  "OpenAI compat" \
  "/v1/chat/completions" \
  "{\"model\":\"multiagente-local\",\"messages\":[{\"role\":\"user\",\"content\":\"Redactame un mail para pedir prórroga\"}]}"

echo
echo "=================================================="
echo "Snapshot de recursos Docker"
echo "=================================================="
docker stats --no-stream ollama api-multiagente chromadb open-webui 2>/dev/null || true