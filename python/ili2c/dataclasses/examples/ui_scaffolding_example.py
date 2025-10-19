"""Generate HTML scaffolding from INTERLIS dataclasses without extra dependencies."""
from __future__ import annotations

import argparse
import sys
from dataclasses import fields
from html import escape
from pathlib import Path
from types import ModuleType
from typing import Iterable

from ..generator import DataclassGenerator
from ...pyili2c.parser import parse


DATA_DIR = Path(__file__).resolve().parent / "data"
MODEL_PATH = DATA_DIR / "simple.ili"


def _load_dataclass_module(model_path: Path) -> ModuleType:
    """Parse *model_path* and return an in-memory module with generated dataclasses."""

    model = parse(model_path).getModels()[0]
    source = DataclassGenerator(model).build_module()
    module = ModuleType("generated_ui_model")
    sys.modules[module.__name__] = module
    exec(source, module.__dict__)
    return module


def _field_label(field_name: str, info: dict) -> str:
    label = info.get("display_name") or field_name.replace("_", " ").title()
    return escape(label)


def _scalar_input(field, info: dict) -> str:
    """Return HTML for a scalar field using INTERLIS metadata."""

    attributes: list[str] = []
    input_type = "text"
    python_type = info.get("python_type")

    if info.get("alias_kind") == "boolean":
        input_type = "checkbox"
    elif python_type == "int":
        input_type = "number"
        if info.get("minimum") is not None:
            attributes.append(f"min=\"{info['minimum']}\"")
        if info.get("maximum") is not None:
            attributes.append(f"max=\"{info['maximum']}\"")
    elif python_type == "float":
        input_type = "number"
        attributes.append("step=\"any\"")
    elif info.get("qualified_target"):
        attributes.append(f"data-target=\"{escape(info['qualified_target'])}\"")

    max_length = info.get("max_length")
    if max_length:
        attributes.append(f"maxlength=\"{max_length}\"")

    if info.get("mandatory"):
        attributes.append("required")

    placeholder: str | None = None
    if info.get("qualified_target"):
        placeholder = info["qualified_target"].split(".")[-1]
    elif info.get("alias_kind") == "boolean":
        placeholder = None
    elif info.get("literals"):
        placeholder = "Select a value"
    elif python_type in {"int", "float"}:
        placeholder = "Enter a number"
    else:
        placeholder = "Enter text"

    attr_text = " ".join(attributes)
    name_attr = escape(field.name)
    label = _field_label(field.name, info)

    if info.get("literals"):
        options = "\n".join(
            f"        <option value=\"{escape(value)}\">{escape(value)}</option>"
            for value in info["literals"]
        )
        required_attr = " required" if info.get("mandatory") else ""
        return (
            f"    <label class=\"field\">{label}\n"
            f"      <select name=\"{name_attr}\"{required_attr}>\n"
            f"        <option value=\"\">-- choose --</option>\n"
            f"{options}\n"
            "      </select>\n"
            "    </label>"
        )

    placeholder_attr = f" placeholder=\"{escape(placeholder)}\"" if placeholder else ""
    attr_text = f" {attr_text}" if attr_text else ""
    checked_attr = " checked" if input_type == "checkbox" and info.get("default") else ""
    input_html = (
        f"      <input type=\"{input_type}\" name=\"{name_attr}\"{placeholder_attr}{attr_text}{checked_attr}>"
    )
    return f"    <label class=\"field\">{label}\n{input_html}\n    </label>"


def _list_input(field, info: dict) -> str:
    """Render HTML for a LIST attribute using a repeatable template."""

    items = info.get("items", {})
    item_placeholder = items.get("qualified_target") or items.get("target") or "Item"
    item_placeholder = item_placeholder.split(".")[-1]
    label = _field_label(field.name, info)
    required = info.get("cardinality", {}).get("min", 0) > 0
    requirement_note = "<span class=\"hint\">At least one entry required.</span>" if required else ""
    name_attr = escape(field.name)
    required_attr = " required" if required else ""

    return (
        f"    <fieldset class=\"list-field\" data-field=\"{name_attr}\">\n"
        f"      <legend>{label}</legend>\n"
        f"      {requirement_note}\n"
        "      <div class=\"list-items\">\n"
        "        <div class=\"list-item\" data-template=\"true\">\n"
        f"          <input type=\"text\" name=\"{name_attr}[]\" placeholder=\"{escape(item_placeholder)}\"{required_attr}>\n"
        "        </div>\n"
        "      </div>\n"
        "      <button type=\"button\" data-action=\"add-item\">Add another</button>\n"
        "    </fieldset>"
    )


