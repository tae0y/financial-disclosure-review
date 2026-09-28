# Third-party material and source notices

The MIT license in this repository applies only to project-authored source code and documentation
to the extent the contributors own the relevant rights. It does not grant rights in third-party
material.

Review criteria may identify or quote official legal and regulatory sources. The repository keeps
the source URL with each criterion so users can verify the current primary material. Official
source material is not relicensed by this project; users must check the applicable source terms
and law before copying or redistributing it.

Do not commit product-page captures, screenshots, extracted page text, model transcripts, or
deployment credentials to the public repository without confirming a lawful publication basis and
the relevant website terms. Product names, company names, and logos remain the property of their
respective owners.

This project produces a technical review aid, not legal, regulatory, or financial advice. A human
reviewer remains responsible for any publication or compliance decision.

## NVIDIA Nemotron-Personas-Korea

`assets/persona_profiles.yaml` contains reader profiles derived from three rows (identified by
their `uuid`) of the NVIDIA Nemotron-Personas-Korea dataset
(<https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea>), by NVIDIA Corporation,
licensed under the Creative Commons Attribution 4.0 International License (CC BY 4.0,
<https://creativecommons.org/licenses/by/4.0/>). The personas are synthetic. Changes made: only
derived reading attributes (reading preference, financial familiarity, likely questions,
prohibited assumptions, analogy policy and a short derivation note) were drafted from those rows;
the dataset's persona text is not redistributed. The derived profiles are provided without
warranty and are not endorsed by NVIDIA.

The application also uses the full dataset at a pinned revision
(`ada0f5b53a38bb5a30cce09358adde883c1ab63a`, nine parquet shards verified by sha256). It is not
committed to this repository: `python -m financial_disclosure_review fetch-personas` (run by the
Docker agent entrypoint on first boot) downloads it from Hugging Face into the local data
directory. At review time one row is selected, and a reader sketch is built from that row's
fields (age, sex, education level, occupation, province, family type) together with the row's
`persona` sentence, quoted verbatim. That sketch appears in the persona explanation's profile,
in the prompt sent to the model and in review output. Attribution: "Nemotron-Personas-Korea" by
NVIDIA Corporation, licensed under CC BY 4.0
(<https://creativecommons.org/licenses/by/4.0/>). Changes made: reading attributes are derived
from the selected row by the rules in `assets/persona_template.yaml`; the quoted `persona`
sentence itself is unmodified. Synthetic personas; no endorsement by NVIDIA is implied.
