import copy


def transform_report(report, features):
    return [transform_report_row(row, features) for row in report]


def transform_report_row(report_row, features):
    parts = report_row["parts"]
    res_parts = {}
    for part in parts:
        tag = part["tag"] = make_tag(part["tag"], features)
        if tag not in res_parts:
            res_parts[tag] = part.copy()
        else:
            res_parts[tag]["ticks"] += part["ticks"]
            res_parts[tag]["idle_ticks"] += part["idle_ticks"]

    res = copy.deepcopy({k: v for (k, v) in report_row.items() if k != "parts"})
    res["parts"] = res_parts
    return res


def make_tag(tag: str, features):
    if not features:
        features = ()
    if "vscode-name" in features and tag.endswith(" - Visual Studio Code"):
        return "Visual Studio Code"
    if "vscode-wpc" in features and tag.endswith(" - Visual Studio Code"):
        split = tag.split(" - ")
        assert len(split) > 1, split
        return split[-2] + " - " + split[-1]
    if "slack-name" in features and tag.startswith("Slack |"):
        return "Slack"
    if "slack-wpc" in features and tag.startswith("Slack |"):
        split = tag.split(" | ")
        if len(split) <= 2:
            return tag
        return split[0] + " | " + split[2]
    if "chrome-name" in features and tag.endswith(" - Google Chrome"):
        return "Google Chrome"
    if "chromium-name" in features and tag.endswith(" - Chromium"):
        return "Chromium"
    return tag
