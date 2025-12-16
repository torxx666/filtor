# Anti-Exfiltration Forensic Analyzer
# Advanced detection of information theft (USB keys, sensitive documents, etc.)

import os
import re
import hashlib
import magic  # python-magic
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import asdict, dataclass, field
import zipfile
import tarfile
import math

@dataclass
class ForensicResult:
    """Detailed forensic analysis result"""
    filepath: str
    risk_score: float  # 0-100
    risk_level: str    # LOW, MEDIUM, HIGH, CRITICAL
    is_sensitive: bool
    detections: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

class DataExfiltrationAnalyzer:
    """Forensic analyzer to detect data exfiltration"""
    
    def __init__(self):
        self.magic = magic.Magic(mime=True)
        self.suspicious_extensions = ['.enc', '.pgp', '.gpg', '.kdbx', '.axx', '.crypt', '.shadow']
        
        # SENSITIVE EXTENSIONS
        self.SENSITIVE_EXTENSIONS = [
            # Databases
            '.db', '.sqlite', '.sqlite3', '.sql', '.mdf', '.ldf', '.accdb', '.mdb',
            # Credentials / Config
            '.pem', '.ppk', '.key', '.kdbx', '.ovpn', '.shadow', '.htpasswd',
            '.config', '.conf', '.cfg', '.ini', '.env', '.json', '.xml',
            # Source Code
            '.py', '.js', '.php', '.java', '.c', '.cpp', '.go', '.rb',
            # Documents (if unexpected context)
            '.xls', '.xlsx', '.doc', '.docx', '.pdf',
            # Crypto Wallets
            '.wallet', '.dat', '.keystore', '.json'
        ]
        
        # Sensitive keywords in filenames
        self.SENSITIVE_KEYWORDS = [
            'pass', 'pwd', 'secret', 'credential', 'login', 'auth', 'token', 'key',
            'backup', 'dump', 'export', 'private', 'confidential', 'compte', 'banque',
            'rib', 'facture', 'contrat', 'salary', 'payroll', 'admin', 'root'
        ]

    def analyze_file(self, filepath: str, context: Optional[Dict] = None) -> ForensicResult:
        """Complete forensic analysis of a file"""
        detections = {}
        risk_score = 0.0
        
        try:
            if not os.path.exists(filepath):
                return self._create_error_result(filepath, "File does not exist")
            
            # Base metadata
            metadata = self._extract_metadata(filepath)
            
            # 1. Filename Analysis
            name_check = self._check_filename_sensitivity(filepath)
            detections['filename'] = name_check
            risk_score += name_check['risk_points']
            
            # 2. Temporal Analysis (recent access/modification)
            temporal_check = self._check_temporal_anomalies(metadata)
            detections['temporal'] = temporal_check
            risk_score += temporal_check['risk_points']
            
            # 3. Type and Extension Analysis
            type_check = self._check_file_type(filepath)
            detections['file_type'] = type_check
            risk_score += type_check['risk_points']
            
            # 4. Sensitive Content Detection
            content_check = self._scan_file_content(filepath)
            detections['sensitive_content'] = content_check
            risk_score += content_check['risk_points']
            
            # 5. Structural Analysis (Office files, PDF, etc.)
            structure_check = self._analyze_structure(filepath, type_check['mime_type'])
            detections['structure'] = structure_check
            risk_score += structure_check['risk_points']
            
            # 6. Steganography Detection
            stego_check = self._detect_steganography(filepath, type_check['mime_type'])
            detections['steganography'] = stego_check
            risk_score += stego_check['risk_points']
            
            # 7. Archive Analysis (hidden content)
            archive_check = self._analyze_archive(filepath)
            detections['archives'] = archive_check
            risk_score += archive_check['risk_points']
            
            # 8. Unusual Encoding/Compression Detection
            encoding_check = self._analyze_encoding(filepath)
            detections['encoding'] = encoding_check
            risk_score += encoding_check['risk_points']
            
            # 9. Size vs Type Analysis
            size_check = self._analyze_size_anomaly(filepath)
            detections['size_anomaly'] = size_check
            risk_score += size_check['risk_points']
            
            # 10. EXIF Metadata Detection (geolocation, author)
            exif_check = self._extract_exif(filepath)
            detections['exif'] = exif_check
            risk_score += exif_check['risk_points']
            
            # 11. Duplication Analysis (recently copied files)
            dup_check = self._check_duplication(filepath, context, metadata.get('hash'))
            detections['duplication'] = dup_check
            risk_score += dup_check['risk_points']
            
            # 12. Database Detection
            db_check = self._analyze_database(filepath)
            detections['database'] = db_check
            risk_score += db_check['risk_points']
            
            # Generate recommendations
            recommendations = self._generate_recommendations(detections, risk_score)
            
            # Cap risk score at 100
            risk_score = min(risk_score, 100.0)
            
            return ForensicResult(
                filepath=filepath,
                risk_score=round(risk_score, 1),
                risk_level=self._calculate_risk_level(risk_score),
                is_sensitive=(risk_score >= 50),
                detections=detections,
                metadata=metadata,
                recommendations=recommendations
            )
            
        except Exception as e:
            return self._create_error_result(filepath, str(e))

    def _extract_metadata(self, filepath: str) -> Dict[str, Any]:
        """Extracts system metadata from the file"""
        stat = os.stat(filepath)
        return {
            'size_bytes': stat.st_size,
            'size_human': self._human_readable_size(stat.st_size),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'accessed': datetime.fromtimestamp(stat.st_atime).isoformat(),
            'owner_uid': stat.st_uid,
            'permissions': oct(stat.st_mode)[-3:],
            'hash': self._calculate_hash(filepath)
        }

    def _check_filename_sensitivity(self, filepath: str) -> Dict[str, Any]:
        """Analyzes filename for suspicious patterns"""
        filename = os.path.basename(filepath).lower()
        risk_points = 0.0
        indicators = []
        
        # Suspicious keywords
        for keyword in self.SENSITIVE_KEYWORDS:
            if keyword in filename:
                indicators.append(f"Sensitive keyword: {keyword}")
                risk_points += 10
        
        # Suspicious patterns
        if re.search(r'(copy|copie|backup|dump|export).*\d{4}', filename):
            indicators.append("Backup/Export pattern")
            risk_points += 15
        
        if re.search(r'(temp|tmp|test).*\.(zip|rar|7z)', filename):
            indicators.append("Suspicious temporary archive")
            risk_points += 12
        
        # Generic suspicious names
        generic_patterns = ['download', 'new', 'untitled', 'document1', 'sans_titre']
        if any(p in filename for p in generic_patterns):
            indicators.append("Suspicious generic name")
            risk_points += 5
        
        return {
            'risk_points': risk_points,
            'indicators': indicators
        }
    
    def _check_temporal_anomalies(self, metadata: Dict) -> Dict[str, Any]:
        """Analyzes timestamps for anomalies"""
        now = datetime.now()
        modified = datetime.fromisoformat(metadata['modified'])
        accessed = datetime.fromisoformat(metadata['accessed'])
        
        risk_points = 0.0
        indicators = []
        
        # Recent modification (last 24h)
        if (now - modified).total_seconds() < 86400:
            indicators.append(f"Modified {self._time_ago(modified)} ago")
            risk_points += 15
        
        # Recent access (last 2h)
        if (now - accessed).total_seconds() < 7200:
            indicators.append(f"Accessed {self._time_ago(accessed)} ago")
            risk_points += 10
        
        # Access outside working hours
        if accessed.hour < 7 or accessed.hour > 20 or accessed.weekday() >= 5:
            indicators.append(f"Access off-hours: {accessed.strftime('%Y-%m-%d %H:%M')}")
            risk_points += 20
        
        return {
            'risk_points': risk_points,
            'indicators': indicators
        }

    def _check_file_type(self, filepath: str) -> Dict[str, Any]:
        """Analyzes file type and extension"""
        mime_type = self.magic.from_file(filepath)
        extension = Path(filepath).suffix.lower()
        
        risk_points = 0.0
        indicators = []
        
        # Sensitive extension
        if extension in self.SENSITIVE_EXTENSIONS:
            indicators.append(f"Sensitive extension: {extension}")
            risk_points += 15
        
        # Mime Type mismatch
        if extension and not self._mime_matches_extension(mime_type, extension):
            indicators.append(f"Real type ({mime_type}) != extension ({extension})")
            risk_points += 25
        
        # Executable files
        if 'executable' in mime_type or extension in ['.exe', '.dll', '.so', '.dylib']:
            indicators.append("Executable file")
            risk_points += 20
        
        return {
            'mime_type': mime_type,
            'extension': extension,
            'risk_points': risk_points,
            'indicators': indicators
        }

    def _scan_file_content(self, filepath: str) -> Dict[str, Any]:
        """Scans content for sensitive patterns (Credit Cards, Emails, IPs)"""
        risk_points = 0.0
        findings = {}
        
        # Regex patterns
        patterns = {
            'credit_card': r'\b(?:\d[ -]*?){13,16}\b',
            'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            'ipv4': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            'phone_us': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'ssn_us': r'\b\d{3}-\d{2}-\d{4}\b',
            'iban': r'\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b',
            'private_key': r'-----BEGIN (RSA|DSA|EC|OPENSSH|PGP) PRIVATE KEY-----',
            'aws_key': r'(AKIA|ASIA)[0-9A-Z]{16}',
            'aws_secret': r'(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])',
            'google_api': r'AIza[0-9A-Za-z\\-_]{35}',
            'azure_key': r'[a-zA-Z0-9+/=]{88}',
            'slack_token': r'xox[baprs]-([0-9a-zA-Z]{10,48})',
            'crypto_address': r'\b(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b|\b0x[a-fA-F0-9]{40}\b'
        }
        
        # --- PRO FORENSIC CHECKS ---
        
        # 1. Hacking Tools & Lateral Movement
        hacking_keywords = ['mimikatz', 'procdump', 'psexec', 'cobaltstrike', 'meterpreter', 'beacon', 'sharphound']
        filename = os.path.basename(filepath).lower()
        if any(k in filename for k in hacking_keywords) or filename in ['lsass.dmp', 'shadow.copy']:
            findings['hacking_tool'] = {'matched': filename}
            risk_points += 40 # CRITICAL
            
        # 2. Obfuscation Detection
        # Double Extension (e.g. invoice.pdf.exe)
        if re.search(r'\.[a-z]{3,4}\.(exe|bat|ps1|vbs|js)$', filename):
            findings['double_extension'] = {'filename': filename}
            risk_points += 30
            
        # RTLO Character (Right-to-Left Override) - U+202E
        if '\u202e' in os.path.basename(filepath):
            findings['rtlo_spoofing'] = {'detected': True}
            risk_points += 50
            
        total_matches = 0
        try:
            # Read file (limited to first 1MB for perf)
            with open(filepath, 'rb') as f_bin:
                head = f_bin.read(4096)
                
            # 3. Magic Bytes Analysis (Header Mismatch)
            # Simple check for common mismatches
            ext = Path(filepath).suffix.lower()
            if ext in ['.jpg', '.jpeg'] and not head.startswith(b'\xff\xd8'):
                findings['header_mismatch'] = {'expected': 'JPEG', 'found': head[:4].hex()}
                risk_points += 20
            if ext == '.pdf' and not head.startswith(b'%PDF'):
                findings['header_mismatch'] = {'expected': 'PDF', 'found': head[:4].hex()}
                risk_points += 20
            if ext == '.exe' and not head.startswith(b'MZ'):
                findings['header_mismatch'] = {'expected': 'PE (MZ)', 'found': head[:4].hex()}
                risk_points += 20
                
            # Decode for Regex (Fallback to text search)
            try:
                content = head.decode('utf-8', errors='ignore')
            except: content = ""
                
            # Check entropy on first 4KB
            entropy = self._calculate_entropy(head)
            findings['entropy'] = round(entropy, 2)
            
            # High entropy > 7.5 often indicates encryption or compression
            # Raise risk only if file type doesn't justify it (e.g. not zip/jpg)
            safe_high_entropy = ['.zip', '.7z', '.rar', '.gz', '.jpg', '.png', '.mp4', '.pdf', '.docx', '.xlsx']
            if entropy > 7.5 and ext not in safe_high_entropy:
                findings['high_entropy'] = {
                    'value': round(entropy, 2),
                    'note': 'Encrypted data or obfuscated payload (High Entropy)'
                }
                risk_points += 25
            
            # Regex Scan on text content
            for name, pattern in patterns.items():
                matches = re.findall(pattern, content)
                if matches:
                    count = len(matches)
                    findings[name] = {'count': count, 'samples': matches[:3]}
                    risk_points += (count * 2) + 10  # Base 10 + 2 per match
                    total_matches += count

        except Exception as e:
            findings['error'] = str(e)
            
        return {
            'risk_points': risk_points,
            'total_matches': total_matches,
            'findings': findings
        }

    def _analyze_structure(self, filepath: str, mime_type: str) -> Dict[str, Any]:
        """Analyzes structure of Office docs, PDFs, etc."""
        risk_points = 0.0
        indicators = []
        
        mime = self.magic.from_file(filepath)
        
        # Office Documents (macros, metadata)
        if any(x in mime for x in ['officedocument', 'msword', 'ms-excel', 'ms-powerpoint']):
            indicators.append("Office Document (may contain macros/metadata)")
            risk_points += 10
            
            # Check macros
            if self._has_macros(filepath):
                indicators.append("⚠️ Contains VBA macros")
                risk_points += 25
        
        # PDF
        if 'pdf' in mime:
            indicators.append("PDF Document")
            risk_points += 5
            
            # Check JS in PDF
            if self._pdf_has_javascript(filepath):
                indicators.append("⚠️ PDF contains JavaScript")
                risk_points += 20
        
        return {
            'risk_points': risk_points,
            'indicators': indicators
        }
        
    def _detect_steganography(self, filepath: str, mime_type: str) -> Dict[str, Any]:
        """Detects potential steganography in images"""
        risk_points = 0.0
        indicators = []
        
        if 'image' in mime_type:
            try:
                size = os.path.getsize(filepath)
                
                # Abnormally large image
                if size > 5 * 1024 * 1024:  # > 5MB
                    indicators.append(f"Large image ({self._human_readable_size(size)})")
                    risk_points += 15
                
                # LSB Analysis
                with open(filepath, 'rb') as f:
                    data = f.read()
                
                # Detect unusual bit patterns
                if self._detect_lsb_anomaly(data):
                    indicators.append("LSB anomaly detected (potential steganography)")
                    risk_points += 25
                
            except Exception as e:
                indicators.append(f"Analysis error: {e}")
        
        return {
            'risk_points': risk_points,
            'indicators': indicators
        }
        
    def _analyze_archive(self, filepath: str) -> Dict[str, Any]:
        """Analyzes archive content"""
        risk_points = 0.0
        indicators = []
        content_summary = {}
        
        try:
            ext = Path(filepath).suffix.lower()
            if ext in ['.zip', '.jar', '.apk', '.docx', '.xlsx', '.pptx']:
                with zipfile.ZipFile(filepath, 'r') as zf:
                    files = zf.namelist()
                    content_summary['file_count'] = len(files)
                    content_summary['files'] = files[:20]  # Limit to 20
                    
                    # Sensitive files in archive
                    sensitive = [f for f in files if any(k in f.lower() for k in self.SENSITIVE_KEYWORDS)]
                    if sensitive:
                        indicators.append(f"Sensitive files: {len(sensitive)}")
                        risk_points += 20
                    
                    # Password protected
                    for info in zf.infolist():
                        if info.flag_bits & 0x1:
                            indicators.append("Password protected archive")
                            risk_points += 15
                            break
            
            elif ext in ['.tar', '.gz', '.bz2']:
                with tarfile.open(filepath, 'r:*') as tf:
                    files = tf.getnames()
                    content_summary['file_count'] = len(files)
                    content_summary['files'] = files[:20]
                    
                    sensitive = [f for f in files if any(k in f.lower() for k in self.SENSITIVE_KEYWORDS)]
                    if sensitive:
                        indicators.append(f"Sensitive files: {len(sensitive)}")
                        risk_points += 20
            
        except Exception as e:
            indicators.append(f"Archive read error: {e}")
        
        return {
            'risk_points': risk_points,
            'indicators': indicators,
            'content': content_summary
        }
        
    def _analyze_encoding(self, filepath: str) -> Dict[str, Any]:
        """Detects base64 or multiple encoding layers"""
        risk_points = 0.0
        indicators = []
        
        try:
            with open(filepath, 'rb') as f:
                header = f.read(512)
            
            # Base64 Detection
            if self._is_likely_base64(header):
                indicators.append("Base64 content detected")
                risk_points += 10
            
            # Non-standard compressed files
            compression_signatures = {
                b'\x1f\x8b': 'gzip',
                b'BZh': 'bzip2',
                b'\xfd7zXZ\x00': 'xz',
                b'\x28\xb5\x2f\xfd': 'zstd',
            }
            
            for sig, comp_type in compression_signatures.items():
                if header.startswith(sig):
                    ext = Path(filepath).suffix.lower()
                    if ext not in ['.gz', '.bz2', '.xz', '.zst']:
                        indicators.append(f"Hidden {comp_type} compression (ext: {ext})")
                        risk_points += 20
            
        except Exception as e:
            pass
            
        return {
            'risk_points': risk_points,
            'indicators': indicators
        }
        
    def _analyze_size_anomaly(self, filepath: str) -> Dict[str, Any]:
        """Analyzes size anomalies"""
        risk_points = 0.0
        indicators = []
        
        size = os.path.getsize(filepath)
        
        # Large files
        if size > 100 * 1024 * 1024:  # > 100MB
            indicators.append(f"Very large file: {self._human_readable_size(size)}")
            risk_points += 20
        
        # Empty sensitive files
        ext = Path(filepath).suffix.lower()
        if size == 0 and ext in self.SENSITIVE_EXTENSIONS:
            indicators.append("Empty file with sensitive extension")
            risk_points += 15
        
        return {
            'risk_points': risk_points,
            'indicators': indicators
        }
        
    def _extract_exif(self, filepath: str) -> Dict[str, Any]:
        """Extracts EXIF using exiftool if available"""
        risk_points = 0.0
        indicators = []
        exif_data = {}
        
        try:
            import subprocess
            result = subprocess.run(['exiftool', '-j', filepath], capture_output=True, text=True)
            if result.returncode == 0:
                data = json.loads(result.stdout)[0]
                
                # Sensitive fields
                sensitive_fields = ['GPS', 'Location', 'Author', 'Creator', 'Company', 'Owner']
                for field in sensitive_fields:
                    matching = {k: v for k, v in data.items() if field in k}
                    if matching:
                        exif_data[field] = matching
                        indicators.append(f"Metadata {field} present")
                        risk_points += 10
                
        except FileNotFoundError:
            pass  # exiftool not installed
        except Exception:
            pass
            
        return {
            'risk_points': risk_points,
            'indicators': indicators,
            'data': exif_data
        }
        
    def _check_duplication(self, filepath: str, context: Optional[Dict], file_hash: str) -> Dict[str, Any]:
        """Checks for duplicated files"""
        risk_points = 0.0
        indicators = []
        
        # If context provided with other analyzed files
        if context and 'file_hashes' in context:
            if file_hash in context['file_hashes']:
                indicators.append(f"Duplicate file detected")
                risk_points += 15
        
        # Pattern de nom (Copy, Copie, etc.)
        filename = os.path.basename(filepath).lower()
        if re.search(r'(copy|copie|\(\d+\))', filename):
            indicators.append("Name indicates a copy")
            risk_points += 10
        
        return {
            'risk_points': risk_points,
            'indicators': indicators
        }
    
    def _analyze_database(self, filepath: str) -> Dict[str, Any]:
        """Analyzes database files"""
        risk_points = 0.0
        indicators = []
        db_info = {}
        
        ext = Path(filepath).suffix.lower()
        
        if ext in ['.sqlite', '.sqlite3', '.db']:
            try:
                conn = sqlite3.connect(f'file:{filepath}?mode=ro', uri=True)
                cursor = conn.cursor()
                
                # Tables check
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [r[0] for r in cursor.fetchall()]
                db_info['tables'] = tables
                
                # Count records (approx)
                total_records = 0
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        total_records += cursor.fetchone()[0]
                    except: pass
                db_info['total_records'] = total_records
                
                indicators.append(f"SQLite Database: {len(tables)} tables, {total_records} records")
                risk_points += 25
                
                # Sensitive tables
                sensitive_tables = [t for t in tables if any(k in t.lower() for k in ['user', 'client', 'password', 'credential', 'employee'])]
                if sensitive_tables:
                    indicators.append(f"Sensitive tables: {', '.join(sensitive_tables)}")
                    risk_points += 20
                
                conn.close()
            except Exception as e:
                indicators.append(f"DB read error: {e}")
        
        elif ext == '.sql':
            # SQL Dump
            indicators.append("SQL Dump file")
            risk_points += 20
            
            try:
                with open(filepath, 'r', errors='ignore') as f:
                    head = f.read(2048)
                    if 'CREATE TABLE' in head.upper() or 'INSERT INTO' in head.upper():
                         indicators.append("Contains SQL schema/data")
                         risk_points += 10
            except: pass
            
        return {
            'risk_points': risk_points,
            'indicators': indicators,
            'info': db_info
        }

    def _generate_recommendations(self, detections: Dict, risk_score: float) -> List[str]:
        """Generates recommendations based on detections"""
        recs = []
        
        if risk_score >= 70:
            recs.append("🚨 ALERT: Highly suspicious file - Immediate investigation recommended")
            recs.append("Isolate file and source (USB key, etc.)")
            recs.append("Check system access logs")
        
        if detections.get('sensitive_content', {}).get('total_matches', 0) > 0:
            recs.append("Sensitive data detected - Verify if exfiltration is authorized")
        
        if detections.get('temporal', {}).get('risk_points', 0) > 15:
            recs.append("Recent access/modification - Check user activity")
        
        if detections.get('archives', {}).get('risk_points', 0) > 0:
            recs.append("Archive detected - Analyze full content")
        
        if detections.get('database', {}).get('risk_points', 0) > 0:
            recs.append("Database file - Verify if dump is authorized")
        
        if detections.get('exif', {}).get('risk_points', 0) > 0:
            recs.append("Metadata present - Clean before external sharing")
        
        return recs
    
    # --- Helper Methods ---
    
    def _calculate_risk_level(self, score: float) -> str:
        """Determines risk level"""
        if score >= 70:
            return "CRITICAL"
        elif score >= 50:
            return "HIGH"
        elif score >= 30:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _human_readable_size(self, size_bytes: int) -> str:
        """Converts size to readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    def _time_ago(self, dt: datetime) -> str:
        """Returns elapsed time string"""
        delta = datetime.now() - dt
        if delta.days > 0:
            return f"{delta.days}d"
        elif delta.seconds > 3600:
            return f"{delta.seconds // 3600}h"
        else:
            return f"{delta.seconds // 60}min"

    def _mime_matches_extension(self, mime: str, ext: str) -> bool:
        """Check consistency between MIME type and extension"""
        # Basic mapping - can be improved
        mapping = {
            'text/plain': ['.txt', '.log', '.ini', '.cfg', '.md', '.py', '.js', '.json', '.xml'],
            'image/jpeg': ['.jpg', '.jpeg'],
            'image/png': ['.png'],
            'application/pdf': ['.pdf'],
            'application/zip': ['.zip', '.docx', '.xlsx', '.pptx', '.jar', '.apk'],
            'application/x-dosexec': ['.exe', '.dll'],
            'application/x-executable': ['.elf', '.so'],
        }
        
        for m, exts in mapping.items():
            if m in mime:
                return ext in exts
        return True # Default lenient

    def _calculate_entropy(self, data: bytes) -> float:
        """Shannon Entropy Calculation on bytes"""
        if not data:
            return 0
        if isinstance(data, str):
            data = data.encode('utf-8', errors='ignore')
            
        prob = [float(data.count(b)) / len(data) for b in dict.fromkeys(list(data))]
        return - sum([p * math.log(p) / math.log(2.0) for p in prob])

    def _calculate_hash(self, filepath: str) -> str:
        """Calculates SHA256 of the file"""
        sha256_hash = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except:
            return "error"
            
    def _create_error_result(self, filepath: str, error: str) -> ForensicResult:
        """Creates an error result"""
        return ForensicResult(
            filepath=filepath,
            risk_score=0.0,
            risk_level="UNKNOWN",
            is_sensitive=False,
            detections={'error': error},
            metadata={},
            recommendations=["Error during analysis"]
        )
        
    def _has_macros(self, filepath: str) -> bool:
        """Basic check for VBA Macros (OLEDUMP style or zip inspection)"""
        try:
            # Check for vbaProject.bin in zip structure
            if zipfile.is_zipfile(filepath):
                 with zipfile.ZipFile(filepath, 'r') as z:
                     if 'xl/vbaProject.bin' in z.namelist() or 'word/vbaProject.bin' in z.namelist():
                         return True
        except: pass
        return False
        
    def _pdf_has_javascript(self, filepath: str) -> bool:
        """Checks for JS in PDF"""
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
                if b'/JavaScript' in content or b'/JS' in content:
                    return True
        except: pass
        return False
    
    def _is_likely_base64(self, data: bytes) -> bool:
        """Checks if data looks like Base64"""
        if len(data) < 20: return False
        try:
            return re.match(b'^[A-Za-z0-9+/]+={0,2}$', data) is not None
        except: return False
    
    def _detect_lsb_anomaly(self, data: bytes) -> bool:
        """Basic LSB anomaly detection"""
        # Complex to do in pure python efficiently on raw bytes without PIL/cv2
        # Placeholder logic
        return False


if __name__ == "__main__":
    # Test script similar to a USB dump
    
    print("🕵️  ANTI-EXFILTRATION FORENSIC ANALYZER")
    print("=======================================")
    
    target_dir = input("Enter directory to analyze (default ./incoming): ") or "./incoming"
    
    analyzer = DataExfiltrationAnalyzer()
    
    # Collect all files
    all_files = []
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            all_files.append(os.path.join(root, file))
            
    print(f"📁 {len(all_files)} files found")
    print("Starting analysis...\n")
    
    results = []
    critical = []
    
    # Parallel analysis
    # For dev simplicity -> sequential
    for f in all_files:
        print(f"Analyzing {os.path.basename(f)}...", end='\r')
        res = analyzer.analyze_file(f)
        results.append(res)
        if res.risk_score >= 50:
            critical.append(res)
            
    print(f"\n\n📊 FORENSIC ANALYSIS REPORT - DATA EXFILTRATION")
    print("===============================================")
    print(f"  • Total files analyzed: {len(results)}")
    print(f"  • Suspicious files: {len(critical)}")
    print("===============================================")
    
    # Critical files
    if critical:
        print(f"\n🚨 CRITICAL FILES ({len(critical)}):")
        for c in critical:
            print(f"\n  [!] {os.path.basename(c.filepath)}")
            print(f"      Risk Score: {c.risk_score} ({c.risk_level})")
            
            # Top detections
            print(f"      Detections:")
            for k, v in c.detections.items():
                if v.get('risk_points', 0) > 0:
                    print(f"       - {k.upper()}: {len(v.get('indicators', []))} indicators")
            
            # Recommendations
            if c.recommendations:
                print(f"     Recommendations:")
                for r in c.recommendations:
                    print(f"       -> {r}")
    else:
        print("\n✅ No threats detected.")