# Faithful Annual Review reconstruction

Reference: D:/iip_exchange/Annual_Review_Chenzhao Jia.pdf (57 pages).

main.tex restores its native source, bibliography, all tables, figures, conclusion and examples. Four tiny singular/plural differences in the recovered source were transcribed to match the PDF. Chinese fonts are embedded afresh; the reference PDF's broken extraction mappings are not copied.

Compile with XeLaTeX and BibTeX: python scripts/compile_manuscript.py --baseline from the project root. This is a historical document reconstruction, not certification or re-estimation of its empirical claims. Make further editorial additions in the separate drafts/manuscript project.
