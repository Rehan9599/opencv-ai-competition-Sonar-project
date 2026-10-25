# PDF Audit for OpenCV AI Competition Submission

Audited on 2026-10-24 with `pdftotext`.

| PDF | Recommendation | Reason |
|---|---|---|
| `data and preprocessing.pdf` | Keep | Technical preprocessing evidence; no detected SIH or legacy problem-statement reference. |
| `model.pdf` | Keep, then update source if regenerated | Useful model-selection evidence; segmentation is described as an alternative, not the shipped path. |
| `scale and limits.pdf` | Keep, then update source if regenerated | Useful limitations and deployment evidence; no detected SIH reference. |
| `literature.pdf` | Regenerate or remove from the public submission | Contains `SIH 26057-Internal Note`; replace with an OpenCV/AWS contest evidence note. |
| `problem and physics.pdf` | Regenerate or remove from the public submission | Contains a generic original problem-statement section and internal taxonomy language that is stale for the contest branch. |
| `system.pdf` | Regenerate or remove from the public submission | Contains `Problem Statement 26057` and should describe the OpenCV 5 plus AWS architecture instead. |

Do not delete the entire `docs/Documents/` directory. The three retained documents support
reproducibility and responsible-use claims. Before publishing, either regenerate the three
flagged PDFs from contest-specific source material or remove only those three files from the
public branch.

Binary files are not safely editable with normal source patches. Do not modify PDFs in place
with a text editor. Regenerate them from their source documents and re-run this audit.
