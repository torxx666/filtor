import json
import os
import cv2
import sys
import subprocess
import re
from datetime import datetime
from loguru import logger

# Optionnel : pour ExifTool
try:
    import exiftool
except ImportError:
    exiftool = None

def extract_binary_strings(filepath, min_len=10, limit=1000, depth="DEEP"):
    """
    General strings extraction with strict noise filtering for video files.
    """
    results = []
    filename = os.path.basename(filepath)
    
    # Stricter Regex for Windows-style paths
    # Must have at least one backslash-separator to be considered a path context in binary blobs
    # e.g., "C:\Windows\System32" or "D:\Files\Video.mp4"
    path_regex = re.compile(rb'[a-zA-Z]:\\[^<>:"|?*]+(?:\\[^<>:"|?*]+)+')
    
    # General ASCII strings (Length increased to reduce small random noise)
    general_regex = re.compile(rb'[ -~]{' + str(min_len).encode() + rb',}')

    # Blocklist of common video atoms and technical signatures to ignore
    IGNORED_STRINGS = {
        'ftyp', 'moov', 'mdat', 'free', 'wide', 'skip', 'pnot', 'prfl', 
        'mvhd', 'trak', 'tkhd', 'mdia', 'mdhd', 'hdlr', 'minf', 'vmhd', 
        'dinf', 'dref', 'stbl', 'stsd', 'stts', 'stss', 'ctts', 'stsc', 
        'stsz', 'stco', 'co64', 'udta', 'meta', 'ilst', 'mean', 'name', 
        'data', 'ftypmp42', 'ftypisom', 'ftypavc1', 'vide'
    }

    def is_readable(s):
        # Heuristic to filter out binary noise
        if not s: return False
        s = s.strip()
        if len(s) < min_len: return False
        
        # 0. Filter partial atoms/signatures
        if any(ign in s.lower() for ign in IGNORED_STRINGS):
            return False
            
        # 0.5 Filter generic noise patterns
        # e.g. "s:\\${_ymA/" -> contains weird symbolic sequences
        if re.search(r'[\$\{\}\[\]\(\)\<\>]', s):
             # strict: reject strings with code-like symbols unless clearly a path
             if not (':\\' in s or ':/' in s):
                 return False
        
        # 1. Ratio of alpha/numeric vs symbols
        alnum_count = sum(1 for c in s if c.isalnum() or c.isspace())
        ratio = alnum_count / len(s)
        
        # Stricter for short strings
        if len(s) < 15:
            if ratio < 0.95: return False # Must be almost pure alnum
            if not any(c.isalpha() for c in s): return False # Must have letters
        else:
            if ratio < 0.8: return False
        
        # 2. Consecutive "weird" characters
        weird_seq = 0
        for c in s:
            if not (c.isalnum() or c.isspace() or c in '._-:\\/'):
                weird_seq += 1
                if weird_seq > 1: return False # Max 1 weird char in a row
            else:
                weird_seq = 0
        
        # 3. Entropy check (Too many symbols/randomness)
        if len(set(s)) / len(s) > 0.8: # Lowered threshold slightly to catch high-entropy "random" strings
             # Allow if it looks like a path or sentence
             if not (' ' in s or ':\\' in s):
                  return False

        return True

    try:
        if not os.path.exists(filepath):
            return []
            
        file_size = os.path.getsize(filepath)
        
        if depth == "FAST":
            max_chunk_start = 512 * 1024 
            max_chunk_end = 256 * 1024   
        else:
            max_chunk_start = 2 * 1024 * 1024 
            max_chunk_end = 1 * 1024 * 1024   
        
        with open(filepath, 'rb') as f:
            if file_size <= (max_chunk_start + max_chunk_end):
                data = f.read()
            else:
                data = f.read(max_chunk_start)
                f.seek(-max_chunk_end, 2)
                data += f.read(max_chunk_end)
            
            # 1. Hunt for Paths (High Priority) - Keep these always if they look like paths
            path_matches = path_regex.findall(data)
            for m in path_matches:
                try:
                    p = m.decode('utf-8', errors='ignore').strip()
                    if len(p) >= 10: 
                         logger.info(f"trouve \"{p}\" ds {filename}")
                         results.append(p)
                except: continue
                
            # 2. Hunt for General Strings
            string_matches = general_regex.findall(data)
            for m in string_matches:
                try:
                    raw_s = m.decode('utf-8', errors='ignore')
                    # Split by newline to avoid concatenated junk
                    for s in raw_s.split('\n'):
                        s = s.strip()
                        if is_readable(s):
                            logger.info(f"trouve \"{s}\" ds {filename}")
                            results.append(s)
                except: continue
        
        # Deduplicate and sort, keeping shortest/most relevant if too many
        unique_results = sorted(list(set(results)), key=len, reverse=True)
        return unique_results[:limit]
    except Exception as e:
        logger.error(f"Binary scan error: {e}")
        return []

def extract_first_frame(video_path, output_image="/tmp/frame.jpg"):
    """Extrait la première frame de la vidéo et la sauvegarde."""
    try:
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(output_image, frame)
            logger.info(f"Première frame extraite dans {output_image}")
        else:
            logger.error("Erreur : impossible de lire la première frame")
            return None
        cap.release()
        return output_image
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction de la frame : {e}")
        return None