def _render_form(cls) -> str:
    meta = getattr(cls, "Meta")
    title = escape(meta.ili_name)
    field_blocks: list[str] = []
    for field in fields(cls):
        info = dict(field.metadata["ili"])
        info.setdefault("mandatory", False)
        if info.get("ili_type") == "ListType":
            field_blocks.append(_list_input(field, info))
        else:
            field_blocks.append(_scalar_input(field, info))
    inner = "\n".join(field_blocks)
    return (
        f"  <section class=\"model\">\n"
        f"    <h2>{title}</h2>\n"
        "    <form>\n"
        f"{inner}\n"
        "      <div class=\"actions\">\n"
        "        <button type=\"submit\">Submit</button>\n"
        "      </div>\n"
        "    </form>\n"
        "  </section>"
    )


def build_html(module: ModuleType) -> str:
    """Return a standalone HTML document for the dataclasses in *module*."""

    forms = []
    for name in getattr(module, "__all__", []):
        cls = getattr(module, name)
        meta = getattr(cls, "Meta")
        if meta.abstract:
            continue
        forms.append(_render_form(cls))

    body = "\n".join(forms)
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "  <meta charset=\"utf-8\">\n"
        "  <title>INTERLIS UI Scaffolding</title>\n"
        "  <style>\n"
        "  body { font-family: sans-serif; margin: 2rem; }\n"
        "  form { display: grid; gap: 1rem; border: 1px solid #ccc; padding: 1.5rem; border-radius: 8px; }\n"
        "  .model { margin-bottom: 3rem; }\n"
        "  .field { display: flex; flex-direction: column; font-weight: 600; }\n"
        "  .field input, .field select { margin-top: 0.5rem; padding: 0.5rem; font-size: 1rem; }\n"
        "  fieldset { border: 1px dashed #aaa; padding: 1rem; }\n"
        "  legend { font-weight: 700; }\n"
        "  .list-item { margin-bottom: 0.5rem; }\n"
        "  .actions { text-align: right; }\n"
        "  button { padding: 0.5rem 1rem; font-size: 1rem; }\n"
        "  .hint { display: block; font-size: 0.85rem; color: #666; margin-bottom: 0.5rem; }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        "  <h1>INTERLIS UI scaffolding</h1>\n"
        "  <p>This page was generated from INTERLIS metadata without additional dependencies.</p>\n"
        f"{body}\n"
        "  <script>\n"
        "  document.addEventListener('click', function (event) {\n"
        "    if (!event.target.matches('[data-action=\\'add-item\\']')) { return; }\n"
        "    var fieldset = event.target.closest('fieldset');\n"
        "    var template = fieldset.querySelector('[data-template]');\n"
        "    var clone = template.cloneNode(true);\n"
        "    clone.removeAttribute('data-template');\n"
        "    clone.querySelectorAll('input').forEach(function (input) { input.value = ''; });\n"
        "    fieldset.querySelector('.list-items').appendChild(clone);\n"
        "  });\n"
        "  </script>\n"
        "</body>\n"
        "</html>\n"
    )


def run(output_path: str | Path = Path("ui_scaffolding_example.html")) -> str:
    """Generate the HTML UI scaffolding and write it to *output_path*."""

    module = _load_dataclass_module(MODEL_PATH)
    html = build_html(module)
    destination = Path(output_path).resolve()
    destination.write_text(html, encoding="utf-8")
    return html


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("ui_scaffolding_example.html"),
        help="Path of the HTML document that should be written",
    )
    args = parser.parse_args(argv)
    run(args.output)
    print(f"Generated {args.output}")


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    main()
