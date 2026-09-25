# Vendored structures

Test inputs for stage 1 (structure ingestion, VER-48) and, from WP22, the Tier-2 leg of VAL-05
(`SPECIFICATION.md` §8.2.2 B2). Each file is byte-for-byte as downloaded from the wwPDB archive and
is never rewritten: its sha256 enters the stage-1 artefact key, which is why `.gitattributes` marks
`tests/data/**` `-text`.

| File | Source | Downloaded | sha256 |
|---|---|---|---|
| `2wcd.pdb.gz` | <https://files.wwpdb.org/pub/pdb/data/structures/divided/pdb/wc/pdb2wcd.ent.gz> | 25 September 2026 | `44cd35a4555422ebb1d73a2812ac9fb724bbe3532e5f6316949dc1adf67087cd` |
| `2wcd.cif.gz` | <https://files.wwpdb.org/pub/pdb/data/structures/divided/mmCIF/wc/2wcd.cif.gz> | 25 September 2026 | `a90292f583a132bdbae4ca84b10a442ae43a5b1ef33add4d05b846f4ecc4074f` |

PDB entry 2WCD is the cytolysin A (ClyA) dodecamer of Mueller et al., *Nature* **459**, 726–730
(2009). Its asymmetric unit holds two dodecamers, chains A–L and M–X. The wwPDB distributes its
archive under CC0 1.0 (<https://www.wwpdb.org/about/usage-policies>).
