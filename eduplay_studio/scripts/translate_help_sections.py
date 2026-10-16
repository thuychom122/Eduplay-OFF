"""Sua nhan nut sai trong tieng Viet + dich 2 muc sang fr/es/de.

1) VI: hoa 4 nhan sai so voi nut that co trong app.
2) FR/ES/DE: thay THEO THU TU cac nut chu trong HTML (giu nguyen 100%
   the/bang/token mau) -> khong the sinh HTML hong.
"""
import json
import pathlib
import re

BASE = pathlib.Path(r"E:\eduplay\v1.0\EDUPLAY-OFFLINE\eduplay_studio\eduplay\resources\i18n")

# --- 1) Sua nhan nut sai trong tieng Viet ----------------------------------
VI_FIX = {
    "help.sections.quickstart.content": [
        ("chọn kiểu <b>Trắc nghiệm</b>", "chọn kiểu <b>Trắc nghiệm cổ điển - Trắc nghiệm</b>"),
        ("chọn <b>Trắc nghiệm 4 đáp án</b>", "chọn <b>Trắc nghiệm</b>"),
    ],
    "help.sections.editor.content": [
        ("bấm nút <b>Ảnh</b>", "bấm nút <b>Chọn hình ảnh</b>"),
        ("<i>Hiện giải thích</i>", "<i>Hiện giải thích đáp án</i>"),
        ("bấm <b>Xóa</b> (sẽ hỏi lại)", "bấm <b>Xóa câu chọn</b> (sẽ hỏi lại)"),
        ("con mắt <b>Xem nhanh</b>", "con mắt <b>Xem câu chọn</b>"),
    ],
}

