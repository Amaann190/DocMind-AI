"""Local text extraction for every extension accepted by the uploader."""

import json
import mailbox
import os
import shutil
import subprocess
import tempfile
import zipfile
from contextlib import closing
from email import policy
from email.parser import BytesParser
from pathlib import Path

from llama_index.core import Document
from llama_index.core.readers.base import BaseReader

from utils.helpers import ALLOWED_UPLOAD_EXTENSIONS, MAX_UPLOAD_FILE_BYTES


def read_text(path):
    """Honor Unicode BOMs; retain Windows text instead of silently dropping bytes."""
    data = Path(path).read_bytes()
    if data.startswith((b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
        return data.decode("utf-32")
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252")


def html_text(content):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(content, "html.parser")
    for element in soup(["script", "style", "noscript"]):
        element.decompose()
    return soup.get_text(" ", strip=True)


def email_text(message):
    body = message.get_body(preferencelist=("plain", "html"))
    text = body.get_content() if body is not None else ""
    if body is not None and body.get_content_type() == "text/html":
        text = html_text(text)
    headers = "\n".join(
        f"{key}: {message[key]}" for key in ("Subject", "From", "To", "Date")
        if message[key]
    )
    return f"{headers}\n\n{text}".strip()


def libreoffice_executable():
    """Find a standard installation or an explicitly configured executable."""
    candidates = [os.environ.get("DOCMIND_LIBREOFFICE")]
    candidates.extend(shutil.which(name) for name in ("soffice", "libreoffice"))
    for root in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)")):
        if root:
            candidates.append(str(Path(root) / "LibreOffice/program/soffice.com"))
    candidates.append("/Applications/LibreOffice.app/Contents/MacOS/soffice")
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    raise RuntimeError(
        "Legacy DOC/PPT files require LibreOffice. Install LibreOffice or set "
        "DOCMIND_LIBREOFFICE to its soffice executable."
    )


def convert_legacy_office(file, extra_info):
    """Convert legacy Office locally, with an isolated profile and bounded runtime."""
    from llama_index.readers.file import DocxReader, PptxReader

    executable = libreoffice_executable()
    suffix = ".docx" if file.suffix.lower() == ".doc" else ".pptx"
    reader = DocxReader() if suffix == ".docx" else PptxReader(raise_on_error=True)
    with tempfile.TemporaryDirectory(prefix="docmind_office_") as directory:
        work = Path(directory)
        profile = work / "profile"
        (profile / "user").mkdir(parents=True)
        # Highest macro security: never run macros from an uploaded document.
        (profile / "user/registrymodifications.xcu").write_text(
            '<?xml version="1.0"?><oor:items xmlns:oor="http://openoffice.org/2001/registry">'
            '<item oor:path="/org.openoffice.Office.Common/Security/Scripting">'
            '<prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop>'
            '</item></oor:items>', encoding="utf-8",
        )
        # A fixed local basename avoids treating repository filenames as switches.
        source = work / ("input" + file.suffix.lower())
        shutil.copyfile(file, source)
        result = subprocess.run(
            [executable, f"-env:UserInstallation={profile.as_uri()}",
             "--headless", "--nologo", "--nodefault", "--norestore",
             "--convert-to", suffix[1:], "--outdir", str(work), str(source)],
            capture_output=True, timeout=120, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        converted = source.with_suffix(suffix)
        if result.returncode != 0 or not converted.is_file():
            raise ValueError(
                f"LibreOffice could not convert {file.name}. "
                "Check that it is a valid, unencrypted Office document."
            )
        return reader.load_data(converted, extra_info=extra_info)


class DocumentTextReader(BaseReader):
    """Fill gaps in LlamaIndex's automatic readers without a second pipeline."""

    def load_data(self, file, extra_info=None, **kwargs):
        file = Path(file)
        suffix = file.suffix.lower()
        metadata = dict(extra_info or {})
        metadata.setdefault("file_name", file.name)
        metadata.setdefault("file_path", str(file))

        if suffix in {".doc", ".ppt"}:
            return convert_legacy_office(file, metadata)
        if suffix in {".html", ".htm"}:
            text = html_text(file.read_bytes())
        elif suffix == ".xml":
            from defusedxml import ElementTree

            # Tags and attributes carry meaning (for example launch/code).
            # Parse safely, then retain that structure instead of returning bare values.
            text = ElementTree.tostring(ElementTree.fromstring(file.read_bytes()), encoding="unicode")
        elif suffix == ".rtf":
            from striprtf.striprtf import rtf_to_text

            text = rtf_to_text(read_text(file))
        elif suffix == ".odt":
            from defusedxml import ElementTree

            with zipfile.ZipFile(file) as archive:
                if archive.getinfo("content.xml").file_size > MAX_UPLOAD_FILE_BYTES:
                    raise ValueError("ODT content.xml exceeds the extraction size limit.")
                root = ElementTree.fromstring(archive.read("content.xml"))
            namespace = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
            text = "\n".join(
                "".join(element.itertext()) for element in root.iter()
                if element.tag in {namespace + "p", namespace + "h"}
            )
        elif suffix in {".eml", ".mhtml"}:
            text = email_text(BytesParser(policy=policy.default).parsebytes(file.read_bytes()))
        elif suffix == ".mbox":
            parser = BytesParser(policy=policy.default)
            with closing(mailbox.mbox(str(file), factory=parser.parse, create=False)) as box:
                return [Document(text=email_text(message), metadata=metadata) for message in box]
        elif suffix == ".msg":
            import extract_msg

            with extract_msg.openMsg(str(file), delayAttachments=True) as message:
                text = message.body or html_text(message.htmlBody or b"")
                text = f"Subject: {message.subject or ''}\n\n{text}"
        elif suffix == ".ipynb":
            notebook = json.loads(read_text(file))
            parts = []
            for cell in notebook.get("cells", []):
                source = cell.get("source", "")
                parts.append("".join(source) if isinstance(source, list) else source)
                for output in cell.get("outputs", []):
                    value = output.get("text") or output.get("data", {}).get("text/plain", "")
                    parts.append("".join(value) if isinstance(value, list) else value)
            text = "\n\n".join(parts)
        else:
            # CSV must retain its header for the existing table verbalizer.
            text = read_text(file)

        return [Document(text=text, metadata=metadata)]


def document_file_extractors():
    from llama_index.readers.file import DocxReader, EpubReader, PandasExcelReader, PDFReader, PptxReader

    text_reader = DocumentTextReader()
    readers = {extension: text_reader for extension in ALLOWED_UPLOAD_EXTENSIONS}
    readers.update({
        ".pdf": PDFReader(),
        ".docx": DocxReader(),
        ".epub": EpubReader(),
        ".pptx": PptxReader(raise_on_error=True),
        # Preserve the first row even in a headerless or single-cell workbook.
        ".xlsx": PandasExcelReader(pandas_config={"header": None, "engine": "openpyxl"}),
        ".xls": PandasExcelReader(pandas_config={"header": None, "engine": "xlrd"}),
    })
    return readers
