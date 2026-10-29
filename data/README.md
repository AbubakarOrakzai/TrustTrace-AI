# Public prompt-injection evaluation data

The evaluation script fetches the **test** split of
[NeurAlchemy's Prompt Injection & Jailbreak Detection Dataset](https://huggingface.co/datasets/neuralchemy/Prompt-injection-dataset)
from Hugging Face's public dataset viewer. It pins repository revision
`7d70432dfcf47a821612cbf9d34e9d9e3ad20e75` and uses the `core` configuration.
The dataset card declares Apache-2.0; it also identifies upstream sources with
their own terms, so consult the dataset card and upstream licenses before
redistributing any examples.

Samples are processed in memory and are not written to disk, printed, sent to
an inference provider, or added to the audit ledger. Only aggregate metrics are
printed. See `backend/evaluate_public_dataset.py`.

The Public Data Lab also provides a small downloadable JSONL file of 12
`original`-source examples from this dataset's pinned `core` test split (six
attack and six benign). The dataset card identifies its original attack
database and hand-crafted benign prompts as Apache-2.0; the sample excludes
rows attributed to separately licensed upstream datasets. Each row contains
only `text`, `label`, and `category`. The sample is for trying the evaluator,
not a representative estimate of real-world detection performance.
With the current deterministic rules, the 12-row sample flags 0 of its 6
attacks and allows all 6 benign rows. This is a useful illustration of the
rules' limitations, not a model-quality benchmark.
The sample is provided under Apache-2.0; see [LICENSE-2.0.txt](LICENSE-2.0.txt).

Source: [dataset card](https://huggingface.co/datasets/neuralchemy/Prompt-injection-dataset/tree/7d70432dfcf47a821612cbf9d34e9d9e3ad20e75)
at revision `7d70432dfcf47a821612cbf9d34e9d9e3ad20e75`, `core` / `test`.
