from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

from rdflib import Graph
from pyshacl import validate

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "ontology" / "gcci_formal_ontology_v1.0.0.zip"


def main() -> None:
    if not PACKAGE.exists():
        raise SystemExit(f"Ontology package not found: {PACKAGE}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(PACKAGE) as archive:
            archive.extractall(tmp_path)

        ttl_files = sorted(tmp_path.rglob("*.ttl"))
        if not ttl_files:
            raise SystemExit("No Turtle files found in ontology package")

        parsed = []
        for ttl in ttl_files:
            Graph().parse(ttl, format="turtle")
            parsed.append(str(ttl.relative_to(tmp_path)))

        data_file = tmp_path / "examples" / "phillips-demo.ttl"
        shape_files = sorted((tmp_path / "shapes").glob("*.ttl"))
        if not data_file.exists() or not shape_files:
            raise SystemExit("Synthetic example graph or SHACL shapes are missing")

        data_graph = Graph().parse(data_file, format="turtle")
        shapes_graph = Graph()
        for shape_file in shape_files:
            shapes_graph.parse(shape_file, format="turtle")

        conforms, _report_graph, report_text = validate(
            data_graph,
            shacl_graph=shapes_graph,
            inference="rdfs",
            abort_on_first=False,
            allow_infos=True,
            allow_warnings=True,
        )

        result = {
            "package": PACKAGE.name,
            "ttl_files_parsed": len(parsed),
            "files": parsed,
            "shacl_conforms": bool(conforms),
            "report": report_text,
        }
        print(json.dumps(result, indent=2))

        if not conforms:
            raise SystemExit("SHACL validation failed")


if __name__ == "__main__":
    main()