def extract_all_metadata(video_path, depth="DEEP"):
    """Extrait toutes les métadonnées de la vidéo, y compris celles de la première frame."""
    logger.info(f"Début de l'analyse vidéo: {video_path}")
    if not os.path.isfile(video_path):
        logger.error(f"Erreur : le fichier '{video_path}' n'existe pas ou n'est pas un fichier valide.")
        return None

    metadata = {
        'file_path': os.path.abspath(video_path),
        'file_name': os.path.basename(video_path),
        'file_size_bytes': os.path.getsize(video_path),
        'file_creation_time': datetime.fromtimestamp(os.path.getctime(video_path)).isoformat(),
        'file_modification_time': datetime.fromtimestamp(os.path.getmtime(video_path)).isoformat(),
        'format': {},
        'streams': [],
        'chapters': [],
        'exiftool_metadata': {},
        'first_frame_metadata': {},
        'embedded_strings': []
    }

    # Extraction avec ffprobe via subprocess
    # Extraction avec ffprobe via subprocess
    try:
        logger.debug(f"Tentative d'extraction des métadonnées ffprobe pour {video_path}")
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            '-show_chapters',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        probe = json.loads(result.stdout)

        # Informations du conteneur
        format_info = probe.get('format', {})
        metadata['format'] = {
            'filename': format_info.get('filename'),
            'format_name': format_info.get('format_name'),
            'format_long_name': format_info.get('format_long_name'),
            'duration_seconds': float(format_info.get('duration', 0)),
            'size_bytes': int(format_info.get('size', 0)),
            'bit_rate': int(format_info.get('bit_rate', 0)),
            'nb_streams': int(format_info.get('nb_streams', 0)),
            'nb_programs': int(format_info.get('nb_programs', 0)),
            'tags': format_info.get('tags', {})
        }

        # Informations des streams
        for stream in probe.get('streams', []):
            stream_info = {
                'index': stream.get('index'),
                'codec_type': stream.get('codec_type'),
                'codec_name': stream.get('codec_name'),
                'codec_long_name': stream.get('codec_long_name'),
                'profile': stream.get('profile'),
                'duration_seconds': float(stream.get('duration', 0)) or float(format_info.get('duration', 0)),
                'bit_rate': stream.get('bit_rate'),
                'frame_rate': stream.get('r_frame_rate'),
                'width': stream.get('width'),
                'height': stream.get('height'),
                'sample_aspect_ratio': stream.get('sample_aspect_ratio'),
                'display_aspect_ratio': stream.get('display_aspect_ratio'),
                'pix_fmt': stream.get('pix_fmt'),
                'sample_rate': stream.get('sample_rate'),
                'channels': stream.get('channels'),
                'channel_layout': stream.get('channel_layout'),
                'tags': stream.get('tags', {}),
                'disposition': stream.get('disposition', {})
            }
            metadata['streams'].append(stream_info)

        # Informations sur les chapitres
        metadata['chapters'] = probe.get('chapters', [])


    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
        logger.warning(f"ffprobe non disponible ou absent : {e}")
        metadata['format'] = {'error': f"ffprobe a échoué ou absent : {str(e)}"}

    # Extraction avec ExifTool (métadonnées cachées)
    if exiftool:
        try:
            logger.debug("Extraction des métadonnées ExifTool...")
            with exiftool.ExifToolHelper() as et:
                exif_metadata = et.get_metadata(video_path)
                metadata['exiftool_metadata'] = exif_metadata[0] if exif_metadata else {}
        except Exception as e:
            logger.error(f"Erreur ExifTool : {e}")
            metadata['exiftool_metadata'] = {"error": "ExifTool non disponible ou erreur"}

    # Extraction de la première frame et ses métadonnées
    frame_path = extract_first_frame(video_path)
    frame_path = extract_first_frame(video_path)
    if frame_path and exiftool:
        try:
            logger.debug("Extraction des métadonnées de la première frame...")
            with exiftool.ExifToolHelper() as et:
                frame_metadata = et.get_metadata(frame_path)
                metadata['first_frame_metadata'] = frame_metadata[0] if frame_metadata else {}
        except Exception as e:
            logger.error(f"Erreur ExifTool pour la frame : {e}")
            metadata['first_frame_metadata'] = {"error": "ExifTool non disponible ou erreur"}

    # NEW: Deep Binary Scan for buried paths
    if depth == "FAST":
        logger.info(f"FAST MODE: Skipping binary string scan for {video_path}")
        metadata['embedded_strings'] = []
    else:
        logger.debug(f"Running binary scan (depth={depth}) for paths...")
        metadata['embedded_strings'] = extract_binary_strings(video_path, depth=depth)

    return metadata

def save_metadata_to_json(metadata, output_file=None):
    """Sauvegarde les métadonnées dans un fichier JSON, par défaut dans /tmp/<nom_fichier_source>.json."""
    try:
        if output_file is None:
            # Générer le nom du fichier JSON à partir du nom du fichier source
            source_filename = os.path.splitext(metadata['file_name'])[0]
            output_file = f"/tmp/{source_filename}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)
        print(f"Métadonnées sauvegardées dans {output_file}")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du JSON : {e}")

# Gestion des arguments de ligne de commande
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage : python3 extract_video_metadata_subprocess.py <chemin_vers_video>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    print(f"Traitement du fichier : {video_path}")
    metadata = extract_all_metadata(video_path)
    
    if metadata:
        # Afficher les métadonnées dans la console
        print(json.dumps(metadata, indent=4, ensure_ascii=False))
        # Sauvegarder dans /tmp/<nom_fichier>.json
        save_metadata_to_json(metadata)
    else:
        print("Aucune métadonnée extraite, vérifiez le fichier ou les dépendances.")