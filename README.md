# Multiagente local

Ecosistema local de agentes inteligentes para asistencia operativa, informática forense, gestión de causas judiciales y memoria de trabajo, con foco fuerte en privacidad, control local de la información y crecimiento modular.

## Objetivo

Este proyecto busca construir un sistema multiagente que funcione en infraestructura propia, evitando exponer datos sensibles de causas, clientes, escritos, transcripciones y memoria de trabajo a servicios externos por defecto.

## Principios

- Todo local por defecto.
- Modelos servidos por Ollama.
- Base vectorial local con ChromaDB.
- Docker Compose como mecanismo principal de despliegue.
- Separación por dominios lógicos.
- Privacidad y trazabilidad como criterios centrales.
- Evolución gradual por fases y ramas.

## Componentes actuales

- `api-multiagente`: orquestador de agentes en producción (asistente personal, perito informático forense, agente de honorarios/contable, etc.) que expone la API principal.
- `openclaw-causas`: servicio especializado en gestión y consulta de causas judiciales, integrado con el resto de los agentes.
- `whisper-worker`: servicio de transcripción de audio y video a texto usando modelos locales, alimentando el RAG.
- `shared-data/`: “hogar” de las causas; carpeta compartida donde se almacenan documentos, escritos, pruebas y transcripciones de videos, que luego se ingestan en los RAG forense y de honorarios.
- `docs/`: documentación detallada de arquitectura y de las distintas fases de evolución del proyecto.

## Puesta en marcha rápida

Requisitos mínimos:

- Docker y Docker Compose instalados.
- Ollama corriendo en la máquina host con los modelos configurados que usan los servicios.

Pasos básicos:

```bash
git clone <url-del-repo>
cd multiagente
cp env.example .env   # ajustar variables necesarias
docker compose up -d --build
```

Una vez levantado:

- La API principal del multiagente queda expuesta por `api-multiagente`.
- Los servicios `openclaw-causas` y `whisper-worker` se comunican por la red interna de Docker.
- Los datos compartidos (causas, documentos, audios, transcripciones) se gestionan desde `shared-data/` y se usan en los RAG de los agentes.

## Documentación

La documentación más detallada se encuentra en la carpeta `docs/`, incluyendo:

- Arquitectura general del ecosistema.
- Detalle de fases de implementación.
- Notas y decisiones de diseño.

Se recomienda comenzar leyendo:

- `docs/README-arquitectura-fase2.*`
- `docs/README-FASE-3.txt`
- y la documentación de arquitectura general.

Ver flujos detallados en docs/FLUJOS-RAG-*.md
