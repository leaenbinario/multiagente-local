def enrutar_consulta(pregunta: str) -> str:
    texto = (pregunta or "").lower()

    claves_forense = [
        "forense", "evidencia", "cadena de custodia", "hash", "hashes",
        "imagen forense", "metadato", "metadatos", "pericia", "informe pericial"
    ]

    claves_contador = [
        "contador", "honorario", "honorarios", "tributario", "impuesto",
        "iva", "factura", "liquidación", "liquidacion", "anticipo"
    ]

    claves_memoria = [
        "memoria", "recordá", "recorda", "recordás", "recordas",
        "recordatorio", "guardar preferencia", "guardá", "guarda"
    ]

    if any(k in texto for k in claves_forense):
        return "forense"

    if any(k in texto for k in claves_contador):
        return "contador"

    if any(k in texto for k in claves_memoria):
        return "memoria"

    return "asistente"
