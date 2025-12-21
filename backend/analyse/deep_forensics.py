#!/usr/bin/env python3
"""
Deep File Analyzer - Analyse approfondie multi-format
Basé sur les meilleures pratiques forensiques et de sécurité
"""

import os
import re
import hashlib
import json
import zipfile
import tarfile
import xml.etree.ElementTree as ET
import struct
import mimetypes
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple, Set
from dataclasses import dataclass, field, asdict
from collections import Counter
import sqlite3

@dataclass
class DeepAnalysisResult:
    """Résultat d'analyse approfondie"""
    filepath: str
    file_type: str
    analysis_depth: str  # SURFACE, STANDARD, DEEP, FORENSIC
    findings: Dict[str, Any] = field(default_factory=dict)
    security_issues: List[str] = field(default_factory=list)
    metadata_extracted: Dict[str, Any] = field(default_factory=dict)
    hidden_content: Dict[str, Any] = field(default_factory=dict)
    risk_indicators: List[str] = field(default_factory=list)
    file_signature: Dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class DeepFileAnalyzer:
    """Analyseur approfondi capable d'inspecter en détail de nombreux formats"""
   
    # Signatures de fichiers (magic bytes)
    FILE_SIGNATURES = {
        'pdf': [b'%PDF'],
        'zip': [b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08'],
        'rar': [b'Rar!\x1a\x07'],
        'gzip': [b'\x1f\x8b'],
        'bzip2': [b'BZh'],
        '7z': [b'7z\xbc\xaf\x27\x1c'],
        'png': [b'\x89PNG\r\n\x1a\n'],
        'jpeg': [b'\xff\xd8\xff'],
        'gif': [b'GIF87a', b'GIF89a'],
        'exe': [b'MZ'],
        'elf': [b'\x7fELF'],
        'sqlite': [b'SQLite format 3\x00'],
        'office_old': [b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'],  # OLE2
        'office_new': [b'PK\x03\x04'],  # OOXML (aussi ZIP)
    }
   
    # Extensions dangereuses/sensibles
    DANGEROUS_EXTENSIONS = {
        '.exe', '.dll', '.so', '.dylib', '.sys', '.bat', '.cmd', '.ps1',
        '.vbs', '.js', '.jar', '.app', '.deb', '.rpm', '.msi', '.scr'
    }
   
    def __init__(self):
        self.analysis_cache = {}
       
    def analyze(self, filepath: str, depth: str = "DEEP") -> DeepAnalysisResult:
        """
        Analyse approfondie d'un fichier
        depth: SURFACE, STANDARD, DEEP, FORENSIC
        """
        result = DeepAnalysisResult(
            filepath=filepath,
            file_type="unknown",
            analysis_depth=depth
        )
       
        if not os.path.exists(filepath):
            result.security_issues.append("Fichier inexistant")
            return result
       
        # 1. Identification du type
        result.file_type = self._identify_file_type(filepath)
        result.file_signature = self._analyze_file_signature(filepath)
       
        # 2. Analyse selon le type
        if 'pdf' in result.file_type.lower():
            result.findings['pdf'] = self._analyze_pdf_deep(filepath)
       
        elif 'office' in result.file_type.lower() or any(ext in filepath.lower() for ext in ['.docx', '.xlsx', '.pptx']):
            result.findings['office'] = self._analyze_office_deep(filepath)
       
        elif 'zip' in result.file_type.lower() or 'archive' in result.file_type.lower():
            result.findings['archive'] = self._analyze_archive_deep(filepath)
       
        elif 'image' in result.file_type.lower():
            result.findings['image'] = self._analyze_image_deep(filepath)
       
        elif 'database' in result.file_type.lower() or filepath.endswith('.db'):
            result.findings['database'] = self._analyze_database_deep(filepath)
       
        elif 'executable' in result.file_type.lower():
            result.findings['executable'] = self._analyze_executable_deep(filepath)
       
        elif 'text' in result.file_type.lower() or 'script' in result.file_type.lower():
            result.findings['text'] = self._analyze_text_deep(filepath)
       
        # 3. Analyses transversales (pour tous les types)
        result.metadata_extracted = self._extract_all_metadata(filepath)
        result.hidden_content = self._detect_hidden_content(filepath)
       
        # 4. Analyses de sécurité
        result.security_issues.extend(self._security_checks(filepath, result))
        result.risk_indicators.extend(self._detect_risk_indicators(filepath, result))
       
        return result
   
    # ========== IDENTIFICATION ==========
   
    def _identify_file_type(self, filepath: str) -> str:
        """Identifie le type de fichier (signature + extension + mime)"""
        try:
            # Par signature
            with open(filepath, 'rb') as f:
                header = f.read(16)
           
            for ftype, signatures in self.FILE_SIGNATURES.items():
                for sig in signatures:
                    if header.startswith(sig):
                        return ftype
           
            # Par extension
            ext = Path(filepath).suffix.lower()
           
            # Par mime type (fallback)
            mime, _ = mimetypes.guess_type(filepath)
            if mime:
                return mime
           
            return f"unknown (ext: {ext})"
        except:
            return "error"
   
    def _analyze_file_signature(self, filepath: str) -> Dict:
        """Analyse la signature du fichier"""
        try:
            with open(filepath, 'rb') as f:
                header = f.read(64)
           
            return {
                'hex': header[:16].hex(),
                'ascii': ''.join(chr(b) if 32 <= b < 127 else '.' for b in header[:16]),
                'matches': self._match_signatures(header),
                'extension': Path(filepath).suffix.lower(),
            }
        except:
            return {}
   
    def _match_signatures(self, header: bytes) -> List[str]:
        """Trouve les signatures correspondantes"""
        matches = []
        for ftype, signatures in self.FILE_SIGNATURES.items():
            for sig in signatures:
                if header.startswith(sig):
                    matches.append(ftype)
        return matches
   
    # ========== ANALYSE PDF ==========
   
    def _analyze_pdf_deep(self, filepath: str) -> Dict:
        """Analyse approfondie de PDF"""
        analysis = {
            'version': None,
            'pages': 0,
            'encrypted': False,
            'has_javascript': False,
            'has_forms': False,
            'has_attachments': False,
            'objects': [],
            'suspicious_elements': [],
            'metadata': {},
            'links': [],
        }
       
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
           
            # Version PDF
            version_match = re.search(b'%PDF-(\d\.\d)', content)
            if version_match:
                analysis['version'] = version_match.group(1).decode()
           
            # Chiffrement
            analysis['encrypted'] = b'/Encrypt' in content
           
            # JavaScript
            js_patterns = [b'/JavaScript', b'/JS', b'/OpenAction', b'/AA']
            for pattern in js_patterns:
                if pattern in content:
                    analysis['has_javascript'] = True
                    analysis['suspicious_elements'].append(f"Contient {pattern.decode()}")
           
            # Formulaires
            if b'/AcroForm' in content:
                analysis['has_forms'] = True
           
            # Pièces jointes
            if b'/EmbeddedFile' in content or b'/Filespec' in content:
                analysis['has_attachments'] = True
                analysis['suspicious_elements'].append("Contient des pièces jointes")
           
            # Actions automatiques
            if b'/OpenAction' in content or b'/AA' in content:
                analysis['suspicious_elements'].append("Actions automatiques détectées")
           
            # Objets
            objects = re.findall(b'(\d+) (\d+) obj', content)
            analysis['objects'] = [f"{obj[0].decode()} {obj[1].decode()}" for obj in objects[:20]]
           
            # URLs/Liens
            urls = re.findall(b'https?://[^\s<>"{}|\\^`\[\]]+', content)
            analysis['links'] = [url.decode(errors='ignore') for url in urls[:20]]
           
            # Compter les pages (approximatif)
            analysis['pages'] = content.count(b'/Type/Page')
           
            # Extraction métadonnées avec pdfinfo si disponible
            try:
                result = subprocess.run(['pdfinfo', filepath], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if ':' in line:
                            key, val = line.split(':', 1)
                            analysis['metadata'][key.strip()] = val.strip()
            except:
                pass
           
        except Exception as e:
            analysis['error'] = str(e)
       
        return analysis
   
    # ========== ANALYSE OFFICE ==========
   
    def _analyze_office_deep(self, filepath: str) -> Dict:
        """Analyse approfondie de documents Office (docx, xlsx, pptx)"""
        analysis = {
            'format': 'unknown',
            'has_macros': False,
            'macro_details': [],
            'embedded_objects': [],
            'external_links': [],
            'metadata': {},
            'content_summary': {},
            'suspicious_elements': [],
        }
       
        try:
            # Vérifier si c'est un OOXML (ZIP)
            if not zipfile.is_zipfile(filepath):
                # Ancien format OLE2
                analysis['format'] = 'OLE2 (ancien format)'
                analysis['suspicious_elements'].append("Ancien format Office (plus risqué)")
                return analysis
           
            analysis['format'] = 'OOXML (moderne)'
           
            with zipfile.ZipFile(filepath, 'r') as zf:
                files = zf.namelist()
               
                # Macros VBA
                vba_files = [f for f in files if 'vbaProject' in f or f.endswith('.bin')]
                if vba_files:
                    analysis['has_macros'] = True
                    analysis['macro_details'] = vba_files
                    analysis['suspicious_elements'].append(f"⚠️ Macros VBA détectées: {len(vba_files)}")
               
                # Objets embarqués
                embedded = [f for f in files if 'embeddings' in f.lower() or 'oleObject' in f]
                if embedded:
                    analysis['embedded_objects'] = embedded
                    analysis['suspicious_elements'].append(f"Objets embarqués: {len(embedded)}")
               
                # Métadonnées
                if 'docProps/core.xml' in files:
                    try:
                        xml_content = zf.read('docProps/core.xml')
                        root = ET.fromstring(xml_content)
                        for elem in root:
                            tag = elem.tag.split('}')[-1]
                            if elem.text:
                                analysis['metadata'][tag] = elem.text
                    except:
                        pass
               
                # Liens externes
                for file in files:
                    if file.endswith('.xml.rels'):
                        try:
                            xml_content = zf.read(file)
                            urls = re.findall(b'Target="(https?://[^"]+)"', xml_content)
                            analysis['external_links'].extend([url.decode() for url in urls])
                        except:
                            pass
               
                # Analyse contenu selon le type
                if 'word/' in str(files):
                    analysis['content_summary'] = self._analyze_word_content(zf)
                elif 'xl/' in str(files):
                    analysis['content_summary'] = self._analyze_excel_content(zf)
                elif 'ppt/' in str(files):
                    analysis['content_summary'] = self._analyze_powerpoint_content(zf)
       
        except Exception as e:
            analysis['error'] = str(e)
       
        return analysis
   
    def _analyze_word_content(self, zf: zipfile.ZipFile) -> Dict:
        """Analyse le contenu d'un document Word"""
        content = {'text_length': 0, 'images': 0, 'tables': 0}
        try:
            if 'word/document.xml' in zf.namelist():
                xml = zf.read('word/document.xml')
                root = ET.fromstring(xml)
               
                # Compter le texte
                text_nodes = root.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
                total_text = ''.join([node.text or '' for node in text_nodes])
                content['text_length'] = len(total_text)
                content['word_count'] = len(total_text.split())
               
                # Images
                images = [f for f in zf.namelist() if f.startswith('word/media/')]
                content['images'] = len(images)
               
                # Tables
                tables = root.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tbl')
                content['tables'] = len(tables)
        except:
            pass
        return content
   
    def _analyze_excel_content(self, zf: zipfile.ZipFile) -> Dict:
        """Analyse le contenu d'un fichier Excel"""
        content = {'sheets': 0, 'formulas': 0, 'external_refs': 0}
        try:
            # Compter les feuilles
            sheets = [f for f in zf.namelist() if f.startswith('xl/worksheets/sheet')]
            content['sheets'] = len(sheets)
           
            # Analyser les formules
            for sheet in sheets[:5]:  # Limiter à 5 feuilles
                try:
                    xml = zf.read(sheet)
                    formulas = re.findall(b'<f[^>]*>([^<]+)</f>', xml)
                    content['formulas'] += len(formulas)
                   
                    # Références externes
                    if b'[' in xml and b']' in xml:
                        content['external_refs'] += 1
                except:
                    pass
        except:
            pass
        return content
   
    def _analyze_powerpoint_content(self, zf: zipfile.ZipFile) -> Dict:
        """Analyse le contenu PowerPoint"""
        content = {'slides': 0, 'notes': 0, 'media': 0}
        try:
            slides = [f for f in zf.namelist() if f.startswith('ppt/slides/slide')]
            content['slides'] = len(slides)
           
            notes = [f for f in zf.namelist() if f.startswith('ppt/notesSlides/')]
            content['notes'] = len(notes)
           
            media = [f for f in zf.namelist() if f.startswith('ppt/media/')]
            content['media'] = len(media)
        except:
            pass
        return content
   
    # ========== ANALYSE ARCHIVES ==========
   
    def _analyze_archive_deep(self, filepath: str) -> Dict:
        """Analyse approfondie d'archives"""
        analysis = {
            'type': None,
            'file_count': 0,
            'total_size': 0,
            'encrypted': False,
            'suspicious_files': [],
            'file_types': {},
            'deep_nesting': False,
            'compression_ratio': 0,
            'file_list': [],
        }
       
        try:
            ext = Path(filepath).suffix.lower()
           
            if ext == '.zip' or zipfile.is_zipfile(filepath):
                analysis['type'] = 'ZIP'
                with zipfile.ZipFile(filepath, 'r') as zf:
                    infos = zf.infolist()
                    analysis['file_count'] = len(infos)
                   
                    for info in infos:
                        analysis['total_size'] += info.file_size
                       
                        # Fichier chiffré
                        if info.flag_bits & 0x1:
                            analysis['encrypted'] = True
                       
                        # Type de fichier
                        file_ext = Path(info.filename).suffix.lower()
                        analysis['file_types'][file_ext] = analysis['file_types'].get(file_ext, 0) + 1
                       
                        # Fichiers suspects
                        if file_ext in self.DANGEROUS_EXTENSIONS:
                            analysis['suspicious_files'].append(info.filename)
                       
                        # Imbrication profonde
                        if info.filename.count('/') > 5:
                            analysis['deep_nesting'] = True
                   
                    analysis['file_list'] = [info.filename for info in infos[:50]]
                   
                    # Ratio de compression
                    compressed_size = sum(info.compress_size for info in infos)
                    if analysis['total_size'] > 0:
                        analysis['compression_ratio'] = round(compressed_size / analysis['total_size'], 3)
           
            elif ext in ['.tar', '.gz', '.bz2', '.xz']:
                analysis['type'] = 'TAR/GZIP'
                with tarfile.open(filepath, 'r:*') as tf:
                    members = tf.getmembers()
                    analysis['file_count'] = len(members)
                   
                    for member in members:
                        analysis['total_size'] += member.size
                       
                        file_ext = Path(member.name).suffix.lower()
                        analysis['file_types'][file_ext] = analysis['file_types'].get(file_ext, 0) + 1
                       
                        if file_ext in self.DANGEROUS_EXTENSIONS:
                            analysis['suspicious_files'].append(member.name)
                   
                    analysis['file_list'] = [m.name for m in members[:50]]
           
        except Exception as e:
            analysis['error'] = str(e)
       
        return analysis
   
    # ========== ANALYSE IMAGES ==========
   
    def _analyze_image_deep(self, filepath: str) -> Dict:
        """Analyse approfondie d'images"""
        analysis = {
            'format': None,
            'dimensions': None,
            'color_mode': None,
            'exif_data': {},
            'gps_location': None,
            'software_used': None,
            'steganography_risk': False,
            'anomalies': [],
        }
       
        try:
            with open(filepath, 'rb') as f:
                header = f.read(12)
           
            # PNG
            if header.startswith(b'\x89PNG'):
                analysis['format'] = 'PNG'
                analysis.update(self._analyze_png(filepath))
           
            # JPEG
            elif header.startswith(b'\xff\xd8'):
                analysis['format'] = 'JPEG'
                analysis.update(self._analyze_jpeg(filepath))
           
            # GIF
            elif header.startswith(b'GIF'):
                analysis['format'] = 'GIF'
           
            # EXIF avec exiftool
            try:
                result = subprocess.run(['exiftool', '-json', filepath],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    exif = json.loads(result.stdout)[0]
                   
                    # GPS
                    if 'GPSLatitude' in exif and 'GPSLongitude' in exif:
                        analysis['gps_location'] = {
                            'lat': exif['GPSLatitude'],
                            'lon': exif['GPSLongitude']
                        }
                        analysis['anomalies'].append("⚠️ Coordonnées GPS présentes")
                   
                    # Logiciel
                    if 'Software' in exif:
                        analysis['software_used'] = exif['Software']
                   
                    analysis['exif_data'] = {k: v for k, v in exif.items() if k in
                        ['Make', 'Model', 'DateTime', 'Software', 'Artist', 'Copyright']}
            except:
                pass
           
            # Détection stéganographie basique
            size = os.path.getsize(filepath)
            if size > 5 * 1024 * 1024:  # > 5MB
                analysis['steganography_risk'] = True
                analysis['anomalies'].append("Taille anormalement grande")
       
        except Exception as e:
            analysis['error'] = str(e)
       
        return analysis
   
    def _analyze_png(self, filepath: str) -> Dict:
        """Analyse spécifique PNG"""
        data = {}
        try:
            with open(filepath, 'rb') as f:
                f.seek(16)  # Skip signature + IHDR chunk start
                width = struct.unpack('>I', f.read(4))[0]
                height = struct.unpack('>I', f.read(4))[0]
                data['dimensions'] = f"{width}x{height}"
               
                bit_depth = struct.unpack('B', f.read(1))[0]
                color_type = struct.unpack('B', f.read(1))[0]
                data['bit_depth'] = bit_depth
                data['color_type'] = ['Grayscale', 'RGB', 'Palette', 'Gray+Alpha', 'RGBA'][color_type] if color_type < 5 else 'Unknown'
        except:
            pass
        return data
   
    def _analyze_jpeg(self, filepath: str) -> Dict:
        """Analyse spécifique JPEG"""
        data = {}
        try:
            with open(filepath, 'rb') as f:
                # Chercher le marqueur SOF (Start of Frame)
                content = f.read(50000)  # Lire les premiers 50KB
               
                # SOF0 marker
                sof = content.find(b'\xff\xc0')
                if sof != -1:
                    f.seek(sof + 5)
                    height = struct.unpack('>H', f.read(2))[0]
                    width = struct.unpack('>H', f.read(2))[0]
                    data['dimensions'] = f"{width}x{height}"
        except:
            pass
        return data
   
    # ========== ANALYSE BASES DE DONNÉES ==========
   
    def _analyze_database_deep(self, filepath: str) -> Dict:
        """Analyse approfondie de bases de données"""
        analysis = {
            'type': None,
            'tables': [],
            'table_count': 0,
            'total_records': 0,
            'schema': {},
            'sensitive_tables': [],
            'indices': [],
        }
       
        try:
            # SQLite
            with open(filepath, 'rb') as f:
                header = f.read(16)
           
            if header.startswith(b'SQLite format 3'):
                analysis['type'] = 'SQLite'
               
                conn = sqlite3.connect(filepath)
                cursor = conn.cursor()
               
                # Lister les tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                analysis['tables'] = tables
                analysis['table_count'] = len(tables)
               
                # Pour chaque table
                for table in tables:
                    try:
                        # Compter les enregistrements
                        cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                        count = cursor.fetchone()[0]
                        analysis['total_records'] += count
                       
                        # Schéma
                        cursor.execute(f"PRAGMA table_info(`{table}`)")
                        columns = cursor.fetchall()
                        analysis['schema'][table] = {
                            'columns': [col[1] for col in columns],
                            'count': count
                        }
                       
                        # Tables sensibles
                        sensitive_keywords = ['user', 'password', 'credential', 'token',
                                             'client', 'customer', 'employee', 'payment', 'card']
                        if any(kw in table.lower() for kw in sensitive_keywords):
                            analysis['sensitive_tables'].append(table)
                    except:
                        pass
               
                # Indices
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
                analysis['indices'] = [row[0] for row in cursor.fetchall()]
               
                conn.close()
       
        except Exception as e:
            analysis['error'] = str(e)
       
        return analysis
   
    # ========== ANALYSE EXÉCUTABLES ==========
   
    def _is_valid_keyword(self, text: str) -> bool:
        """
        Vérifie si un mot-clé/string est valide pour l'indexation Deep.
        Exclut les chaînes contenant #{ }[]' et autres caractères "louches",
        mais autorise les points.
        """
        # Caractères interdits explicitement (et autres bruits courants)
        invalid_chars = set("#{}[]'\"`")
        
        # Vérifier la présence de caractères interdits
        if any(char in invalid_chars for char in text):
            return False
            
        # Doit contenir au moins un caractère alphanumérique
        if not any(c.isalnum() for c in text):
            return False
            
        return True

    def _analyze_executable_deep(self, filepath: str) -> Dict:
        """Analyse approfondie d'exécutables"""
        analysis = {
            'format': None,
            'architecture': None,
            'sections': [],
            'imports': [],
            'exports': [],
            'strings': [],
            'packed': False,
            'suspicious_indicators': [],
        }
       
        try:
            with open(filepath, 'rb') as f:
                header = f.read(4)
           
            # Windows PE
            if header.startswith(b'MZ'):
                analysis['format'] = 'PE (Windows)'
                analysis.update(self._analyze_pe(filepath))
           
            # Linux ELF
            elif header.startswith(b'\x7fELF'):
                analysis['format'] = 'ELF (Linux)'
                analysis.update(self._analyze_elf(filepath))
           
            # Extraire strings
            try:
                result = subprocess.run(['strings', '-n', '8', filepath],
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    raw_strings = result.stdout.split('\n')
                    # FILTRAGE: On ne garde que les strings "propres"
                    valid_strings = [s for s in raw_strings if self._is_valid_keyword(s)]
                    analysis['strings'] = valid_strings[:100]  # Premières 100 valides
                   
                    # Chercher des indicateurs suspects
                    suspicious = ['password', 'credential', 'token', 'api_key',
                                'keylog', 'inject', 'exploit', 'shell', 'reverse']
                    for s in valid_strings[:500]:
                        if any(susp in s.lower() for susp in suspicious):
                            analysis['suspicious_indicators'].append(s[:80])
            except:
                pass
       
        except Exception as e:
            analysis['error'] = str(e)
       
        return analysis
   
    def _analyze_pe(self, filepath: str) -> Dict:
        """Analyse PE (Windows)"""
        data = {}
        try:
            with open(filepath, 'rb') as f:
                f.seek(0x3c)
                pe_offset = struct.unpack('<I', f.read(4))[0]
                f.seek(pe_offset)
               
                pe_sig = f.read(4)
                if pe_sig == b'PE\x00\x00':
                    machine = struct.unpack('<H', f.read(2))[0]
                    architectures = {0x14c: 'x86', 0x8664: 'x64', 0x1c0: 'ARM'}
                    data['architecture'] = architectures.get(machine, f'Unknown ({hex(machine)})')
        except:
            pass
        return data
   
    def _analyze_elf(self, filepath: str) -> Dict:
        """Analyse ELF (Linux)"""
        data = {}
        try:
            with open(filepath, 'rb') as f:
                f.seek(4)
                ei_class = struct.unpack('B', f.read(1))[0]
                data['architecture'] = '64-bit' if ei_class == 2 else '32-bit'
        except:
            pass
        return data
   
    # ========== ANALYSE TEXTE/SCRIPTS ==========
   
    def _analyze_text_deep(self, filepath: str) -> Dict:
        """Analyse approfondie de fichiers texte/scripts"""
        analysis = {
            'encoding': None,
            'line_count': 0,
            'char_count': 0,
            'language': None,
            'obfuscation_score': 0,
            'suspicious_patterns': [],
            'urls': [],
            'ips': [],
            'secrets_found': [],
        }
       
        try:
            # Détecter l'encodage
            with open(filepath, 'rb') as f:
                raw = f.read()
           
            for encoding in ['utf-8', 'latin-1', 'cp1252', 'utf-16']:
                try:
                    content = raw.decode(encoding)
                    analysis['encoding'] = encoding
                    break
                except:
                    continue
           
            if not content:
                return analysis
           
            lines = content.split('\n')
            analysis['line_count'] = len(lines)
            analysis['char_count'] = len(content)
           
            # Détecter le langage
            if filepath.endswith('.py'):
                analysis['language'] = 'Python'
            elif filepath.endswith(('.sh', '.bash')):
                analysis['language'] = 'Shell'
            elif filepath.endswith('.js'):
                analysis['language'] = 'JavaScript'
            elif filepath.endswith(('.php', '.php3')):
                analysis['language'] = 'PHP'
           
            # Obfuscation
            obfusc_indicators = {
                'eval': content.count('eval('),
                'exec': content.count('exec('),
                'base64': content.count('base64'),
                'hex_strings': len(re.findall(r'\\x[0-9a-fA-F]{2}', content)),
                'long_lines': sum(1 for line in lines if len(line) > 500),
            }
            analysis['obfuscation_score'] = sum(obfusc_indicators.values())
           
            # URLs
            urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', content)
            analysis['urls'] = list(set(urls))[:20]
           
            # Adresses IP
            ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', content)
            analysis['ips'] = list(set(ips))[:20]
           
            # Secrets (patterns sensibles)
            secret_patterns = {
                'api_key': r'(?i)(api[_-]?key|apikey)["\s:=]+([a-zA-Z0-9\-_]{20,})',
                'password': r'(?i)(password|passwd)["\s:=]+(\S+)',
                'aws_key': r'(AKIA[0-9A-Z]{16})',
                'private_key': r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----',
                'jwt': r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*',
            }
           
            for secret_type, pattern in secret_patterns.items():
                matches = re.findall(pattern, content)
                if matches:
                    analysis['secrets_found'].append({
                        'type': secret_type,
                        'count': len(matches),
                        'sample': '[REDACTED]' if 'password' in secret_type or 'key' in secret_type else str(matches[0])[:30]
                    })
           
            # Patterns suspects
            suspicious = [
                ('Shell commands', r'(?:system|exec|popen|subprocess)\s*\('),
                ('SQL injection', r'(?i)SELECT.*FROM.*WHERE'),
                ('File operations', r'(?:open|fopen|file_get_contents)\s*\('),
                ('Network', r'(?:socket|curl|wget|urllib)'),
                ('Crypto', r'(?:encrypt|decrypt|cipher|AES|RSA)'),
            ]
           
            for name, pattern in suspicious:
                if re.search(pattern, content):
                    analysis['suspicious_patterns'].append(name)
       
        except Exception as e:
            analysis['error'] = str(e)
       
        return analysis
   
    # ========== ANALYSES TRANSVERSALES ==========
   
    def _extract_all_metadata(self, filepath: str) -> Dict:
        """Extrait toutes les métadonnées disponibles"""
        metadata = {
            'filesystem': {},
            'exiftool': {},
            'file_command': None,
        }
       
        # Métadonnées système
        try:
            stat = os.stat(filepath)
            metadata['filesystem'] = {
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'accessed': datetime.fromtimestamp(stat.st_atime).isoformat(),
                'permissions': oct(stat.st_mode)[-3:],
                'inode': stat.st_ino,
            }
        except:
            pass
       
        # Commande file
        try:
            result = subprocess.run(['file', '-b', filepath],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                metadata['file_command'] = result.stdout.strip()
        except:
            pass
       
        # exiftool (si disponible)
        try:
            result = subprocess.run(['exiftool', '-json', '-g', filepath],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                metadata['exiftool'] = json.loads(result.stdout)[0]
        except:
            pass
       
        return metadata
   
    def _detect_hidden_content(self, filepath: str) -> Dict:
        """Détecte du contenu caché ou inhabituel"""
        hidden = {
            'alternate_data_streams': [],  # Windows ADS
            'trailing_data': False,
            'embedded_files': [],
            'polyglot': False,
        }
       
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
           
            # Détection polyglot (fichier avec plusieurs signatures)
            signatures_found = []
            for ftype, sigs in self.FILE_SIGNATURES.items():
                for sig in sigs:
                    if sig in content:
                        signatures_found.append(ftype)
           
            if len(set(signatures_found)) > 1:
                hidden['polyglot'] = True
                hidden['signatures'] = list(set(signatures_found))
           
            # Données après EOF marker (PDF, ZIP, etc.)
            if content.startswith(b'%PDF'):
                eof = content.rfind(b'%%EOF')
                if eof != -1 and eof < len(content) - 10:
                    hidden['trailing_data'] = True
                    hidden['trailing_bytes'] = len(content) - eof
           
            elif content.startswith(b'PK'):
                # ZIP: données après End of Central Directory
                eocd = content.rfind(b'PK\x05\x06')
                if eocd != -1 and eocd < len(content) - 22:
                    hidden['trailing_data'] = True
                    hidden['trailing_bytes'] = len(content) - eocd - 22
           
            # Chercher des fichiers embarqués (signatures multiples)
            offset = 0
            while offset < len(content) - 4:
                for ftype, sigs in self.FILE_SIGNATURES.items():
                    for sig in sigs:
                        if content[offset:offset+len(sig)] == sig and offset > 0:
                            hidden['embedded_files'].append({
                                'type': ftype,
                                'offset': offset,
                                'signature': sig.hex()
                            })
                offset += 1
                if offset > 10000:  # Limite pour perf
                    break
       
        except Exception as e:
            hidden['error'] = str(e)
       
        return hidden
   
    def _security_checks(self, filepath: str, result: DeepAnalysisResult) -> List[str]:
        """Effectue des vérifications de sécurité"""
        issues = []
       
        # Extension dangereuse
        ext = Path(filepath).suffix.lower()
        if ext in self.DANGEROUS_EXTENSIONS:
            issues.append(f"⚠️ Dangerous extension: {ext}")
       
        # Discordance signature/extension
        sig_matches = result.file_signature.get('matches', [])
        if sig_matches and len(sig_matches) > 0:
            expected_type = sig_matches[0]
            if ext and expected_type not in ext:
                issues.append(f"⚠️ Signature ({expected_type}) does not match extension ({ext})")
       
        # Macros dans Office
        if 'office' in result.findings and result.findings['office'].get('has_macros'):
            issues.append("⚠️ Document contains VBA macros (code execution risk)")
       
        # JavaScript dans PDF
        if 'pdf' in result.findings and result.findings['pdf'].get('has_javascript'):
            issues.append("⚠️ PDF contains JavaScript (exploitation risk)")
       
        # Fichiers chiffrés/protégés
        if 'archive' in result.findings and result.findings['archive'].get('encrypted'):
            issues.append("⚠️ Archive protected by password")
       
        if 'pdf' in result.findings and result.findings['pdf'].get('encrypted'):
            issues.append("⚠️ Encrypted PDF")
       
        # Contenu caché
        if result.hidden_content.get('polyglot'):
            issues.append("🚨 Polyglot file detected (multiple signatures)")
       
        if result.hidden_content.get('trailing_data'):
            issues.append("⚠️ Data found after trailing EOCD/EOF marker")
       
        if result.hidden_content.get('embedded_files'):
            count = len(result.hidden_content['embedded_files'])
            issues.append(f"⚠️ {count} potentially embedded file(s)")
       
        # Scripts obfusqués
        if 'text' in result.findings:
            obfusc_score = result.findings['text'].get('obfuscation_score', 0)
            if obfusc_score > 5:
                issues.append(f"⚠️ Potentially obfuscated script (score: {obfusc_score})")
           
            if result.findings['text'].get('secrets_found'):
                count = len(result.findings['text']['secrets_found'])
                issues.append(f"🚨 {count} secret(s) or credential(s) detected")
       
        # Exécutables
        if 'executable' in result.findings:
            if result.findings['executable'].get('suspicious_indicators'):
                count = len(result.findings['executable']['suspicious_indicators'])
                issues.append(f"⚠️ {count} suspicious indicator(s) in executable")
       
        # GPS dans images
        if 'image' in result.findings and result.findings['image'].get('gps_location'):
            issues.append("⚠️ GPS coordinates found in image")
       
        return issues
   
    def _detect_risk_indicators(self, filepath: str, result: DeepAnalysisResult) -> List[str]:
        """Détecte des indicateurs de risque supplémentaires"""
        indicators = []
       
        # Nom de fichier suspect
        filename = os.path.basename(filepath).lower()
        suspicious_names = ['crack', 'keygen', 'patch', 'hack', 'exploit',
                          'backdoor', 'trojan', 'virus', 'malware']
        if any(susp in filename for susp in suspicious_names):
            indicators.append(f"Suspicious filename: {filename}")
       
        # Taille anormale
        size = os.path.getsize(filepath)
        if size == 0:
            indicators.append("Empty file")
        elif size > 1024 * 1024 * 1024:  # > 1GB
            indicators.append(f"Very large file: {size / (1024**3):.2f} GB")
       
        # Modification récente
        mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
        if (datetime.now() - mtime).total_seconds() < 3600:  # < 1h
            indicators.append("Modified very recently (< 1h)")
       
        # Archive avec beaucoup de fichiers
        if 'archive' in result.findings:
            file_count = result.findings['archive'].get('file_count', 0)
            if file_count > 1000:
                indicators.append(f"Archive with {file_count} files (potential zip bomb)")
           
            # Ratio de compression suspect
            ratio = result.findings['archive'].get('compression_ratio', 1)
            if ratio < 0.01:  # Compression > 100:1
                indicators.append(f"Very high compression ratio: {1/ratio:.0f}:1 (possible zip bomb)")
       
        # Base de données avec tables sensibles
        if 'database' in result.findings:
            sensitive = result.findings['database'].get('sensitive_tables', [])
            if sensitive:
                indicators.append(f"Database with {len(sensitive)} sensitive table(s)")
       
        return indicators

# ========== FONCTIONS UTILITAIRES ==========

def batch_analyze(directory: str, depth: str = "DEEP", pattern: str = "*") -> List[DeepAnalysisResult]:
    """Analyse en batch d'un dossier"""
    analyzer = DeepFileAnalyzer()
    results = []
   
    files = list(Path(directory).rglob(pattern))
    print(f"🔍 Analyzing {len(files)} files with depth: {depth}\n")
   
    for i, filepath in enumerate(files, 1):
        if filepath.is_file():
            try:
                result = analyzer.analyze(str(filepath), depth)
                results.append(result)
               
                risk_emoji = "🚨" if result.security_issues else "✅"
                print(f"[{i}/{len(files)}] {risk_emoji} {filepath.name}")
               
                if result.security_issues:
                    for issue in result.security_issues[:2]:
                        print(f"    • {issue}")
               
            except Exception as e:
                print(f"[{i}/{len(files)}] ❌ Error: {filepath.name} - {e}")
   
    return results

def generate_report(results: List[DeepAnalysisResult], output_file: str):
    """Génère un rapport détaillé"""
    report = {
        'summary': {
            'total_files': len(results),
            'files_with_issues': sum(1 for r in results if r.security_issues),
            'file_types': {},
        },
        'detailed_results': [asdict(r) for r in results]
    }
   
    # Compter par type
    for r in results:
        ftype = r.file_type
        report['summary']['file_types'][ftype] = report['summary']['file_types'].get(ftype, 0) + 1
   
    # Export JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
   
    print(f"\n📊 Report generated: {output_file}")
   
    # Résumé console
    print("\n" + "="*80)
    print("📋 SUMMARY")
    print("="*80)
    print(f"Total files: {report['summary']['total_files']}")
    print(f"Files with issues: {report['summary']['files_with_issues']}")
    print(f"\nFile types:")
    for ftype, count in sorted(report['summary']['file_types'].items(), key=lambda x: x[1], reverse=True):
        print(f"  • {ftype}: {count}")

def main():
    import sys
   
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python deep_analyzer.py <fichier>                    # Analyser un fichier")
        print("  python deep_analyzer.py --dir <dossier>              # Analyser un dossier")
        print("  python deep_analyzer.py --dir <dossier> --depth FORENSIC  # Profondeur max")
        sys.exit(1)
   
    if sys.argv[1] == '--dir':
        # Mode batch
        directory = sys.argv[2]
        depth = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == '--depth' else "DEEP"
       
        results = batch_analyze(directory, depth)
       
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"deep_analysis_report_{timestamp}.json"
        generate_report(results, output)
   
    else:
        # Mode fichier unique
        filepath = sys.argv[1]
        depth = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == '--depth' else "DEEP"
       
        analyzer = DeepFileAnalyzer()
        result = analyzer.analyze(filepath, depth)
       
        # Affichage détaillé
        print("\n" + "="*80)
        print(f"📄 ANALYSE APPROFONDIE: {os.path.basename(filepath)}")
        print("="*80)
        print(f"\nType: {result.file_type}")
        print(f"Profondeur: {result.analysis_depth}")
       
        if result.file_signature:
            print(f"\nSignature:")
            print(f"  • Hex: {result.file_signature.get('hex', 'N/A')}")
            print(f"  • Matches: {', '.join(result.file_signature.get('matches', []))}")
       
        if result.security_issues:
            print(f"\n🚨 PROBLÈMES DE SÉCURITÉ ({len(result.security_issues)}):")
            for issue in result.security_issues:
                print(f"  • {issue}")
       
        if result.risk_indicators:
            print(f"\n⚠️  INDICATEURS DE RISQUE ({len(result.risk_indicators)}):")
            for indicator in result.risk_indicators:
                print(f"  • {indicator}")
       
        print(f"\n📋 ANALYSES DÉTAILLÉES:")
        for key, data in result.findings.items():
            print(f"\n  [{key.upper()}]")
            if isinstance(data, dict):
                for k, v in list(data.items())[:10]:  # Limiter l'affichage
                    if isinstance(v, (str, int, float, bool)):
                        print(f"    • {k}: {v}")
                    elif isinstance(v, list) and len(v) > 0:
                        print(f"    • {k}: {len(v)} élément(s)")
       
        # Export JSON
        output = f"{Path(filepath).stem}_analysis.json"
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(asdict(result), f, indent=2, ensure_ascii=False)
        print(f"\n💾 Rapport détaillé: {output}")

if __name__ == "__main__":
    main()