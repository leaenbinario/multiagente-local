# Flujo de clases (videos y audios) hacia el RAG

Este documento describe el flujo completo por el cual un video o audio de clase se convierte en conocimiento consultable por los agentes (por ejemplo, agente forense u honorarios).

## 1. Origen del material

- Fuente típica: grabaciones de clases, conferencias o charlas en video o audio.
- Formatos habituales: `.mp4`, `.mkv`, `.mp3`, `.wav`, `.opus`, etc.
- Objetivo: convertir el contenido hablado en texto y ponerlo a disposición del RAG temático correspondiente.

## 2. Ingesta del archivo en shared-data

1. El archivo de audio/video se copia a la carpeta compartida del sistema:

   - Carpeta base: `shared-data/`
   - Subcarpetas recomendadas (ejemplos):
     - `shared-data/clases/forense/`
     - `shared-data/clases/honorarios/`
     - `shared-data/clases/otros/`

2. La ubicación en `shared-data` permite que tanto `whisper-worker` como los procesos de ingesta del RAG accedan al mismo archivo.

## 3. Transcripción con whisper-worker

1. Un proceso (manual o automatizado) envía el audio/video a `whisper-worker` para su transcripción.
2. `whisper-worker` procesa el archivo usando modelos locales de reconocimiento de voz.
3. La salida es un archivo de texto (por ejemplo `.txt` o `.json`) con la transcripción completa.
4. La transcripción se guarda también dentro de `shared-data`, idealmente en una estructura paralela:

   - Ejemplo:
     - Audio original: `shared-data/clases/forense/2026-05-curso-forense-clase1.opus`
     - Transcripción: `shared-data/clases/forense/transcripciones/2026-05-curso-forense-clase1.txt`

## 4. Ingesta de la transcripción al RAG

1. Un proceso de ingesta (script o servicio) recorre las transcripciones nuevas en `shared-data`.
2. Cada transcripción se limpia y fragmenta en trozos (chunks) adecuados para el RAG.
3. El contenido se indexa en la base vectorial local (ChromaDB), asociándolo al dominio correspondiente:

   - Dominio forense: transcripciones relacionadas con informática forense.
   - Dominio honorarios: transcripciones relacionadas con práctica procesal, honorarios y gestión judicial.

4. Se almacenan metadatos importantes, por ejemplo:
   - nombre del archivo original,
   - fecha de la clase,
   - módulo/curso,
   - tipo de agente que debe usar esa información (forense, honorarios, etc.).

## 5. Consulta desde los agentes

1. Cuando el usuario realiza una consulta a través de `api-multiagente`, el agente correspondiente (por ejemplo, forense) identifica el dominio de conocimiento adecuado.
2. El agente lanza una búsqueda semántica en la base vectorial:
   - recupera los fragmentos más relevantes de las transcripciones,
   - combina ese contexto con el modelo local servido por Ollama.
3. La respuesta que devuelve al usuario está fundamentada en el contenido de las clases previamente transcritas e ingestadas, manteniendo toda la información dentro de la infraestructura local.

## 6. Buenas prácticas

- Mantener una convención clara de nombres para los archivos de clase (fecha, curso, módulo).
- Separar por dominio (`forense`, `honorarios`, `otros`) desde el nivel de carpetas.
- Registrar en algún lugar (por ejemplo, en un CSV o en una pequeña base local) qué archivos ya fueron ingestados al RAG para evitar duplicados.
- Conservar siempre el vínculo entre:
  - audio/video original,
  - transcripción,
  - documentos auxiliares (diapositivas, PDFs de la clase) si se ingestan por separado.