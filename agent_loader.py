from typing import Any, Dict


def load_agent_yaml(path: str) -> Dict[str, Any]:
    # Minimal YAML loader without external deps (expects the provided format)
    # This is intentionally simplistic; for complex YAML, use PyYAML.
    data: Dict[str, Any] = {"abilities": [], "tags": []}
    with open(path, "r", encoding="utf-8") as f:
        lines = [l.rstrip("\n") for l in f]
    section = None
    buf = []
    description_lines = []
    reasoning_lines = []
    decision_lines = []
    required_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("---"):
            i += 1
            continue
        if ":" in line and not line.lstrip().startswith("-"):
            key, val = line.split(":", 1)
            k = key.strip()
            v = val.strip()
            if k == "name":
                data["name"] = v
            elif k == "description":
                data["description"] = v
            elif k == "author":
                data["author"] = v
            elif k == "version":
                data["version"] = v
            elif k == "abilities":
                section = "abilities"
            elif k == "tags":
                section = "tags"
            else:
                section = None
        elif line.lstrip().startswith("-"):
            item = line.split("-", 1)[1].strip()
            if section == "abilities":
                data["abilities"].append(item)
            elif section == "tags":
                data["tags"].append(item)
        else:
            # Capture Markdown sections after YAML header
            txt = line
            if txt.strip().upper().startswith("## REASONING FRAMEWORK"):
                section = "rfw"
            elif txt.strip().upper().startswith("## DECISION CRITERIA"):
                section = "dc"
            elif txt.strip().upper().startswith("## REQUIRED OUTPUT"):
                section = "req"
            else:
                if section == "rfw":
                    reasoning_lines.append(txt)
                elif section == "dc":
                    decision_lines.append(txt)
                elif section == "req":
                    required_lines.append(txt)
        i += 1
    data["reasoning_framework"] = "\n".join(reasoning_lines).strip()
    data["decision_criteria"] = "\n".join(decision_lines).strip()
    data["required_output"] = "\n".join(required_lines).strip()
    return data
