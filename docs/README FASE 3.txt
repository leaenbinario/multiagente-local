# Multiagente local

Sistema local de agentes de IA para trabajo pericial, asistencia operativa y gestión de causas judiciales, con enfoque fuerte en privacidad y control total de la información.

## Objetivo

Construir un ecosistema de agentes inteligentes que funcione en infraestructura local para:

- asistencia personal y operativa;
- apoyo forense e informático;
- gestión de causas judiciales;
- redacción de mensajes y escritos;
- memoria local de trabajo;
- futura expansión a otros dominios como SEO, docencia y trading.

## Principios

- Todo lo sensible queda dentro del entorno local.
- Los datos de causas, clientes, escritos y memoria no salen a servicios externos salvo configuración explícita.
- La interfaz web consume un backend local compatible con OpenAI.
- La arquitectura está diseñada para crecer por módulos.

## Arquitectura

### Servicios

- `ollama`: motor local para modelos LLM y embeddings.
- `chromadb`: base vectorial local para recuperación semántica.
- `api-multiagente`: orquestador principal y backend OpenAI-compatible.
- `openclaw-causas`: servicio especializado en fichas de causas, contactos, resúmenes e historial.
- `open-webui`: interfaz web para conversar con el sistema local.
- `whisper-worker`: procesamiento opcional de audio y video.

### Flujo general

1. El usuario consulta desde Open WebUI o desde un cliente propio.
2. `api-multiagente` detecta la intención.
3. Si la consulta corresponde a causas, deriva a `openclaw-causas`.
4. Si corresponde a forense, operativa o honorarios, deriva al agente adecuado.
5. Si requiere memoria local, consulta el archivo persistente.
6. La respuesta vuelve al cliente con el resultado y, cuando aplica, fuentes o metadatos internos.

## Funcionalidades

### Agente forense
- apoyo en análisis forense digital;
- cadena de custodia;
- integridad y hashes;
- metadatos y evidencias.

### Agente operativa
- redacción breve de escritos;
- notas al juzgado;
- seguimiento de expedientes;
- apoyo administrativo general.

### Agente honorarios
- regulación de honorarios;
- anticipos;
- liquidaciones;
- apoyo contable básico.

### Memoria local
- guardar información útil del trabajo;
- buscar recuerdos por clave o contenido;
- mantener contexto persistente sin depender de la nube.

### Causas
- crear causa;
- actualizar causa;
- buscar y listar causas;
- ver resumen;
- consultar historial;
- registrar contactos;
- sugerir email de seguimiento;
- sugerir WhatsApp de seguimiento.

## Endpoints

### Consulta general
- `POST /consulta`
- `POST /orquestador/consulta`

### Agentes
- `POST /forense/consulta`
- `POST /operativa/consulta`
- `POST /honorarios/consulta`
- `POST /asistente/consulta`
- `POST /contador/consulta`

### Memoria
- `POST /memoria/guardar`
- `POST /memoria/buscar`

### Causas
- `GET /causas`
- `GET /causas/buscar`
- `GET /causas/{id_causa}`
- `POST /causas`
- `PUT /causas/{id_causa}`
- `POST /causas/{id_causa}/contactos`
- `GET /causas/{id_causa}/historial`
- `GET /causas/{id_causa}/resumen`
- `POST /causas/resumen`
- `POST /causas/sugerir-email`
- `POST /causas/sugerir-whatsapp`

### Compatibilidad OpenAI
- `GET /v1/models`
- `POST /v1/chat/completions`
- `GET /models`
- `POST /chat/completions`

## Variables de entorno

```env
OLLAMA_BASE_URL=http://ollama:11434
CHROMA_HOST=chromadb
CHROMA_PORT=8000
OPENCLAW_CAUSAS_URL=http://openclaw-causas:9100
API_HOST=0.0.0.0
API_PORT=9000

OLLAMA_PORT=11434
CHROMA_PORT_HOST=8000
OPENWEBUI_PORT=3000

EMBEDDING_MODEL=nomic-embed-text:latest
ROUTING_MIN_SCORE=0.35
ROUTING_MIN_DIFF=0.03
DEFAULT_N_RESULTADOS=4

OPENAI_API_KEY=dummy-key
```

## Docker Compose

El stack se ejecuta con Docker Compose y persiste datos en volúmenes locales:

- `./volumes/ollama`
- `./volumes/chromadb`
- `./volumes/open-webui`
- `./shared-data`
- `./api-multiagente/data`

### Arranque

```bash
docker compose up -d --build
```

### Estado

```bash
docker compose ps
```

### Logs

```bash
docker compose logs -f api-multiagente
docker compose logs -f openclaw-causas
docker compose logs -f ollama
```

## Casos de uso

### Consulta forense
“Cómo verifico la integridad de una evidencia digital?”

### Seguimiento de causa
“Mostrame el historial de la causa causa-1234”

### Borrador de WhatsApp
“Sugerime un whatsapp de seguimiento para la causa causa-1234”

### Memoria
“Qué recordás de mis preferencias de trabajo?”

## Privacidad

Este sistema está diseñado para uso local. La información sensible de clientes, causas y escritos se procesa dentro de la infraestructura propia del usuario.

## Estado de la Fase 3

Esta fase consolida:

- orquestación local entre agentes;
- gestión de causas con WhatsApp y email;
- backend OpenAI-compatible para Open WebUI;
- memoria persistente local;
- base para crecer hacia nuevos agentes especializados.

## Próximos pasos

- Fase 4: modularización del backend.
- Fase 5: agentes auxiliares y herramientas.
- Fase 6: expansión a SEO, docencia y trading.