# --- 2) Dich FR / ES / DE --------------------------------------------------
QUICKSTART = {
    "fr": [
        "⚡ Démarrage rapide — prêt en 30 secondes",
        "Envie d’essayer tout de suite sans tout lire ? Trois étapes suffisent pour obtenir un jeu de 5 questions à envoyer aux élèves. Idéal pour une première utilisation.",
        "1",
        "Créer le projet",
        "Sur l’accueil → cliquez sur ",
        "CRÉER",
        " → saisissez un nom (ex. : ",
        "Maths 5 - Fractions",
        ") → choisissez le type ",
        "Quiz classique - Choix multiple",
        " → cliquez sur ",
        "Créer et éditer",
        ".",
        "2",
        "Rédiger 5 questions",
        "Dans la colonne de gauche, cliquez sur ",
        "Ajouter",
        " → au centre, choisissez ",
        "Choix multiple",
        " → saisissez la question et les 4 propositions → cochez la bonne réponse → cliquez sur ",
        "Enregistrer la question",
        ". Répétez 5 fois.",
        "3",
        "Tester et envoyer",
        "En haut, cliquez sur ",
        "Aperçu",
        " pour tester → si tout convient, cliquez sur ",
        "Export interne (HTML)",
        " → choisissez un dossier → vous obtenez un fichier ",
        ".html",
        " → envoyez-le aux élèves (Zalo, e-mail…) ; il se joue dans le navigateur.",
        "🎬 ",
        "Exemple complet :",
        " Créer « Maths 5 - Fractions » → 5 questions à choix multiple → ",
        "Aperçu",
        " → ",
        "Export interne (HTML)",
        " → envoyer à la classe. Terminé en 1 minute !",
    ],
    "es": [
        "⚡ Inicio rápido — listo en 30 segundos",
        "¿Quieres probar sin leer todo? Con 3 pasos tendrás un juego de 5 preguntas para enviar a los alumnos. Ideal para empezar.",
        "1",
        "Crear el proyecto",
        "En el inicio → pulsa ",
        "CREAR",
        " → escribe un nombre (p. ej.: ",
        "Matemáticas 5 - Fracciones",
        ") → elige el tipo ",
        "Quiz clásico - Opción múltiple",
        " → pulsa ",
        "Crear y editar",
        ".",
        "2",
        "Redactar 5 preguntas",
        "En la columna izquierda pulsa ",
        "Añadir",
        " → en el centro elige ",
        "Opción múltiple",
        " → escribe la pregunta y las 4 opciones → marca la correcta → pulsa ",
        "Guardar pregunta",
        ". Repite 5 veces.",
        "3",
        "Probar y enviar",
        "Arriba pulsa ",
        "Vista previa",
        " para probar → si está bien, pulsa ",
        "Exportación interna (HTML)",
        " → elige dónde guardar → tendrás un archivo ",
        ".html",
        " → envíalo a los alumnos (Zalo, correo…); se juega en el navegador.",
        "🎬 ",
        "Ejemplo completo:",
        " Crear «Matemáticas 5 - Fracciones» → 5 preguntas de opción múltiple → ",
        "Vista previa",
        " → ",
        "Exportación interna (HTML)",
        " → enviar a la clase. ¡Listo en 1 minuto!",
    ],
    "de": [
        "⚡ Schnellstart — in 30 Sekunden fertig",
        "Du möchtest sofort loslegen, ohne alles zu lesen? In 3 Schritten hast du ein Spiel mit 5 Fragen für die Schüler. Ideal für den ersten Start.",
        "1",
        "Projekt anlegen",
        "Auf der Startseite → klicke auf ",
        "ERSTELLEN",
        " → gib einen Namen ein (z. B. ",
        "Mathe 5 - Brüche",
        ") → wähle den Typ ",
        "Quiz Classic - Multiple Choice",
        " → klicke auf ",
        "Erstellen & Bearbeiten",
        ".",
        "2",
        "5 Fragen schreiben",
        "In der linken Spalte ",
        "Hinzufügen",
        " → in der Mitte ",
        "Multiple-Choice",
        " → gib Frage und 4 Antworten ein → hake die richtige an → klicke auf ",
        "Frage speichern",
        ". 5-mal wiederholen.",
        "3",
        "Testen und senden",
        "Oben ",
        "Vorschau",
        " zum Testen → passt, dann ",
        "Interner Export (HTML)",
        " → Speicherort wählen → du erhältst eine ",
        ".html",
        "-Datei → sende sie an die Schüler (Zalo, E-Mail…); sie spielt sich im Browser.",
        "🎬 ",
        "Vollständiges Beispiel:",
        " „Mathe 5 - Brüche“ anlegen → 5 Multiple-Choice-Fragen → ",
        "Vorschau",
        " → ",
        "Interner Export (HTML)",
        " → an die Klasse senden. Fertig in 1 Minute!",
    ],
}

