from pathlib import Path
import os
import shutil
import subprocess

import torch
import whisper

IN_DIR = Path(os.getenv("INPUT_DIR", "/entradas"))
OUT_DIR = Path(os.getenv("OUT_DIR", "/transcripciones"))
TMP_DIR = Path(os.getenv("TMP_DIR", "/tmp/whisper"))
MODEL_NAME = os.getenv("WHISPER_MODEL", "medium")
LANGUAGE = os.getenv("WHISPER_LANGUAGE", "es")
DELETE_SOURCE = os.getenv("DELETE_SOURCE_AFTER_SUCCESS", "false").lower() == "true"

MEDIA_EXTS = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v",
    ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma", ".amr", ".3gp"
}


def listar_medios() -> list[Path]:
    if not IN_DIR.exists():
        return []
    archivos = [
        p for p in IN_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in MEDIA_EXTS
    ]
    return sorted(archivos, key=lambda p: p.name.lower())


def convertir_a_wav_16k_mono(origen: Path, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(origen),
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        str(destino),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def main():
    medios = listar_medios()

    if not medios:
        print("No hay archivos para transcribir. Saliendo.")
        return

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Cargando modelo '{MODEL_NAME}' de Whisper en {device}...")

    model = whisper.load_model(MODEL_NAME, device=device)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    for media in medios:
        out_file = OUT_DIR / f"{media.stem}.txt"
        tmp_audio = TMP_DIR / f"{media.stem}.wav"

        if out_file.exists() and out_file.stat().st_size > 0:
            print(f"Ya existe transcripción, salteando: {media}")
            continue

        print(f"Preparando {media} -> {tmp_audio}")

        try:
            convertir_a_wav_16k_mono(media, tmp_audio)
        except Exception as e:
            print(f"Error convirtiendo {media}: {e}")
            continue

        print(f"Transcribiendo {media} -> {out_file}")

        try:
            result = model.transcribe(
                str(tmp_audio),
                language=LANGUAGE,
                fp16=(device == "cuda"),
            )
            text = result.get("text", "").strip()

            if not text:
                print(f"Advertencia: transcripción vacía para {media}.")
                continue

            with out_file.open("w", encoding="utf-8") as f:
                f.write(text + "\n")

            print(f"Listo: {out_file}")

            if DELETE_SOURCE:
                try:
                    media.unlink()
                    print(f"Eliminado original: {media}")
                except Exception as e:
                    print(f"Error al eliminar {media}: {e}")

        except Exception as e:
            print(f"Error transcribiendo {media}: {e}")

        finally:
            try:
                if tmp_audio.exists():
                    tmp_audio.unlink()
            except Exception as e:
                print(f"No se pudo borrar temporal {tmp_audio}: {e}")

    try:
        if TMP_DIR.exists() and not any(TMP_DIR.iterdir()):
            shutil.rmtree(TMP_DIR, ignore_errors=True)
    except Exception:
        pass

    print("Proceso finalizado.")


if __name__ == "__main__":
    main()