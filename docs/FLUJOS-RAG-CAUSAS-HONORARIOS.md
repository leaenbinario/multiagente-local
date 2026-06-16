# Flujo de causas y honorarios hacia el RAG

Este documento describe cómo los documentos de causas judiciales y honorarios se convierten en conocimiento consultable por los agentes (forense, honorarios/contador, asistente) dentro del ecosistema multiagente local.[file:572]

## 1. Origen de la información

- Escritos judiciales (demandas, contestaciones, recursos, oficios, cédulas).
- Pruebas documentales (informes, dictámenes, PDFs periciales, transcripciones).
- Documentos de honorarios (liquidaciones, regulaciones, actualizaciones UMA, modelos de escritos relacionados).

Objetivo: que el contenido relevante de estos documentos pueda ser buscado y utilizado por los agentes especializados sin salir de la infraestructura local.[file:572]

## 2. Organización inicial en shared-data

Los documentos se copian a la carpeta compartida del sistema:

- Carpeta base: `shared-data/`
- Subcarpetas recomendadas:
  - `shared-data/causas/<identificador-causa>/documentos/`
  - `shared-data/causas/<identificador-causa>/pruebas/`
  - `shared-data/honorarios/documentos/`

Esta organización convierte `shared-data` en el “hogar” de las causas y centraliza todo lo que luego se ingestará en los RAG forense y de honorarios.[file:572]

## 3. Ingesta para el RAG forense

1. Un proceso de ingesta (por ejemplo `ingesta_forense.py`) recorre las carpetas destinadas a documentación técnica y pericial, típicamente:

   - `shared-data/documentos_forenses/`
   - y/o subcarpetas específicas dentro de cada causa.

2. El script:
   - lee PDFs, textos y otros formatos soportados,
   - limpia el contenido,
   - lo fragmenta en chunks de tamaño adecuado.

3. Esos chunks se insertan en la colección `documentos_forense` de ChromaDB, usando embeddings generados por Ollama (`nomic-embed-text:latest`) y almacenando metadatos como:

   - ruta del archivo origen,
   - identificador de causa,
   - tipo de documento (pericial, técnico, jurisprudencia, etc.).[file:572]

4. El agente forense consulta esta colección cuando recibe una pregunta del dominio pericial/forense.

## 4. Ingesta para el RAG de honorarios/contador

1. Un proceso de ingesta específico (por ejemplo `ingesta_contador.py`) recorre documentos vinculados a honorarios:

   - `shared-data/honorarios/documentos/`
   - modelos de escritos, regulaciones, actualizaciones, cálculos de intereses, etc.

2. El flujo es análogo al del agente forense:

   - lectura y normalización del texto,
   - partición en chunks,
   - inserción en la colección `documentos_contable` de ChromaDB con metadatos (tipo de escrito, fuero, etapa procesal, etc.).[file:572]

3. El agente de honorarios/contador usa esta colección como base de su RAG cuando se le consulta sobre liquidaciones, regulaciones, actualizaciones y estrategias procesales relacionadas.

## 5. Consulta desde los agentes

1. El usuario realiza una consulta a través de `api-multiagente` (directa o vía Open WebUI).  
2. El orquestador analiza el mensaje y lo enruta al agente correspondiente:

   - Agente forense → colección `documentos_forense`.
   - Agente honorarios/contador → colección `documentos_contable`.
   - Asistente general → colección `documentos_asistente`.[file:572]

3. El agente:

   - consulta ChromaDB con la pregunta,
   - obtiene los chunks más relevantes,
   - arma un CONTEXTO con texto y fuentes,
   - llama a Ollama (por ejemplo `llama3.2:3b`) con un prompt adecuado al rol.[file:572]

4. La respuesta que vuelve al usuario combina:
   - el razonamiento del modelo,
   - las citas de los documentos originales de `shared-data`,
   todo dentro del entorno local.[file:572]

## 6. Buenas prácticas de archivo

- Usar un identificador consistente de causa en las carpetas (`causa-2026-XXXX`, por ejemplo).
- Mantener separados:
  - documentos de fondo de la causa,
  - documentos de honorarios,
  aunque ambos pueden alimentar distintos RAG.
- Registrar qué documentos ya se ingestaron para evitar duplicados (por ejemplo, con un índice simple o un log de ingesta).
- Cuando se cambie un documento relevante, volver a lanzar la ingesta correspondiente para mantener actualizado el RAG.
