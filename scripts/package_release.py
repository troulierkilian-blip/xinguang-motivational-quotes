"""Build and verify a portable Windows release using explicit project files."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = "1.0.0"


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    dist = ROOT / "dist"
    archive = dist / f"xinguang-v{VERSION}-windows-x64.zip"
    files = {
        "心光.exe": dist / "心光.exe",
        "使用说明.txt": ROOT / "使用说明.txt",
        "LICENSE": ROOT / "LICENSE",
        "THIRD_PARTY_NOTICES.md": ROOT / "THIRD_PARTY_NOTICES.md",
        "验证报告.md": ROOT / "验证报告.md",
        "界面预览.png": ROOT / "docs" / "preview.png",
    }
    for path in sorted((ROOT / "assets" / "licenses").rglob("*")):
        if path.is_file():
            name = "licenses/" + path.relative_to(ROOT / "assets" / "licenses").as_posix()
            files[name] = path
    for name, path in files.items():
        if not path.is_file():
            raise FileNotFoundError(f"Missing release input: {name}")

    digests = {name: sha256_file(path) for name, path in files.items()}
    manifest = "".join(f"{digest}  {name}\n" for name, digest in digests.items())
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for name, path in files.items():
            bundle.write(path, name)
        bundle.writestr("SHA256SUMS.txt", manifest.encode("utf-8"))

    with zipfile.ZipFile(archive) as bundle:
        if set(bundle.namelist()) != set(files) | {"SHA256SUMS.txt"}:
            raise ValueError("Unexpected ZIP contents")
        bad_file = bundle.testzip()
        if bad_file:
            raise ValueError(f"ZIP CRC validation failed: {bad_file}")
        for name, expected in digests.items():
            actual = hashlib.sha256(bundle.read(name)).hexdigest()
            if actual != expected:
                raise ValueError(f"ZIP checksum mismatch: {name}")

    archive_hash = sha256_file(archive)
    checksums = dist / f"xinguang-v{VERSION}-SHA256SUMS.txt"
    checksums.write_text(f"{archive_hash}  {archive.name}\n"
                         f"{digests['心光.exe']}  心光.exe\n", encoding="utf-8")
    result = {"version": VERSION, "archive": archive.name,
              "bytes": archive.stat().st_size, "sha256": archive_hash,
              "exe_sha256": digests["心光.exe"], "entries": len(files) + 1,
              "checksum_file": checksums.name, "verified": True}
    (dist / "release-manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
