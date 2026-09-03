"""Generate the materials appendix from vignettes.yaml.

Generated rather than hand-written so the appendix cannot drift from the stimuli
actually used. Rerun after any edit to materials/vignettes.yaml.
"""
import re
from pathlib import Path

import yaml

from src.conditions import OFFER_PREFIXES, QUESTION

OUT = Path("paper/appendix_materials.tex")

ESC = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
       "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
       "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def tex(s):
    s = "".join(ESC.get(c, c) for c in s)
    # curly quotes and dashes -> LaTeX forms
    s = (s.replace("—", "---").replace("–", "--")
           .replace("\u2019", "'").replace("\u2018", "`")
           .replace("\u201c", "``").replace("\u201d", "''"))
    # straight double quotes -> paired LaTeX quotes
    s = re.sub(r'"([^"]*)"', r"``\1''", s)
    return re.sub(r"\s*\n\s*", " ", s)


def main():
    vs = yaml.safe_load(open("materials/vignettes.yaml"))
    L = [r"\section{Stimulus materials}", r"\label{app:vignettes}", "",
         r"""All five vignettes and their scripted histories, verbatim. The vignette text is
identical across the short and long conditions; the long condition prepends the history.
The offer strings below are appended to the vignette to form the final user turn, and are
the only place familiarity language appears in any user turn.""", "",
         r"\begin{quote}\small"]
    for k in ("none", "knowledge", "relational"):
        # build the full string BEFORE escaping: the prefix's trailing space is
        # significant and was previously lost to strip()
        full = tex(OFFER_PREFIXES[k] + QUESTION)
        L.append(rf"\textbf{{{k}:}} ``{full}''\\")
    L += [r"\end{quote}", ""]

    for v in vs:
        dom = v["domain"].replace("_", " ")
        L += [rf"\subsection*{{{v['id'].upper()} --- {dom}}}", "",
              r"\noindent\textbf{Vignette (both conditions).}", "",
              r"\begin{quote}\small " + tex(v["short"]).strip() + r"\end{quote}", "",
              r"\noindent\textbf{Scripted history (long condition only).}", "",
              r"\begin{quote}\small"]
        for t in v["history"]:
            who = "User" if t["role"] == "user" else "Assistant"
            L.append(rf"\textbf{{{who}:}} {tex(t['content']).strip()}\\[2pt]")
        L += [r"\end{quote}", ""]

    OUT.write_text("\n".join(L) + "\n")
    print(f"wrote {OUT} ({len(vs)} vignettes)")


if __name__ == "__main__":
    main()