EDITOR = {
    "fr": [
        "✏️ Rédiger les questions",
        "L’éditeur est l’endroit où vous saisissez vos questions. L’écran est divisé en 3 colonnes : ",
        "Gauche",
        " la liste des questions, ",
        "Centre",
        " la saisie, ",
        "Droite",
        " l’aperçu. 5 types de questions sont disponibles, chacun avec sa propre saisie. Vous pouvez aussi joindre une image et une explication à chaque question.",
        "Ajouter une question :",
        " Colonne gauche → cliquez sur ",
        "Ajouter",
        " → au centre, choisissez le ",
        "Type",
        " de question → une fois la saisie terminée, cliquez sur ",
        "Enregistrer la question",
        ".",
        "Type de question",
        "Comment la saisir",
        "Remarque",
        "Choix multiple",
        "Saisissez 4 propositions, cochez la bonne",
        "Convient à tous les niveaux",
        "Vrai / Faux",
        "Choisissez ",
        "Vrai",
        " ou ",
        "Faux",
        "2 réponses seulement",
        "Texte à trous",
        "Dans la question, tapez ",
        "___",
        " (3 tirets bas). Dans la réponse, une bonne réponse par ligne.",
        "Insensible à la casse",
        "Association",
        "Saisissez au format ",
        "Gauche = Droite",
        ", une paire par ligne",
        "Glisser-déposer pendant le jeu",
        "Réponse courte",
        "Réponse courte, plusieurs réponses possibles",
        "Tolère les approximations",
        "🖼️ Ajouter une image :",
        " Dans la zone question, cliquez sur ",
        "Sélectionner une image",
        " → choisissez un fichier PNG/JPG → l’image est enregistrée dans le dossier ",
        "media",
        " du projet et s’affiche en jeu.",
        "💬 Explication :",
        " Saisissez-la dans le champ ",
        "Explication",
        " → elle s’affiche après la réponse de l’élève (si ",
        "Afficher les explications des réponses",
        " est activé).",
        "🔧 Modifier / Supprimer :",
        " Cliquez sur une question dans la colonne gauche pour la modifier → ",
        "Enregistrer la question",
        ". Pour supprimer, cliquez sur ",
        "Supprimer",
        " (une confirmation s’affiche). Bouton œil ",
        "Aperçu ciblé",
        " pour tester une seule question.",
    ],
    "es": [
        "✏️ Redactar preguntas",
        "El editor es donde escribes las preguntas. La pantalla tiene 3 columnas: ",
        "Izquierda",
        " la lista de preguntas, ",
        "Centro",
        " la escritura, ",
        "Derecha",
        " la vista previa. Hay 5 tipos de pregunta disponibles, cada uno con su forma de escribir. También puedes adjuntar una imagen y una explicación a cada pregunta.",
        "Añadir una pregunta:",
        " Columna izquierda → pulsa ",
        "Añadir",
        " → en el centro elige el ",
        "Tipo",
        " de pregunta → cuando termines, pulsa ",
        "Guardar pregunta",
        ".",
        "Tipo de pregunta",
        "Cómo escribirla",
        "Nota",
        "Opción múltiple",
        "Escribe 4 opciones y marca la correcta",
        "Sirve para cualquier nivel",
        "Verdadero / Falso",
        "Elige ",
        "Verdadero",
        " o ",
        "Falso",
        "Solo 2 opciones",
        "Rellenar espacios",
        "En la pregunta escribe ",
        "___",
        " (3 guiones bajos). En la respuesta, una correcta por línea.",
        "No distingue mayúsculas",
        "Emparejar",
        "Escribe en formato ",
        "Izquierda = Derecha",
        ", un par por línea",
        "Se arrastra durante el juego",
        "Respuesta corta",
        "Respuesta corta, admite varias respuestas",
        "Acepta respuestas parecidas",
        "🖼️ Adjuntar imagen:",
        " En la casilla de la pregunta, pulsa ",
        "Seleccionar imagen",
        " → elige un archivo PNG/JPG → la imagen se guarda en la carpeta ",
        "media",
        " del proyecto y se ve al jugar.",
        "💬 Explicación:",
        " Escríbela en el campo ",
        "Explicación",
        " → se muestra después de que el alumno responda (si ",
        "Mostrar explicaciones de respuestas",
        " está activada).",
        "🔧 Editar / Eliminar:",
        " Pulsa una pregunta de la columna izquierda para editarla → ",
        "Guardar pregunta",
        ". Para eliminarla, pulsa ",
        "Eliminar selección",
        " (pedirá confirmación). El botón de ojo ",
        "Vista previa",
        " prueba una sola pregunta.",
    ],
    "de": [
        "✏️ Fragen schreiben",
        "Im Editor schreibst du die Fragen. Der Bildschirm ist in 3 Spalten geteilt: ",
        "Links",
        " die Frageliste, ",
        "Mitte",
        " die Eingabe, ",
        "Rechts",
        " die Vorschau. Es stehen 5 Fragetypen zur Verfügung, jeder mit eigener Eingabe. Du kannst jeder Frage auch ein Bild und eine Erklärung hinzufügen.",
        "Neue Frage anlegen:",
        " Linke Spalte → klicke auf ",
        "Hinzufügen",
        " → in der Mitte den ",
        "Typ",
        " der Frage wählen → nach der Eingabe auf ",
        "Frage speichern",
        " klicken.",
        "Fragetyp",
        "Wie man sie eingibt",
        "Hinweis",
        "Multiple-Choice",
        "4 Antworten eingeben, die richtige anhaken",
        "Für alle Stufen geeignet",
        "Richtig / Falsch",
        "Wähle ",
        "Richtig",
        " oder ",
        "Falsch",
        "Nur 2 Antworten",
        "Lückentext",
        "In der Frage ",
        "___",
        " eingeben (3 Unterstriche). Bei der Antwort eine richtige Lösung pro Zeile.",
        "Groß-/Kleinschreibung egal",
        "Zuordnung",
        "Als ",
        "Links = Rechts",
        " eingeben, ein Paar pro Zeile",
        "Wird im Spiel per Ziehen zugeteilt",
        "Kurzantwort",
        "Kurze Antwort, mehrere Lösungen möglich",
        "Näherungen werden akzeptiert",
        "🖼️ Bild anhängen:",
        " Im Fragefeld auf ",
        "Bild auswählen",
        " klicken → PNG/JPG-Datei wählen → das Bild wird im Ordner ",
        "media",
        " des Projekts gespeichert und im Spiel angezeigt.",
        "💬 Erklärung:",
        " Im Feld ",
        "Erklärung",
        " eintragen → sie erscheint, nachdem die Schüler antworten (wenn ",
        "Antworterklärungen anzeigen",
        " aktiv ist).",
        "🔧 Bearbeiten / Löschen:",
        " Auf eine Frage in der linken Spalte klicken → ",
        "Frage speichern",
        ". Zum Löschen ",
        "Auswahl löschen",
        " anklicken (mit Rückfrage). Mit dem Auge ",
        "Auswahl ansehen",
        " eine einzelne Frage testen.",
    ],
}

