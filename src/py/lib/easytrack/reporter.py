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
    res["parts"] = sorted(res_parts.values(), key=lambda v: -v['ticks'])
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


def print_basic_format(report_rows, fileobj):
    def _print(*a, **kw):
        print(*a, **kw, file=fileobj)

    _print(f"{len(report_rows)} chunks:")
    _print()
    for row in report_rows:
        total = row["total_ticks"] + row["total_idle_ticks"] + row["untracked_ticks"]
        tbusy = round(row["total_ticks"] / total * 100)
        tidle = round(row["total_idle_ticks"] / total * 100)
        tuntracked = round(row["untracked_ticks"] / total * 100)
        _print(
            f'{row["from"]}-{row["to"]} - {tbusy}% busy, {tidle}% idle, {tuntracked}% untracked:'
        )
        for i, part in enumerate(row["parts"], start=1):
            pbusy = round(part["ticks"] / total * 100)
            pidle = round(part["idle_ticks"] / total * 100)
            _print(f'{i:2}: {pbusy}% busy, {pidle}% idle - {part["tag"]}')
        _print()
