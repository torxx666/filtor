import sqlite3
import json
import os

DB_PATH = "c:/Users/torxx/DCO/Filtor/backend/leak.db"

# Mapping French -> English
TRANSLATIONS = {
    "🚨 Fichier polyglot détecté (multiples signatures)": "🚨 Polyglot file detected (multiple signatures)",
    "⚠️ Extension dangereuse:": "⚠️ Dangerous extension:",
    "⚠️ Signature (": "⚠️ Signature (", # Context dependent, handle carefully
    "ne correspond pas à l'extension": "does not match extension",
    "⚠️ Document contient des macros VBA": "⚠️ Document contains VBA macros",
    "⚠️ PDF contient du JavaScript": "⚠️ PDF contains JavaScript",
    "⚠️ Archive protégée par mot de passe": "⚠️ Archive protected by password",
    "⚠️ PDF chiffré": "⚠️ Encrypted PDF",
    "⚠️ Données après marqueur de fin de fichier": "⚠️ Data found after trailing EOCD/EOF marker",
    "fichier(s) potentiellement embarqué(s)": "potentially embedded file(s)",
    "⚠️ Script potentiellement obfusqué": "⚠️ Potentially obfuscated script",
    "🚨": "🚨", # Keep
    "secret(s) ou credential(s) détecté(s)": "secret(s) or credential(s) detected",
    "indicateur(s) suspect(s) dans l'exécutable": "suspicious indicator(s) in executable",
    "⚠️ Coordonnées GPS présentes dans l'image": "⚠️ GPS coordinates found in image",
    "Nom de fichier suspect:": "Suspicious filename:",
    "Fichier vide": "Empty file",
    "Fichier très volumineux:": "Very large file:",
    "Modifié très récemment": "Modified very recently",
    "Archive avec": "Archive with",
    "fichiers (potentiel zip bomb)": "files (potential zip bomb)",
    "Ratio de compression très élevé:": "Very high compression ratio:",
    "zip bomb possible": "possible zip bomb",
    "Base de données avec": "Database with",
    "table(s) sensible(s)": "sensitive table(s)"
}

def migrate_db():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    try:
        # Fetch all files with potential French text in info or details
        # Optimziation: Just fetch all and process in python for 100% safety on JSON
        rows = c.execute("SELECT id, info, details FROM files").fetchall()
        
        updated_count = 0
        
        for row in rows:
            file_id = row['id']
            info = row['info']
            details_str = row['details']
            
            new_info = info
            new_details_str = details_str
            changed = False

            # Translate INFO column
            if info:
                for fr, en in TRANSLATIONS.items():
                    if fr in new_info:
                        new_info = new_info.replace(fr, en)
                        changed = True
            
            # Translate DETAILS column (JSON)
            if details_str:
                try:
                    # Naive string replacement on the JSON string is risky but likely okay for these specific phrases
                    # Better: Load JSON, walk it? 
                    # Given the structure, simple string replace is safer than missing deep nested keys, 
                    # provided the French strings are unique enough.
                    for fr, en in TRANSLATIONS.items():
                        if fr in new_details_str:
                            new_details_str = new_details_str.replace(fr, en)
                            changed = True
                except:
                    pass

            if changed:
                c.execute("UPDATE files SET info = ?, details = ? WHERE id = ?", (new_info, new_details_str, file_id))
                updated_count += 1
                if updated_count % 100 == 0:
                    print(f"Migrated {updated_count} records...")

        conn.commit()
        print(f"Migration complete. Updated {updated_count} files.")

    except Exception as e:
        print(f"Error migrating DB: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()