EXTRA = {
    "fr": {
        "help.sections.browse.title": "Parcourir les projets",
        "help.sections.browse.subtitle": "Rechercher, filtrer et gérer les projets",
        "editor.center.save_question": "Enregistrer la question",
    },
    "es": {
        "help.sections.browse.title": "Explorar proyectos",
        "help.sections.browse.subtitle": "Buscar, filtrar y gestionar proyectos",
        "editor.center.save_question": "Guardar pregunta",
    },
    "de": {
        "help.sections.browse.title": "Projekte durchsuchen",
        "help.sections.browse.subtitle": "Projekte suchen, filtern und verwalten",
        "editor.center.save_question": "Frage speichern",
    },
}


def text_nodes(html: str):
    return [n for n in re.split(r"(<[^>]+>)", html) if n and not n.startswith("<")]


def apply_translation(html: str, parts) -> str:
    out_parts = re.split(r"(<[^>]+>)", html)
    idx = 0
    for i, chunk in enumerate(out_parts):
        if chunk.startswith("<"):
            continue
        if idx < len(parts):
            out_parts[i] = parts[idx]
            idx += 1
    if idx != len(parts):
        raise ValueError(
            f"so nut chu khong khop: html co {idx}, ban dich co {len(parts)}"
        )
    return "".join(out_parts)


def main() -> int:
    vi_path = BASE / "vi.json"
    vi = json.loads(vi_path.read_text(encoding="utf-8"))
    vi_changed = []
    for key, pairs in VI_FIX.items():
        text = vi[key]
        new = text
        for old, rep in pairs:
            if old not in new:
                print(f"  [!] VI khong tim thay: {old[:50]}")
                continue
            new = new.replace(old, rep)
        if new != text:
            vi[key] = new
            vi_changed.append(key.split(".")[2])
    if vi_changed:
        vi_path.write_text(
            json.dumps(vi, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(f"vi: sua nhan nut -> {vi_changed}")

    for lang in ("fr", "es", "de"):
        path = BASE / f"{lang}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        changed = []
        for section, table in (("quickstart", QUICKSTART), ("editor", EDITOR)):
            key = f"help.sections.{section}.content"
            src = vi[key]  # luon lay HTML goc da sua nhan nut
            out = apply_translation(src, table[lang])
            if out != data.get(key):
                data[key] = out
                changed.append(section)
        for key, value in EXTRA[lang].items():
            if data.get(key) != value:
                data[key] = value
                changed.append(key.split(".")[-1])
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"{lang}: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())